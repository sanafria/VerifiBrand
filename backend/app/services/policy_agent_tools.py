"""Policy and Content Passport Agent Tools for BrandLedger.

Owned by Member 2 (Nimra).
Implements the five authoritative policy & passport agent tools:
1. get_approved_policies: Retrieve active/approved policies (filtering out draft/inactive/archived).
2. get_policy_details: Retrieve full policy card with historical version lookup (?version=X).
3. get_passport: Retrieve Content Passport certificate with cryptographic verification.
4. verify_passport: Verify Content Passport SHA-256 hash against canonical snapshot.
5. explain_finding: Explain finding, verify verbatim source quote ("No receipt, no flag"),
   and provide actionable remediation guidance.

Safety & Determinism Guarantees:
- Never fabricates or hallucinates source quotes.
- Strictly returns 404/not found for non-existent versions (never silently falls back to latest).
- Mismatched or fabricated quotes trigger UNVERIFIED / HUMAN_REVIEW_REQUIRED evidence provenance.
- Works seamlessly in both live PostgreSQL environments and offline/test mock mode.
"""

from datetime import date, datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from backend.app.db import db_manager
from backend.app.schemas.agent_tools import (
    ContentPassportResult,
    ExplainFindingResult,
    GetApprovedPoliciesResult,
    PolicyDetailsResult,
    VerifyPassportResult,
)
from backend.app.schemas.finding import Finding
from backend.app.schemas.policy import (
    CardType,
    PolicyCardResponse,
    PolicyStatus,
    SeverityLevel,
    normalize_policy_status,
)
from backend.app.services.evidence_verifier import normalize_text_for_comparison
from backend.app.services.review_service import compute_canonical_passport_hash

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock Passport Seed Store (Offline & Test Resilience)
# ---------------------------------------------------------------------------

_VALID_SNAPSHOT_1: Dict[str, Any] = {
    "draft_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "scan_id": "8b9a1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
    "review_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "reviewer_id": "reviewer_zoya_01",
    "reviewer_name": "Zoya Reviewer",
    "decision": "approved",
    "approved_at": "2026-06-01T12:00:00Z",
    "applied_policy_versions": [
        {
            "policy_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
            "policy_key": "pol_term_001",
            "version": 1,
            "title": "Brand Addressing Terminology",
        },
        {
            "policy_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
            "policy_key": "pol_offer_002",
            "version": 1,
            "title": "Summer Discount Promotion Validity",
        },
    ],
    "findings_summary": {
        "total_findings": 0,
        "blockers": 0,
    },
}

_VALID_HASH_1: str = compute_canonical_passport_hash(_VALID_SNAPSHOT_1)

# Tampered snapshot where hash is pre-set to valid hash, but snapshot was maliciously modified
_TAMPERED_SNAPSHOT_2: Dict[str, Any] = {
    "draft_id": "e32ac10b-12cc-4372-a567-0e02b2c3d999",
    "scan_id": "7b9a1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4e",
    "review_id": "2a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6e",
    "reviewer_id": "unauthorized_party",
    "reviewer_name": "Adversary",
    "decision": "approved",
    "applied_policy_versions": [],
}

# The stored hash claims it is one thing, but snapshot hashes to something completely different
_TAMPERED_STORED_HASH: str = "000000000000000000000000000000000000000000000000000000000000dead"

_SEED_PASSPORTS: Dict[str, Dict[str, Any]] = {
    "c56a4180-65aa-42ec-a945-5fd21dec0538": {
        "id": "c56a4180-65aa-42ec-a945-5fd21dec0538",
        "draft_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "scan_id": "8b9a1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
        "review_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "passport_hash": _VALID_HASH_1,
        "status": "valid",
        "metadata_snapshot": _VALID_SNAPSHOT_1,
        "created_at": "2026-06-01T12:00:00Z",
    },
    "d67b5291-76bb-53fd-ba56-6fe32efd1649": {
        "id": "d67b5291-76bb-53fd-ba56-6fe32efd1649",
        "draft_id": "e32ac10b-12cc-4372-a567-0e02b2c3d999",
        "scan_id": "7b9a1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4e",
        "review_id": "2a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6e",
        "passport_hash": _TAMPERED_STORED_HASH,
        "status": "valid",
        "metadata_snapshot": _TAMPERED_SNAPSHOT_2,
        "created_at": "2026-06-02T14:30:00Z",
    },
}

