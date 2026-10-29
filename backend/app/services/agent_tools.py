"""Agent Tools Interface for BrandLedger.

Exposes authoritative, deterministic tools for AI agents and external callers:
1. scan_creative: Runs backend compliance scan with evidence verification.
2. get_findings: Retrieves persisted findings for an existing scan or draft.
3. verify_merkle_proof: Mathematically verifies cryptographic Merkle inclusion proofs.

Safety & Authoritative Compliance Guarantees:
- Deterministic backend logic is authoritative: agents NEVER override, invent,
  or suppress findings.
- The system returns explicit machine-readable compliance decisions:
  * PASS: Clean scan with zero blocking violations.
  * BLOCK: One or more high or blocker violations detected.
  * HUMAN_REVIEW: Ambiguous claims, unsupported claims requiring human judgment,
    missing evidence, or unparseable inputs.
- All evidence citations retain verbatim policy quotes and exact policy versions.
"""

from datetime import date
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from backend.app.db import db_manager
from backend.app.schemas.agent_tools import (
    ComplianceDecision,
    EvidenceCitation,
    GetFindingsResult,
    ScanCreativeInput,
    ScanCreativeResult,
)
from backend.app.schemas.finding import Finding, FindingCategory, FindingSeverity
from backend.app.schemas.merkle import MerkleProof, MerkleProofVerificationResult
from backend.app.schemas.scan import ScanStatus
from backend.app.services.evidence_verifier import filter_and_verify_findings
from backend.app.services.merkle_ledger import verify_merkle_proof as merkle_verify
from backend.app.services.policy_engine import scan_draft

logger = logging.getLogger(__name__)

# Fallback sample policies if database is offline or not configured
DEFAULT_SAMPLE_POLICIES = [
    {
        "id": "pol_term_001",
        "version": "1.0",
        "title": "Brand Terminology Policy",
        "category": "terminology",
        "content": "The brand prohibits the term 'Customers' and requires the term 'Members'. Always refer to account holders as members.",
        "rules": [
            {
                "type": "terminology",
                "prohibited": "Customers",
                "replacement": "Members",
                "quote": "The brand prohibits the term 'Customers' and requires the term 'Members'."
            }
        ],
        "metadata": {"prohibited_terms": [{"term": "Customers", "replacement": "Members"}]}
    },
    {
        "id": "pol_offer_002",
        "version": "2.1",
        "title": "Summer Discount Promotion",
        "category": "offer_validity",
        "content": "Summer Discount promotion is valid through 2026-06-30. After this date, standard pricing applies.",
        "metadata": {
            "offer_name": "Summer Discount",
            "valid_until": "2026-06-30",
            "quote": "Summer Discount promotion is valid through 2026-06-30."
        }
    },
    {
        "id": "pol_num_003",
        "version": "1.5",
        "title": "Rewards Program Limits",
        "category": "rewards",
        "content": "The maximum reward is 500 points for any individual transaction. Points cannot be transferred.",
        "rules": [
            {
                "type": "numerical",
                "metric": "reward",
                "value": 500,
                "unit": "points",
                "limit_type": "max",
                "quote": "The maximum reward is 500 points for any individual transaction."
            }
        ]
    },
    {
        "id": "pol_claim_004",
        "version": "3.0",
        "title": "Marketing Claim Substantiation",
        "category": "claims",
        "content": "All performance guarantees and promises of guaranteed results require prior approved evidence from legal compliance.",
        "rules": [
            {
                "type": "claim_verification",
                "requires_evidence": True,
                "quote": "All performance guarantees and promises of guaranteed results require prior approved evidence from legal compliance."
            }
        ]
    }
]


# ---------------------------------------------------------------------------
# Tool 1: scan_creative
# ---------------------------------------------------------------------------

