"""Publication Gate and Verification Service for BrandLedger (Owned by Member 6).

Implements:
- Constant-time HMAC-SHA256 signature verification for CMS webhooks.
- Idempotent duplicate-event tracking and safe concurrency protection.
- Deterministic publication eligibility decision:
  * PASS only when draft has reviewer approval, zero active blockers, and valid Content Passport.
  * BLOCK with literal evidence citations if blockers exist, approval is missing, or passport is tampered.
"""
from datetime import datetime
import hashlib
import hmac
import json
import logging
from typing import List, Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, status

from backend.app.db import db_manager
from backend.app.schemas.gate import (
    GateDecision,
    GateFindingEvidence,
    PublishGateRequest,
    PublishGateResponse,
)
from backend.app.schemas.passport import PassportResponse, PassportStatus
from backend.app.services.review_service import get_passport
from backend.app.services.scan_service import get_persisted_scan

logger = logging.getLogger(__name__)


def compute_payload_hash(payload: PublishGateRequest) -> str:
    """Compute deterministic SHA-256 fingerprint of gate request payload for idempotency verification."""
    data = {
        "event_id": payload.event_id.strip(),
        "draft_id": str(payload.draft_id) if payload.draft_id else None,
        "scan_id": str(payload.scan_id) if payload.scan_id else None,
        "passport_id": str(payload.passport_id) if payload.passport_id else None,
        "content_text": payload.content_text.strip() if payload.content_text else None,
    }
    canonical = json.dumps(data, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_hmac_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    secret: str,
) -> bool:
    """Verify incoming webhook HMAC-SHA256 signature against raw request body.

    Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks.
    Accepts both hex digest format and 'sha256=<hex>' prefix.
    """
    if not signature_header or not signature_header.strip():
        return False
    if not secret or not secret.strip():
        logger.error("CMS webhook secret is empty or unset.")
        return False

    clean_sig = signature_header.strip()
    if clean_sig.lower().startswith("sha256="):
        clean_sig = clean_sig[7:].strip()

    expected_sig = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig.lower(), clean_sig.lower())


async def ensure_gate_schema() -> None:
    """Ensure the publication_events table and indices exist in PostgreSQL."""
    ddl = """
    CREATE TABLE IF NOT EXISTS publication_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_id VARCHAR(255) UNIQUE NOT NULL,
        draft_id UUID REFERENCES content_drafts(id) ON DELETE SET NULL,
        scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
        passport_id UUID REFERENCES passports(id) ON DELETE SET NULL,
        decision VARCHAR(50) NOT NULL CHECK (decision IN ('PASS', 'BLOCK', 'pass', 'block')),
        status_code INT NOT NULL DEFAULT 200,
        reason TEXT NOT NULL,
        response_payload JSONB NOT NULL,
        payload_hash VARCHAR(64),
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
    );
    ALTER TABLE publication_events ADD COLUMN IF NOT EXISTS payload_hash VARCHAR(64);
    CREATE INDEX IF NOT EXISTS idx_publication_events_event_id ON publication_events(event_id);
    CREATE INDEX IF NOT EXISTS idx_publication_events_draft_id ON publication_events(draft_id);
    """
    try:
        await db_manager.execute(ddl)
    except Exception as exc:
        logger.warning("Could not execute publication_events DDL check: %s", exc)


async def get_recorded_gate_event(
    event_id: str,
) -> Optional[Tuple[PublishGateResponse, Optional[str]]]:
    """Retrieve previously recorded publication decision and payload_hash for duplicate event ID."""
    query = """
        SELECT response_payload, payload_hash
        FROM publication_events
        WHERE event_id = $1;
    """
    row = await db_manager.fetchrow(query, event_id.strip())
    if not row:
        return None

    payload_data = row["response_payload"]
    if isinstance(payload_data, str):
        try:
            payload_data = json.loads(payload_data)
        except Exception:
            return None

    if isinstance(payload_data, dict):
        payload_data["duplicate"] = True
        return PublishGateResponse.model_validate(payload_data), row.get("payload_hash")

    return None


async def get_duplicate_publication_event(
    event_id: str,
) -> Optional[PublishGateResponse]:
    """Retrieve previously recorded publication decision for duplicate event ID."""
    rec = await get_recorded_gate_event(event_id)
    if rec:
        return rec[0]
    return None