_mock_passports: Dict[str, Dict[str, Any]] = {k: dict(v) for k, v in _SEED_PASSPORTS.items()}


def reset_mock_passports() -> None:
    """Reset mock passports to seed state."""
    global _mock_passports
    _mock_passports = {k: dict(v) for k, v in _SEED_PASSPORTS.items()}


def register_mock_passport(passport: Dict[str, Any]) -> str:
    """Register a passport in the in-memory fallback store."""
    passport_id = str(passport.get("id") or uuid4())
    passport_copy = dict(passport)
    passport_copy["id"] = passport_id
    _mock_passports[passport_id] = passport_copy
    return passport_id


# ---------------------------------------------------------------------------
# Tool 1: get_approved_policies
# ---------------------------------------------------------------------------

async def get_approved_policies(
    card_type: Optional[str] = None,
) -> GetApprovedPoliciesResult:
    """Retrieve all approved active policies.
    
    Excludes draft, inactive, and archived policies.
    Preserves stable IDs, policy_key, rules, and verbatim source quotes.
    """
    # 1. Try real PostgreSQL database if connected
    if db_manager.is_connected:
        try:
            query = """
                SELECT id, policy_key, title, card_type, rule_text, approved_value,
                       source_quote, valid_from, valid_until, severity, status,
                       version, rules, metadata, created_at, updated_at
                FROM policy_cards
                WHERE status = 'active'
            """
            params: List[Any] = []
            if card_type:
                query += " AND card_type = $1"
                params.append(card_type.lower())
            query += " ORDER BY created_at ASC;"

            rows = await db_manager.fetch(query, *params)
            policies: List[PolicyCardResponse] = []
            for r in rows:
                rules_val = r["rules"]
                if isinstance(rules_val, str):
                    try:
                        rules_val = json.loads(rules_val)
                    except Exception:
                        rules_val = []
                elif not isinstance(rules_val, list):
                    rules_val = []

                meta_val = r["metadata"]
                if isinstance(meta_val, str):
                    try:
                        meta_val = json.loads(meta_val)
                    except Exception:
                        meta_val = {}
                elif not isinstance(meta_val, dict):
                    meta_val = {}

                policies.append(PolicyCardResponse(
                    id=r["id"],
                    policy_key=r["policy_key"],
                    title=r["title"],
                    card_type=CardType(r["card_type"]),
                    rule_text=r["rule_text"],
                    approved_value=r["approved_value"],
                    source_quote=r["source_quote"],
                    valid_from=r["valid_from"],
                    valid_until=r["valid_until"],
                    severity=SeverityLevel(r["severity"]),
                    status=PolicyStatus.ACTIVE,
                    version=r["version"],
                    rules=rules_val,
                    metadata=meta_val,
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                ))
            return GetApprovedPoliciesResult(
                total_policies=len(policies),
                policies=policies,
            )
        except Exception as exc:
            logger.warning("Database error fetching approved policies: %s", exc)

    # 2. Fallback in-memory store
    from backend.app.api.policies import _mock_policies

    approved_policies: List[PolicyCardResponse] = []
    for p in _mock_policies:
        raw_status = p.get("status")
        normalized = normalize_policy_status(raw_status)
        if normalized != PolicyStatus.ACTIVE:
            continue

        if card_type:
            raw_card_type = p.get("card_type")
            ct_str = raw_card_type.value if hasattr(raw_card_type, "value") else str(raw_card_type)
            if ct_str.lower() != card_type.lower():
                continue

        p_id = p["id"] if isinstance(p["id"], UUID) else UUID(str(p["id"]))
        approved_policies.append(PolicyCardResponse(
            id=p_id,
            policy_key=p.get("policy_key"),
            title=p["title"],
            card_type=CardType(p["card_type"]),
            rule_text=p["rule_text"],
            approved_value=p.get("approved_value"),
            source_quote=p["source_quote"],
            valid_from=p.get("valid_from"),
            valid_until=p.get("valid_until"),
            severity=SeverityLevel(p["severity"]),
            status=PolicyStatus.ACTIVE,
            version=p["version"],
            rules=p.get("rules", []),
            metadata=p.get("metadata", {}),
            created_at=p.get("created_at") or datetime.now(timezone.utc),
            updated_at=p.get("updated_at") or datetime.now(timezone.utc),
        ))

    return GetApprovedPoliciesResult(
        total_policies=len(approved_policies),
        policies=approved_policies,
    )