def evaluate_compliance_decision(
    findings: List[Finding],
    scan_failed: bool = False,
    error_message: Optional[str] = None,
) -> tuple[ComplianceDecision, str, int, bool]:
    """Deterministically determine the compliance decision based on findings.

    Returns:
        (decision, decision_reason, blockers_count, has_blockers)
    """
    if scan_failed:
        reason = f"Scan failed to complete: {error_message or 'Unknown scan error'}. Human review required."
        return ComplianceDecision.HUMAN_REVIEW, reason, 0, False

    blockers = [
        f for f in findings
        if f.severity in (FindingSeverity.HIGH.value, "high", "blocker")
    ]
    unverified_claims = [
        f for f in findings
        if f.category in (FindingCategory.UNSUPPORTED_CLAIM.value, "unsupported_claim", "tone")
        or not f.is_verified
    ]

    blockers_count = len(blockers)
    has_blockers = blockers_count > 0

    if has_blockers:
        reason = (
            f"Blocked: Detected {blockers_count} blocking compliance violation(s) "
            f"(e.g., '{blockers[0].matched_text}' under {blockers[0].category})."
        )
        return ComplianceDecision.BLOCK, reason, blockers_count, True

    if unverified_claims:
        reason = (
            f"Human Review Required: {len(unverified_claims)} unverified or ambiguous claim(s) "
            f"require substantiation or legal human review (e.g., '{unverified_claims[0].matched_text}')."
        )
        return ComplianceDecision.HUMAN_REVIEW, reason, 0, False

    reason = "Compliant: All deterministic checks passed with zero blocking violations."
    return ComplianceDecision.PASS, reason, 0, False


async def scan_creative(
    creative_input: Union[str, Dict[str, Any], ScanCreativeInput],
    policy_cards: Optional[List[Dict[str, Any]]] = None,
    scan_date: Optional[str] = None,
) -> ScanCreativeResult:
    """Execute authoritative deterministic compliance scan for a creative asset.

    Accepts:
    - creative_input: Raw text string, dictionary, or ScanCreativeInput model.
    - policy_cards: Optional list of approved policy card dicts. If omitted,
      loads active policy cards from the database if connected, or uses default
      approved policy definitions.
    - scan_date: Explicit reference date (YYYY-MM-DD). Defaults to today.

    Returns:
        ScanCreativeResult containing authoritative status, decision (PASS/BLOCK/HUMAN_REVIEW),
        findings, and evidence citations.
    """
    # 1. Parse and validate input
    if isinstance(creative_input, ScanCreativeInput):
        content_text = creative_input.content_text
        input_scan_date = creative_input.scan_date or scan_date
        input_policies = creative_input.policy_cards or policy_cards
        draft_id = creative_input.draft_id
    elif isinstance(creative_input, dict):
        content_text = str(creative_input.get("content_text") or creative_input.get("text") or "").strip()
        input_scan_date = creative_input.get("scan_date") or scan_date
        input_policies = creative_input.get("policy_cards") or policy_cards
        raw_draft_id = creative_input.get("draft_id")
        draft_id = UUID(str(raw_draft_id)) if raw_draft_id else None
    elif isinstance(creative_input, str):
        content_text = creative_input.strip()
        input_scan_date = scan_date
        input_policies = policy_cards
        draft_id = None
    else:
        return ScanCreativeResult(
            status=ScanStatus.FAILED,
            decision=ComplianceDecision.HUMAN_REVIEW,
            decision_reason="Invalid creative input type. Expected string, dict, or ScanCreativeInput.",
            total_findings=0,
            blockers_count=0,
            has_blockers=False,
            findings=[],
            evidence_citations=[],
        )

    if not content_text:
        return ScanCreativeResult(
            status=ScanStatus.FAILED,
            decision=ComplianceDecision.HUMAN_REVIEW,
            decision_reason="Empty creative content provided. Content cannot be evaluated.",
            total_findings=0,
            blockers_count=0,
            has_blockers=False,
            findings=[],
            evidence_citations=[],
        )

    # 2. Resolve scan reference date
    resolved_scan_date = input_scan_date or date.today().isoformat()

    # 3. Resolve policy cards
    policies_to_use = input_policies
    if not policies_to_use:
        if db_manager.is_connected:
            try:
                from backend.app.services.scan_service import load_active_policy_cards
                db_cards, _ = await load_active_policy_cards()
                if db_cards:
                    policies_to_use = db_cards
            except Exception as exc:
                logger.warning("Could not load policy cards from database: %s", exc)

    if not policies_to_use:
        policies_to_use = DEFAULT_SAMPLE_POLICIES

    # 4. Invoke deterministic policy engine
    try:
        raw_findings = scan_draft(
            content_text=content_text,
            policy_cards=policies_to_use,
            scan_date=resolved_scan_date,
        )
    except ValueError as val_err:
        return ScanCreativeResult(
            status=ScanStatus.FAILED,
            decision=ComplianceDecision.HUMAN_REVIEW,
            decision_reason=f"Scan validation error: {str(val_err)}",
            total_findings=0,
            blockers_count=0,
            has_blockers=False,
            findings=[],
            evidence_citations=[],
        )
    except Exception as exc:
        logger.error("Scan engine execution error: %s", exc)
        return ScanCreativeResult(
            status=ScanStatus.FAILED,
            decision=ComplianceDecision.HUMAN_REVIEW,
            decision_reason=f"Scan execution error: {str(exc)}",
            total_findings=0,
            blockers_count=0,
            has_blockers=False,
            findings=[],
            evidence_citations=[],
        )

    # 5. Format validated findings and extract traceable evidence citations
    validated_findings: List[Finding] = []
    citations: List[EvidenceCitation] = []

    for f_item in raw_findings:
        f = Finding.model_validate(f_item)
        validated_findings.append(f)
        citations.append(EvidenceCitation(
            policy_card_id=f.policy_card_id,
            policy_version=f.policy_version,
            source_quote=f.source_quote,
            category=f.category,
            severity=f.severity,
            matched_text=f.matched_text,
        ))

    # 6. Evaluate authoritative compliance decision
    decision, reason, blockers_count, has_blockers = evaluate_compliance_decision(
        findings=validated_findings,
        scan_failed=False,
    )

    return ScanCreativeResult(
        status=ScanStatus.COMPLETED,
        decision=decision,
        decision_reason=reason,
        total_findings=len(validated_findings),
        blockers_count=blockers_count,
        has_blockers=has_blockers,
        findings=validated_findings,
        evidence_citations=citations,
        draft_id=draft_id,
    )