async def record_publication_event(
    event_id: str,
    decision_resp: PublishGateResponse,
    payload_hash: Optional[str] = None,
) -> PublishGateResponse:
    """Persist publication decision record with concurrency-safe ON CONFLICT handling."""
    # Ensure foreign keys actually exist in parent tables before inserting into FK columns.
    valid_draft_id = None
    if decision_resp.draft_id:
        try:
            d_row = await db_manager.fetchrow(
                "SELECT id FROM content_drafts WHERE id = $1;",
                decision_resp.draft_id,
            )
            if d_row:
                valid_draft_id = decision_resp.draft_id
        except Exception:
            valid_draft_id = None

    valid_scan_id = None
    if decision_resp.scan_id:
        try:
            s_row = await db_manager.fetchrow(
                "SELECT id FROM scans WHERE id = $1;",
                decision_resp.scan_id,
            )
            if s_row:
                valid_scan_id = decision_resp.scan_id
        except Exception:
            valid_scan_id = None

    valid_passport_id = None
    if decision_resp.passport_id:
        try:
            p_row = await db_manager.fetchrow(
                "SELECT id FROM passports WHERE id = $1;",
                decision_resp.passport_id,
            )
            if p_row:
                valid_passport_id = decision_resp.passport_id
        except Exception:
            valid_passport_id = None

    insert_query = """
        INSERT INTO publication_events (
            event_id, draft_id, scan_id, passport_id, decision, status_code, reason, response_payload, payload_hash
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING id;
    """
    serialized_payload = json.dumps(decision_resp.model_dump(mode="json"))

    row = await db_manager.fetchrow(
        insert_query,
        event_id.strip(),
        valid_draft_id,
        valid_scan_id,
        valid_passport_id,
        decision_resp.decision.value,
        decision_resp.status_code,
        decision_resp.reason,
        serialized_payload,
        payload_hash,
    )

    if not row:
        # A concurrent worker inserted the identical event_id at the exact same instant
        existing = await get_duplicate_publication_event(event_id)
        if existing:
            return existing

    return decision_resp