# ---------------------------------------------------------------------------
# Tool 2: get_policy_details
# ---------------------------------------------------------------------------

async def get_policy_details(
    policy_id: Union[str, UUID],
    version: Optional[Union[int, str]] = None,
) -> PolicyDetailsResult:
    """Retrieve policy details for a given policy ID or policy_key.
    
    If version is specified, queries the immutable historical policy_card_versions table.
    Strictly returns found=False if that specific historical version does not exist.
    """
    clean_id_str = str(policy_id).strip()
    is_uuid = False
    clean_uuid: Optional[UUID] = None
    try:
        clean_uuid = UUID(clean_id_str)
        is_uuid = True
    except ValueError:
        pass

    target_version_int: Optional[int] = None
    if version is not None:
        try:
            target_version_int = int(str(version).split(".")[0])
        except ValueError:
            target_version_int = None

    # 1. Database execution
    if db_manager.is_connected:
        try:
            # First resolve the policy_cards row to obtain ID and policy_key
            if is_uuid:
                pc_row = await db_manager.fetchrow(
                    "SELECT id, policy_key FROM policy_cards WHERE id = $1;",
                    clean_uuid,
                )
            else:
                pc_row = await db_manager.fetchrow(
                    "SELECT id, policy_key FROM policy_cards WHERE policy_key = $1;",
                    clean_id_str,
                )

            if not pc_row:
                return PolicyDetailsResult(
                    found=False,
                    policy_id=clean_id_str,
                    error=f"Policy card '{clean_id_str}' was not found.",
                )

            real_id = pc_row["id"]
            policy_key = pc_row["policy_key"]

            # If specific version requested: query policy_card_versions
            if target_version_int is not None:
                ver_row = await db_manager.fetchrow(
                    """
                    SELECT policy_card_id, version, title, card_type, rule_text,
                           approved_value, source_quote, valid_from, valid_until,
                           severity, rules, metadata, created_at
                    FROM policy_card_versions
                    WHERE policy_card_id = $1 AND version = $2;
                    """,
                    real_id,
                    target_version_int,
                )
                if not ver_row:
                    return PolicyDetailsResult(
                        found=False,
                        policy_id=str(real_id),
                        policy_key=policy_key,
                        requested_version=str(version),
                        error=f"Version {version} for policy '{clean_id_str}' does not exist.",
                    )

                rules_val = ver_row["rules"]
                if isinstance(rules_val, str):
                    try:
                        rules_val = json.loads(rules_val)
                    except Exception:
                        rules_val = []
                elif not isinstance(rules_val, list):
                    rules_val = []

                meta_val = ver_row["metadata"]
                if isinstance(meta_val, str):
                    try:
                        meta_val = json.loads(meta_val)
                    except Exception:
                        meta_val = {}
                elif not isinstance(meta_val, dict):
                    meta_val = {}

                card_resp = PolicyCardResponse(
                    id=ver_row["policy_card_id"],
                    policy_key=policy_key,
                    title=ver_row["title"],
                    card_type=CardType(ver_row["card_type"]),
                    rule_text=ver_row["rule_text"],
                    approved_value=ver_row["approved_value"],
                    source_quote=ver_row["source_quote"],
                    valid_from=ver_row["valid_from"],
                    valid_until=ver_row["valid_until"],
                    severity=SeverityLevel(ver_row["severity"]),
                    status=PolicyStatus.ACTIVE,
                    version=ver_row["version"],
                    rules=rules_val,
                    metadata=meta_val,
                    created_at=ver_row["created_at"],
                    updated_at=ver_row["created_at"],
                )
                return PolicyDetailsResult(
                    found=True,
                    policy_id=str(real_id),
                    policy_key=policy_key,
                    version=str(ver_row["version"]),
                    requested_version=str(version),
                    is_historical=True,
                    policy=card_resp,
                )

            # Latest active policy details
            curr_row = await db_manager.fetchrow(
                """
                SELECT id, policy_key, title, card_type, rule_text, approved_value,
                       source_quote, valid_from, valid_until, severity, status,
                       version, rules, metadata, created_at, updated_at
                FROM policy_cards
                WHERE id = $1;
                """,
                real_id,
            )
            rules_val = curr_row["rules"]
            if isinstance(rules_val, str):
                try:
                    rules_val = json.loads(rules_val)
                except Exception:
                    rules_val = []
            elif not isinstance(rules_val, list):
                rules_val = []

            meta_val = curr_row["metadata"]
            if isinstance(meta_val, str):
                try:
                    meta_val = json.loads(meta_val)
                except Exception:
                    meta_val = {}
            elif not isinstance(meta_val, dict):
                meta_val = {}

            card_resp = PolicyCardResponse(
                id=curr_row["id"],
                policy_key=curr_row["policy_key"],
                title=curr_row["title"],
                card_type=CardType(curr_row["card_type"]),
                rule_text=curr_row["rule_text"],
                approved_value=curr_row["approved_value"],
                source_quote=curr_row["source_quote"],
                valid_from=curr_row["valid_from"],
                valid_until=curr_row["valid_until"],
                severity=SeverityLevel(curr_row["severity"]),
                status=normalize_policy_status(curr_row["status"]),
                version=curr_row["version"],
                rules=rules_val,
                metadata=meta_val,
                created_at=curr_row["created_at"],
                updated_at=curr_row["updated_at"],
            )
            return PolicyDetailsResult(
                found=True,
                policy_id=str(real_id),
                policy_key=policy_key,
                version=str(curr_row["version"]),
                is_historical=False,
                policy=card_resp,
            )
        except Exception as exc:
            logger.warning("Database error fetching policy details: %s", exc)

    # 2. In-memory fallback
    from backend.app.api.policies import _mock_policies, _mock_versions

    matching_card = None
    for p in _mock_policies:
        if is_uuid and p["id"] == clean_uuid:
            matching_card = p
            break
        elif str(p.get("policy_key", "")).lower() == clean_id_str.lower():
            matching_card = p
            break
        elif str(p["id"]).lower() == clean_id_str.lower():
            matching_card = p
            break

    if not matching_card:
        return PolicyDetailsResult(
            found=False,
            policy_id=clean_id_str,
            error=f"Policy card '{clean_id_str}' was not found.",
        )

    card_uuid = matching_card["id"]
    card_key = matching_card.get("policy_key")

    # If historical version requested:
    if target_version_int is not None:
        matching_ver = None
        for v in _mock_versions:
            if v["policy_card_id"] == card_uuid and v["version"] == target_version_int:
                matching_ver = v
                break

        if not matching_ver:
            return PolicyDetailsResult(
                found=False,
                policy_id=str(card_uuid),
                policy_key=card_key,
                requested_version=str(version),
                error=f"Version {version} for policy '{clean_id_str}' does not exist.",
            )

        card_resp = PolicyCardResponse(
            id=card_uuid,
            policy_key=card_key,
            title=matching_ver["title"],
            card_type=CardType(matching_ver["card_type"]),
            rule_text=matching_ver["rule_text"],
            approved_value=matching_ver.get("approved_value"),
            source_quote=matching_ver["source_quote"],
            valid_from=matching_ver.get("valid_from"),
            valid_until=matching_ver.get("valid_until"),
            severity=SeverityLevel(matching_ver["severity"]),
            status=PolicyStatus.ACTIVE,
            version=matching_ver["version"],
            rules=matching_ver.get("rules", []),
            metadata=matching_ver.get("metadata", {}),
            created_at=matching_ver.get("created_at") or datetime.now(timezone.utc),
            updated_at=matching_ver.get("created_at") or datetime.now(timezone.utc),
        )
        return PolicyDetailsResult(
            found=True,
            policy_id=str(card_uuid),
            policy_key=card_key,
            version=str(matching_ver["version"]),
            requested_version=str(version),
            is_historical=True,
            policy=card_resp,
        )

    # Current policy
    card_resp = PolicyCardResponse(
        id=card_uuid,
        policy_key=card_key,
        title=matching_card["title"],
        card_type=CardType(matching_card["card_type"]),
        rule_text=matching_card["rule_text"],
        approved_value=matching_card.get("approved_value"),
        source_quote=matching_card["source_quote"],
        valid_from=matching_card.get("valid_from"),
        valid_until=matching_card.get("valid_until"),
        severity=SeverityLevel(matching_card["severity"]),
        status=normalize_policy_status(matching_card.get("status")),
        version=matching_card["version"],
        rules=matching_card.get("rules", []),
        metadata=matching_card.get("metadata", {}),
        created_at=matching_card.get("created_at") or datetime.now(timezone.utc),
        updated_at=matching_card.get("updated_at") or datetime.now(timezone.utc),
    )
    return PolicyDetailsResult(
        found=True,
        policy_id=str(card_uuid),
        policy_key=card_key,
        version=str(matching_card["version"]),
        is_historical=False,
        policy=card_resp,
    )