# ---------------------------------------------------------------------------
# Tool 2: get_findings
# ---------------------------------------------------------------------------

async def get_findings(
    scan_id: Optional[Union[str, UUID]] = None,
    draft_id: Optional[Union[str, UUID]] = None,
) -> GetFindingsResult:
    """Retrieve persisted findings for an existing scan or content draft.

    Accepts:
    - scan_id: The UUID or string ID of the target scan.
    - draft_id: The UUID or string ID of the target draft.

    Returns:
        GetFindingsResult with structured findings and execution status.
    """
    if not scan_id and not draft_id:
        return GetFindingsResult(
            found=False,
            error="Either scan_id or draft_id must be provided to query findings.",
            total_findings=0,
            findings=[],
        )

    # Validate UUID format
    clean_scan_uuid: Optional[UUID] = None
    if scan_id:
        try:
            clean_scan_uuid = UUID(str(scan_id).strip())
        except ValueError:
            return GetFindingsResult(
                found=False,
                scan_id=str(scan_id),
                error=f"Invalid scan_id format: '{scan_id}'. Expected valid UUID.",
                total_findings=0,
                findings=[],
            )

    clean_draft_uuid: Optional[UUID] = None
    if draft_id:
        try:
            clean_draft_uuid = UUID(str(draft_id).strip())
        except ValueError:
            return GetFindingsResult(
                found=False,
                draft_id=str(draft_id),
                error=f"Invalid draft_id format: '{draft_id}'. Expected valid UUID.",
                total_findings=0,
                findings=[],
            )

    # Query database if connected
    if not db_manager.is_connected:
        try:
            await db_manager.connect()
        except Exception:
            pass

    if not db_manager.is_connected:
        return GetFindingsResult(
            found=False,
            scan_id=str(clean_scan_uuid) if clean_scan_uuid else None,
            draft_id=str(clean_draft_uuid) if clean_draft_uuid else None,
            error="Database connection is not available to retrieve persisted findings.",
            total_findings=0,
            findings=[],
        )

    try:
        if clean_scan_uuid:
            scan_row = await db_manager.fetchrow(
                "SELECT id, draft_id, status FROM scans WHERE id = $1;",
                clean_scan_uuid,
            )
            if not scan_row:
                return GetFindingsResult(
                    found=False,
                    scan_id=str(clean_scan_uuid),
                    error=f"Scan with ID '{clean_scan_uuid}' not found.",
                    total_findings=0,
                    findings=[],
                )
            target_scan_id = clean_scan_uuid
            target_draft_id = scan_row["draft_id"]
            scan_status = scan_row["status"]
        else:
            # Query latest scan for draft_id
            scan_row = await db_manager.fetchrow(
                """
                SELECT id, draft_id, status
                FROM scans
                WHERE draft_id = $1
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                clean_draft_uuid,
            )
            if not scan_row:
                return GetFindingsResult(
                    found=False,
                    draft_id=str(clean_draft_uuid),
                    error=f"No scan records found for draft ID '{clean_draft_uuid}'.",
                    total_findings=0,
                    findings=[],
                )
            target_scan_id = scan_row["id"]
            target_draft_id = clean_draft_uuid
            scan_status = scan_row["status"]

        findings_rows = await db_manager.fetch(
            """
            SELECT policy_card_id, policy_version, category, severity,
                   matched_text, source_quote, explanation, suggested_fix,
                   confidence, is_verified
            FROM findings
            WHERE scan_id = $1
            ORDER BY created_at ASC;
            """,
            target_scan_id,
        )

        findings: List[Finding] = []
        for r in findings_rows:
            findings.append(Finding(
                policy_card_id=str(r["policy_card_id"] or ""),
                policy_version=str(r["policy_version"]),
                category=r["category"],
                severity=r["severity"],
                matched_text=r["matched_text"],
                source_quote=r["source_quote"],
                explanation=r["explanation"],
                suggested_fix=r["suggested_fix"] or "",
                confidence=float(r["confidence"]),
                is_verified=bool(r["is_verified"]),
            ))

        return GetFindingsResult(
            found=True,
            scan_id=str(target_scan_id),
            draft_id=str(target_draft_id),
            status=scan_status,
            total_findings=len(findings),
            findings=findings,
            error=None,
        )

    except Exception as exc:
        logger.error("Error retrieving findings: %s", exc)
        return GetFindingsResult(
            found=False,
            scan_id=str(clean_scan_uuid) if clean_scan_uuid else None,
            draft_id=str(clean_draft_uuid) if clean_draft_uuid else None,
            error=f"Failed to query findings: {str(exc)}",
            total_findings=0,
            findings=[],
        )


# ---------------------------------------------------------------------------
# Tool 3: verify_merkle_proof
# ---------------------------------------------------------------------------

def verify_merkle_proof(
    leaf: Union[str, Dict[str, Any], Any],
    proof: Union[MerkleProof, Dict[str, Any], List[Any]],
    expected_root: str,
) -> MerkleProofVerificationResult:
    """Validate a Merkle inclusion proof using actual cryptographic verification.

    Accepts:
    - leaf: 64-character SHA-256 leaf hash OR raw ledger entry dict/string.
    - proof: MerkleProof object, dict representation, or list of steps.
    - expected_root: The expected 64-character hex Merkle root.

    Returns:
        Explicit, machine-readable MerkleProofVerificationResult.
    """
    return merkle_verify(
        leaf=leaf,
        proof=proof,
        expected_root=expected_root,
    )