async def evaluate_publication_eligibility(
    payload: PublishGateRequest,
) -> PublishGateResponse:
    """Evaluate whether a content draft is eligible for publication.

    Enforces authoritative rules:
    - BLOCK if draft has not received human reviewer approval.
    - BLOCK if scan has active blocking or high severity findings.
    - BLOCK if Content Passport is missing, revoked, or fails cryptographic hash verification.
    - BLOCK if content text was altered after human reviewer approval.
    - PASS only when all criteria are satisfied.
    """
    event_id = payload.event_id.strip()

    # 1. Identifier Validation
    if not payload.draft_id and not payload.passport_id:
        return PublishGateResponse(
            event_id=event_id,
            decision=GateDecision.BLOCK,
            status_code=400,
            reason="MISSING_IDENTIFIERS",
            explanation="Publication request must provide at least one valid 'draft_id' or 'passport_id'.",
        )

    # 2. Evaluation Branch: Passport ID provided directly
    if payload.passport_id:
        try:
            passport: PassportResponse = await get_passport(payload.passport_id)
        except HTTPException as http_err:
            if http_err.status_code == 404:
                return PublishGateResponse(
                    event_id=event_id,
                    decision=GateDecision.BLOCK,
                    status_code=200,
                    reason="PASSPORT_NOT_FOUND",
                    explanation=f"Content Passport '{payload.passport_id}' was not found in the database.",
                    passport_id=payload.passport_id,
                )
            raise

        resolved_draft_id = passport.draft_id
        resolved_scan_id = passport.scan_id
        passport_id = passport.id

        # Verification 2a: Identifier consistency check
        if payload.draft_id and payload.draft_id != resolved_draft_id:
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="ID_MISMATCH",
                explanation=f"Supplied draft_id '{payload.draft_id}' does not match passport draft ID '{resolved_draft_id}'.",
                draft_id=payload.draft_id,
                passport_id=passport_id,
            )

        if payload.scan_id and payload.scan_id != resolved_scan_id:
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="ID_MISMATCH",
                explanation=f"Supplied scan_id '{payload.scan_id}' does not match passport scan ID '{resolved_scan_id}'.",
                draft_id=resolved_draft_id,
                scan_id=payload.scan_id,
                passport_id=passport_id,
            )

        # Verification 2b: Passport Revocation Check
        if passport.status != PassportStatus.VALID:
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="PASSPORT_REVOKED",
                explanation=f"Content Passport status is '{passport.status.value}', expected 'valid'.",
                draft_id=resolved_draft_id,
                scan_id=resolved_scan_id,
                passport_id=passport_id,
                passport_hash_verified=passport.hash_verified,
            )

        # Verification 2c: Cryptographic SHA-256 Tamper Detection Check
        if not passport.hash_verified:
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="PASSPORT_TAMPERED",
                explanation="Cryptographic tamper check failed: recomputed canonical SHA-256 fingerprint does not match stored passport hash.",
                draft_id=resolved_draft_id,
                scan_id=resolved_scan_id,
                passport_id=passport_id,
                passport_hash_verified=False,
            )

        # Verification 2d: Draft approval verification in database
        draft_row = await db_manager.fetchrow(
            "SELECT id, title, content_text, status FROM content_drafts WHERE id = $1;",
            resolved_draft_id,
        )
        if not draft_row:
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="DRAFT_NOT_FOUND",
                explanation=f"Associated content draft '{resolved_draft_id}' not found.",
                draft_id=resolved_draft_id,
                passport_id=passport_id,
            )

        if draft_row["status"] != "approved":
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="DRAFT_NOT_APPROVED",
                explanation=f"Content draft status is '{draft_row['status']}'. Publication requires explicit human reviewer approval.",
                draft_id=resolved_draft_id,
                scan_id=resolved_scan_id,
                passport_id=passport_id,
                passport_hash_verified=passport.hash_verified,
            )

        # Verification 2e: Copy alteration check (post-approval tamper check)
        if payload.content_text is not None and payload.content_text.strip():
            approved_text = (draft_row["content_text"] or "").strip()
            snapshot_text = (passport.metadata_snapshot.get("draft_content") or "").strip()
            submitted_text = payload.content_text.strip()

            if submitted_text != approved_text and submitted_text != snapshot_text:
                return PublishGateResponse(
                    event_id=event_id,
                    decision=GateDecision.BLOCK,
                    status_code=200,
                    reason="CONTENT_MODIFIED_POST_APPROVAL",
                    explanation="Creative copy has been altered after approval. Submitted content does not match the approved Content Passport snapshot.",
                    draft_id=resolved_draft_id,
                    scan_id=resolved_scan_id,
                    passport_id=passport_id,
                    passport_hash_verified=passport.hash_verified,
                )

        # Verification 2f: Scan Blocker Check
        try:
            scan_res = await get_persisted_scan(resolved_scan_id)
            blockers = [f for f in scan_res.findings if f.severity in ("blocker", "high")]
            if blockers or scan_res.has_blockers:
                evidence_list = [
                    GateFindingEvidence(
                        policy_card_id=f.policy_card_id,
                        policy_version=f.policy_version,
                        category=f.category,
                        severity=f.severity,
                        matched_text=f.matched_text,
                        source_quote=f.source_quote,
                        explanation=f.explanation,
                        suggested_fix=f.suggested_fix or "",
                    )
                    for f in blockers
                ]
                return PublishGateResponse(
                    event_id=event_id,
                    decision=GateDecision.BLOCK,
                    status_code=200,
                    reason="ACTIVE_BLOCKING_FINDINGS",
                    explanation=f"Compliance scan contains {len(evidence_list)} active blocking violation(s).",
                    draft_id=resolved_draft_id,
                    scan_id=resolved_scan_id,
                    passport_id=passport_id,
                    passport_hash_verified=passport.hash_verified,
                    findings=evidence_list,
                    total_blockers=len(evidence_list),
                )
        except HTTPException as http_err:
            if http_err.status_code == 404:
                return PublishGateResponse(
                    event_id=event_id,
                    decision=GateDecision.BLOCK,
                    status_code=200,
                    reason="SCAN_NOT_FOUND",
                    explanation=f"Associated scan record '{resolved_scan_id}' was not found.",
                    draft_id=resolved_draft_id,
                    passport_id=passport_id,
                )
            raise

        # All conditions satisfied for passport-backed request
        return PublishGateResponse(
            event_id=event_id,
            decision=GateDecision.PASS,
            status_code=200,
            reason="PUBLICATION_AUTHORIZED",
            explanation="Content draft is approved, zero active blockers detected, and Content Passport cryptographic integrity is verified.",
            draft_id=resolved_draft_id,
            scan_id=resolved_scan_id,
            passport_id=passport_id,
            passport_hash_verified=True,
            total_blockers=0,
        )

    # 3. Evaluation Branch: Draft ID provided without passport ID in payload
    draft_id = payload.draft_id
    draft_row = await db_manager.fetchrow(
        "SELECT id, title, content_text, status FROM content_drafts WHERE id = $1;",
        draft_id,
    )
    if not draft_row:
        return PublishGateResponse(
            event_id=event_id,
            decision=GateDecision.BLOCK,
            status_code=200,
            reason="DRAFT_NOT_FOUND",
            explanation=f"Content draft '{draft_id}' was not found in the database.",
            draft_id=draft_id,
        )

    # Retrieve scan for this draft
    scan_row = await db_manager.fetchrow(
        "SELECT id FROM scans WHERE draft_id = $1 ORDER BY created_at DESC LIMIT 1;",
        draft_id,
    )
    scan_id = scan_row["id"] if scan_row else payload.scan_id
    if not scan_id:
        return PublishGateResponse(
            event_id=event_id,
            decision=GateDecision.BLOCK,
            status_code=200,
            reason="NO_SCAN_FOUND",
            explanation=f"Content draft '{draft_id}' has not undergone an authoritative compliance scan.",
            draft_id=draft_id,
        )

    evidence_list: List[GateFindingEvidence] = []
    try:
        scan_res = await get_persisted_scan(scan_id)
        blockers = [f for f in scan_res.findings if f.severity in ("blocker", "high")]
        evidence_list = [
            GateFindingEvidence(
                policy_card_id=f.policy_card_id,
                policy_version=f.policy_version,
                category=f.category,
                severity=f.severity,
                matched_text=f.matched_text,
                source_quote=f.source_quote,
                explanation=f.explanation,
                suggested_fix=f.suggested_fix or "",
            )
            for f in blockers
        ]
        if blockers or scan_res.has_blockers:
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="ACTIVE_BLOCKING_FINDINGS",
                explanation=f"Content draft contains {len(evidence_list)} active blocking violation(s).",
                draft_id=draft_id,
                scan_id=scan_id,
                findings=evidence_list,
                total_blockers=len(evidence_list),
            )
    except HTTPException as http_err:
        if http_err.status_code == 404:
            return PublishGateResponse(
                event_id=event_id,
                decision=GateDecision.BLOCK,
                status_code=200,
                reason="SCAN_NOT_FOUND",
                explanation=f"Associated scan record '{scan_id}' was not found.",
                draft_id=draft_id,
            )
        raise
    except Exception as exc:
        logger.error("Database or service error retrieving scan %s: %s", scan_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database or service failure retrieving compliance scan: {str(exc)}",
        )

    # Check approval status
    if draft_row["status"] != "approved":
        return PublishGateResponse(
            event_id=event_id,
            decision=GateDecision.BLOCK,
            status_code=200,
            reason="DRAFT_NOT_APPROVED",
            explanation=f"Content draft status is '{draft_row['status']}'. Publication requires explicit human reviewer approval.",
            draft_id=draft_id,
            scan_id=scan_id,
            findings=evidence_list,
            total_blockers=len(evidence_list),
        )

    # If approved, verify that a valid Content Passport exists
    passport_row = await db_manager.fetchrow(
        "SELECT id FROM passports WHERE draft_id = $1 AND status = 'valid' ORDER BY created_at DESC LIMIT 1;",
        draft_id,
    )
    if not passport_row:
        return PublishGateResponse(
            event_id=event_id,
            decision=GateDecision.BLOCK,
            status_code=200,
            reason="MISSING_PASSPORT",
            explanation="Draft is marked approved, but no valid Content Passport certificate has been issued.",
            draft_id=draft_id,
            scan_id=scan_id,
        )

    # Verify cryptographic integrity of the retrieved passport
    passport = await get_passport(passport_row["id"])
    if not passport.hash_verified:
        return PublishGateResponse(
            event_id=event_id,
            decision=GateDecision.BLOCK,
            status_code=200,
            reason="PASSPORT_TAMPERED",
            explanation="Cryptographic tamper check failed on Content Passport.",
            draft_id=draft_id,
            scan_id=scan_id,
            passport_id=passport.id,
            passport_hash_verified=False,
        )

    return PublishGateResponse(
        event_id=event_id,
        decision=GateDecision.PASS,
        status_code=200,
        reason="PUBLICATION_AUTHORIZED",
        explanation="Content draft is approved, zero active blockers detected, and Content Passport cryptographic integrity is verified.",
        draft_id=draft_id,
        scan_id=scan_id,
        passport_id=passport.id,
        passport_hash_verified=True,
        total_blockers=0,
    )