# ---------------------------------------------------------------------------
# Tool 3: get_passport
# ---------------------------------------------------------------------------

async def get_passport(
    passport_id: Union[str, UUID],
) -> ContentPassportResult:
    """Retrieve Content Passport certificate and re-verify hash integrity.
    
    Returns machine-readable ContentPassportResult with applied policy versions
    and hash_verified boolean.
    """
    clean_id_str = str(passport_id).strip()
    clean_uuid: Optional[UUID] = None
    try:
        clean_uuid = UUID(clean_id_str)
    except ValueError:
        pass

    # 1. Database execution
    if db_manager.is_connected and clean_uuid:
        try:
            row = await db_manager.fetchrow(
                """
                SELECT id, draft_id, scan_id, review_id, passport_hash, status,
                       metadata_snapshot, created_at
                FROM passports
                WHERE id = $1;
                """,
                clean_uuid,
            )
            if row:
                snapshot = row["metadata_snapshot"]
                if isinstance(snapshot, str):
                    try:
                        snapshot = json.loads(snapshot)
                    except Exception:
                        snapshot = {}

                computed_hash = compute_canonical_passport_hash(snapshot)
                hash_verified = (computed_hash == row["passport_hash"])
                applied_policies = snapshot.get("applied_policy_versions") or snapshot.get("policies") or []

                return ContentPassportResult(
                    found=True,
                    id=str(row["id"]),
                    draft_id=str(row["draft_id"]),
                    scan_id=str(row["scan_id"]),
                    review_id=str(row["review_id"]),
                    passport_hash=row["passport_hash"],
                    status=row["status"],
                    metadata_snapshot=snapshot,
                    applied_policy_versions=applied_policies if isinstance(applied_policies, list) else [],
                    hash_verified=hash_verified,
                    created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
                )
        except Exception as exc:
            logger.warning("Database error fetching passport: %s", exc)

    # 2. In-memory fallback
    matching = _mock_passports.get(clean_id_str)
    if not matching:
        # Search by lowercase string
        for pid, pdata in _mock_passports.items():
            if pid.lower() == clean_id_str.lower():
                matching = pdata
                break

    if not matching:
        return ContentPassportResult(
            found=False,
            id=clean_id_str,
            error=f"Content Passport with ID '{clean_id_str}' was not found.",
        )

    snapshot = matching.get("metadata_snapshot", {})
    stored_hash = matching.get("passport_hash", "")
    computed_hash = compute_canonical_passport_hash(snapshot)
    hash_verified = (computed_hash == stored_hash)

    applied_policies = snapshot.get("applied_policy_versions") or snapshot.get("policies") or []
    if not isinstance(applied_policies, list):
        applied_policies = []

    return ContentPassportResult(
        found=True,
        id=matching["id"],
        draft_id=str(matching.get("draft_id", "")),
        scan_id=str(matching.get("scan_id", "")),
        review_id=str(matching.get("review_id", "")),
        passport_hash=stored_hash,
        status=matching.get("status", "valid"),
        metadata_snapshot=snapshot,
        applied_policy_versions=applied_policies,
        hash_verified=hash_verified,
        created_at=str(matching.get("created_at", "")),
    )


# ---------------------------------------------------------------------------
# Tool 4: verify_passport
# ---------------------------------------------------------------------------

async def verify_passport(
    passport_id: Optional[Union[str, UUID]] = None,
    passport_hash: Optional[str] = None,
    metadata_snapshot: Optional[Dict[str, Any]] = None,
) -> VerifyPassportResult:
    """Cryptographically verify the integrity of a Content Passport certificate.
    
    Verifies that the stored hash matches the deterministic SHA-256 hash of the
    canonically sorted metadata snapshot.
    Returns status: VALID, TAMPERED, or NOT_FOUND.
    """
    if passport_id:
        passport_result = await get_passport(passport_id)
        if not passport_result.found:
            return VerifyPassportResult(
                passport_id=str(passport_id),
                status="NOT_FOUND",
                hash_verified=False,
                stored_hash=None,
                computed_hash=None,
                explanation=f"Content Passport '{passport_id}' not found.",
            )

        stored = passport_result.passport_hash or ""
        snapshot = passport_result.metadata_snapshot or {}
        computed = compute_canonical_passport_hash(snapshot)

        if passport_result.hash_verified:
            return VerifyPassportResult(
                passport_id=str(passport_id),
                status="VALID",
                hash_verified=True,
                stored_hash=stored,
                computed_hash=computed,
                explanation="Content Passport hash matches canonical metadata snapshot. Integrity confirmed.",
            )
        else:
            return VerifyPassportResult(
                passport_id=str(passport_id),
                status="TAMPERED",
                hash_verified=False,
                stored_hash=stored,
                computed_hash=computed,
                explanation=(
                    f"Cryptographic hash mismatch! Content Passport has been tampered with or corrupted. "
                    f"Stored: '{stored}', Computed: '{computed}'."
                ),
            )

    # Verification from raw input snapshot & hash
    if passport_hash is not None and metadata_snapshot is not None:
        computed = compute_canonical_passport_hash(metadata_snapshot)
        matches = (computed.lower() == passport_hash.lower())
        if matches:
            return VerifyPassportResult(
                passport_id=None,
                status="VALID",
                hash_verified=True,
                stored_hash=passport_hash,
                computed_hash=computed,
                explanation="Provided hash matches canonical snapshot hash. Integrity confirmed.",
            )
        else:
            return VerifyPassportResult(
                passport_id=None,
                status="TAMPERED",
                hash_verified=False,
                stored_hash=passport_hash,
                computed_hash=computed,
                explanation=(
                    f"Cryptographic hash mismatch! Stored: '{passport_hash}', "
                    f"Computed: '{computed}'."
                ),
            )

    return VerifyPassportResult(
        passport_id=None,
        status="NOT_FOUND",
        hash_verified=False,
        stored_hash=None,
        computed_hash=None,
        explanation="Either passport_id or (passport_hash and metadata_snapshot) must be provided.",
    )


# ---------------------------------------------------------------------------
# Tool 5: explain_finding
# ---------------------------------------------------------------------------

async def explain_finding(
    finding_id: Optional[Union[str, UUID]] = None,
    scan_id: Optional[Union[str, UUID]] = None,
    finding_index: Optional[int] = None,
    finding: Optional[Finding] = None,
) -> ExplainFindingResult:
    """Explain a compliance finding, verify verbatim quote provenance, and guide remediation.
    
    Enforces 'No receipt, no flag':
    - Resolves the exact cited policy card and version.
    - Checks whether source_quote appears verbatim in the approved policy text.
    - Sets evidence_provenance to 'VERIFIED' only on exact quote match.
    - If quote is fabricated or mismatched, marks 'UNVERIFIED / HUMAN_REVIEW_REQUIRED'.
    """
    target_finding: Optional[Finding] = finding

    # 1. Resolve finding by ID or scan index if not directly passed
    if not target_finding:
        if finding_id and db_manager.is_connected:
            try:
                row = await db_manager.fetchrow(
                    """
                    SELECT id, scan_id, policy_card_id, policy_version, category,
                           severity, matched_text, source_quote, explanation,
                           suggested_fix, confidence, is_verified
                    FROM findings
                    WHERE id = $1;
                    """,
                    UUID(str(finding_id).strip()),
                )
                if row:
                    target_finding = Finding(
                        policy_card_id=str(row["policy_card_id"] or ""),
                        policy_version=str(row["policy_version"]),
                        category=row["category"],
                        severity=row["severity"],
                        matched_text=row["matched_text"],
                        source_quote=row["source_quote"],
                        explanation=row["explanation"],
                        suggested_fix=row["suggested_fix"] or "",
                        confidence=float(row["confidence"]),
                        is_verified=bool(row["is_verified"]),
                    )
            except Exception as exc:
                logger.warning("Error fetching finding by ID: %s", exc)

        elif scan_id and db_manager.is_connected:
            try:
                idx = finding_index or 0
                rows = await db_manager.fetch(
                    """
                    SELECT id, scan_id, policy_card_id, policy_version, category,
                           severity, matched_text, source_quote, explanation,
                           suggested_fix, confidence, is_verified
                    FROM findings
                    WHERE scan_id = $1
                    ORDER BY created_at ASC;
                    """,
                    UUID(str(scan_id).strip()),
                )
                if rows and 0 <= idx < len(rows):
                    row = rows[idx]
                    target_finding = Finding(
                        policy_card_id=str(row["policy_card_id"] or ""),
                        policy_version=str(row["policy_version"]),
                        category=row["category"],
                        severity=row["severity"],
                        matched_text=row["matched_text"],
                        source_quote=row["source_quote"],
                        explanation=row["explanation"],
                        suggested_fix=row["suggested_fix"] or "",
                        confidence=float(row["confidence"]),
                        is_verified=bool(row["is_verified"]),
                    )
            except Exception as exc:
                logger.warning("Error fetching findings by scan_id: %s", exc)

    if not target_finding:
        return ExplainFindingResult(
            found=False,
            finding_id=str(finding_id) if finding_id else None,
            scan_id=str(scan_id) if scan_id else None,
            evidence_provenance="HUMAN_REVIEW_REQUIRED",
            is_verified=False,
            remediation_guidance="Target finding could not be located in database or scan memory.",
            error=f"Finding '{finding_id or scan_id}' not found.",
        )

    # 2. Look up the exact referenced policy card and version
    policy_lookup = await get_policy_details(
        policy_id=target_finding.policy_card_id,
        version=target_finding.policy_version,
    )

    if not policy_lookup.found or not policy_lookup.policy:
        return ExplainFindingResult(
            found=True,
            finding_id=str(finding_id) if finding_id else None,
            scan_id=str(scan_id) if scan_id else None,
            category=target_finding.category,
            severity=target_finding.severity,
            matched_text=target_finding.matched_text,
            policy_card_id=target_finding.policy_card_id,
            policy_version=target_finding.policy_version,
            verbatim_source_quote=target_finding.source_quote,
            evidence_provenance="UNVERIFIED",
            is_verified=False,
            remediation_guidance=(
                f"Finding cites policy '{target_finding.policy_card_id}' (version {target_finding.policy_version}), "
                f"which does not exist in the approved policy library. "
                f"Human compliance review required before taking enforcement action."
            ),
            error=f"Cited policy card '{target_finding.policy_card_id}' v{target_finding.policy_version} not found in library.",
        )

    policy_card = policy_lookup.policy

    # 3. Verify verbatim source quotation ("No receipt, no flag")
    quote = target_finding.source_quote.strip() if target_finding.source_quote else ""
    norm_quote = normalize_text_for_comparison(quote)
    norm_rule = normalize_text_for_comparison(policy_card.rule_text)
    norm_source = normalize_text_for_comparison(policy_card.source_quote)

    quote_verified = False
    if norm_quote and (norm_quote.lower() in norm_rule.lower() or norm_quote.lower() in norm_source.lower()):
        quote_verified = True
    else:
        # Check within individual structured rules
        for r_dict in policy_card.rules:
            if isinstance(r_dict, dict):
                r_quote = normalize_text_for_comparison(r_dict.get("quote", ""))
                if norm_quote and norm_quote.lower() in r_quote.lower():
                    quote_verified = True
                    break

    if not quote_verified:
        return ExplainFindingResult(
            found=True,
            finding_id=str(finding_id) if finding_id else None,
            scan_id=str(scan_id) if scan_id else None,
            category=target_finding.category,
            severity=target_finding.severity,
            matched_text=target_finding.matched_text,
            policy_card_id=str(policy_card.id),
            policy_version=str(policy_card.version),
            verbatim_source_quote=target_finding.source_quote,
            evidence_provenance="UNVERIFIED",
            is_verified=False,
            remediation_guidance=(
                f"Evidence provenance check failed: Cited quotation '{target_finding.source_quote}' "
                f"does NOT appear verbatim in policy '{policy_card.title}' (v{policy_card.version}). "
                f"Under the 'No receipt, no flag' rule, this finding cannot be automatically enforced. "
                f"Requires human legal/compliance review."
            ),
            details={
                "policy_title": policy_card.title,
                "policy_rule_text": policy_card.rule_text,
                "quote_matched": False,
            },
        )

    # 4. Generate specific remediation guidance based on rule category
    cat = (target_finding.category or "").lower()
    matched = target_finding.matched_text

    if "terminolog" in cat:
        approved_term = policy_card.approved_value or "approved terminology"
        guidance = (
            f"Replace non-compliant term '{matched}' with '{approved_term}'. "
            f"Brand policy '{policy_card.title}' states: \"{policy_card.source_quote}\""
        )
    elif "offer" in cat:
        guidance = (
            f"Offer reference '{matched}' is expired or outside the approved promotion window. "
            f"Check active offer dates: \"{policy_card.source_quote}\". "
            f"Update creative copy to active campaign terms."
        )
    elif "claim" in cat or "unsupported" in cat:
        guidance = (
            f"Marketing claim '{matched}' requires certified substantiation documentation. "
            f"Brand policy '{policy_card.title}' requires: \"{policy_card.source_quote}\". "
            f"Attach verified evidence receipt before submitting for human approval."
        )
    elif "fact" in cat or "numerical" in cat:
        guidance = (
            f"Numerical claim '{matched}' exceeds authorized limits. "
            f"Policy rule states: \"{policy_card.source_quote}\". "
            f"Adjust figures to conform to approved limit ({policy_card.approved_value or 'authorized maximum'})."
        )
    else:
        guidance = (
            f"Revise '{matched}' to comply with policy '{policy_card.title}' (v{policy_card.version}). "
            f"Policy citation: \"{policy_card.source_quote}\". "
            f"Suggested fix: {target_finding.suggested_fix or 'Adjust copy to align with brand guidelines.'}"
        )

    return ExplainFindingResult(
        found=True,
        finding_id=str(finding_id) if finding_id else None,
        scan_id=str(scan_id) if scan_id else None,
        category=target_finding.category,
        severity=target_finding.severity,
        matched_text=target_finding.matched_text,
        policy_card_id=str(policy_card.id),
        policy_version=str(policy_card.version),
        verbatim_source_quote=target_finding.source_quote,
        evidence_provenance="VERIFIED",
        is_verified=True,
        remediation_guidance=guidance,
        details={
            "policy_title": policy_card.title,
            "policy_key": policy_card.policy_key,
            "policy_card_type": policy_card.card_type.value,
            "quote_matched": True,
            "suggested_fix": target_finding.suggested_fix,
        },
    )
