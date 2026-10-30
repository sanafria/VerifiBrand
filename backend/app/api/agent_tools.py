"""Agent Tools API Router for BrandLedger.

Exposes authoritative, deterministic REST endpoints for AI agents and external callers:
- POST /api/tools/scan_creative: Run deterministic compliance scan with evidence citations.
- GET  /api/tools/findings: Retrieve findings by scan_id or draft_id.
- POST /api/tools/verify_merkle_proof: Independently verify Merkle inclusion proof.

Member 2 (Nimra) Policy & Passport Agent Tools:
- GET  /api/tools/policies: Retrieve active/approved policies for AI agent rules reasoning.
- GET  /api/tools/policies/{policy_id}: Retrieve policy details or historical version snapshot.
- GET  /api/tools/passports/{passport_id}: Retrieve issued Content Passport with hash verification.
- POST /api/tools/passports/verify: Cryptographically verify Content Passport hash against snapshot.
- POST /api/tools/findings/explain: Explain compliance finding and verify quote provenance ("No receipt, no flag").
- GET  /api/tools/findings/{finding_id}/explain: Convenience route to explain a persisted finding.

Security:
- Protected with AGENT_API_KEY authentication (Bearer or X-Agent-Key).
- Constant-time token verification via secrets.compare_digest.
"""

import secrets
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.schemas.agent_tools import (
    ContentPassportResult,
    ExplainFindingInput,
    ExplainFindingResult,
    GetApprovedPoliciesResult,
    GetFindingsResult,
    PolicyDetailsResult,
    ScanCreativeInput,
    ScanCreativeResult,
    VerifyPassportInput,
    VerifyPassportResult,
)
from backend.app.schemas.merkle import MerkleProofVerificationResult
from backend.app.services.agent_tools import (
    explain_finding,
    get_approved_policies,
    get_findings,
    get_passport,
    get_policy_details,
    scan_creative,
    verify_merkle_proof,
    verify_passport,
)

# ---------------------------------------------------------------------------
# Agent Authentication
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-Agent-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)


def verify_agent_auth(
    header_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth),
) -> bool:
    """Validate agent authentication credentials when AGENT_API_KEY is configured.

    Accepts:
    - X-Agent-Key header
    - Authorization: Bearer <key> header
    Uses secrets.compare_digest for constant-time comparison to prevent timing attacks.
    """
    expected_key = getattr(settings, "AGENT_API_KEY", "") or ""
    if not expected_key:
        return True  # Permissive if not configured (e.g. local dev / open test mode)

    provided_key = header_key or (bearer.credentials if bearer else None)
    if not provided_key or not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized agent request: Invalid or missing Agent API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


router = APIRouter(
    prefix="/tools",
    tags=["Agent Tools"],
    dependencies=[Depends(verify_agent_auth)],
)


class VerifyMerkleProofRequest(BaseModel):
    """Payload to independently verify a Merkle inclusion proof."""
    leaf: Any = Field(..., description="64-character SHA-256 leaf hash OR original ledger entry dict/string")
    proof: Any = Field(..., description="MerkleProof object, dict, or list of proof steps")
    expected_root: str = Field(..., description="Expected 64-character SHA-256 Merkle root")


# ---------------------------------------------------------------------------
# Member 4 Endpoints: Scan, Findings, Merkle
# ---------------------------------------------------------------------------

@router.post(
    "/scan_creative",
    response_model=ScanCreativeResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Scan Creative",
    description="Scan creative content against approved brand policies and return authoritative findings and compliance decision (PASS, BLOCK, HUMAN_REVIEW).",
)
async def tool_scan_creative(payload: ScanCreativeInput) -> ScanCreativeResult:
    """Execute authoritative deterministic compliance scan for creative content."""
    return await scan_creative(creative_input=payload)


@router.get(
    "/findings",
    response_model=GetFindingsResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Get Findings",
    description="Retrieve persisted compliance findings for an existing scan or creative draft.",
)
async def tool_get_findings(
    scan_id: Optional[str] = Query(None, description="Target scan UUID"),
    draft_id: Optional[str] = Query(None, description="Target draft UUID"),
) -> GetFindingsResult:
    """Retrieve persisted findings by scan_id or draft_id."""
    return await get_findings(scan_id=scan_id, draft_id=draft_id)


@router.post(
    "/verify_merkle_proof",
    response_model=MerkleProofVerificationResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Verify Merkle Proof",
    description="Independently verify a Merkle inclusion proof mathematically against an expected root.",
)
def tool_verify_merkle_proof(payload: VerifyMerkleProofRequest) -> MerkleProofVerificationResult:
    """Independently calculate and verify Merkle inclusion proof."""
    return verify_merkle_proof(
        leaf=payload.leaf,
        proof=payload.proof,
        expected_root=payload.expected_root,
    )


# ---------------------------------------------------------------------------
# Member 2 Endpoints: Policy & Content Passport Agent Tools
# ---------------------------------------------------------------------------

@router.get(
    "/policies",
    response_model=GetApprovedPoliciesResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Get Approved Policies",
    description="Retrieve all active, approved policy cards with stable IDs, versions, rules, and verbatim source quotes. Excludes draft, inactive, and archived cards.",
)
async def tool_get_approved_policies(
    card_type: Optional[str] = Query(None, description="Optional category filter (e.g., terminology, offer, claim, fact)"),
) -> GetApprovedPoliciesResult:
    """Retrieve active/approved brand policies for agent decisioning."""
    return await get_approved_policies(card_type=card_type)


@router.get(
    "/policies/{policy_id}",
    response_model=PolicyDetailsResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Get Policy Details",
    description="Retrieve details of a policy card by UUID or stable policy_key. Supports historical version lookup via ?version=X. Strictly returns 404 if the requested version does not exist.",
)
async def tool_get_policy_details(
    policy_id: str,
    version: Optional[str] = Query(None, description="Optional historical version number/string (e.g. 1 or 2)"),
) -> PolicyDetailsResult:
    """Retrieve policy details or immutable historical snapshot."""
    result = await get_policy_details(policy_id=policy_id, version=version)
    if not result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or f"Policy '{policy_id}' not found.",
        )
    return result


@router.get(
    "/passports/{passport_id}",
    response_model=ContentPassportResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Get Passport",
    description="Retrieve an issued Content Passport certificate, its frozen metadata snapshot, applied policy versions, and verified cryptographic hash status.",
)
async def tool_get_passport(passport_id: str) -> ContentPassportResult:
    """Retrieve Content Passport certificate and verify its cryptographic hash."""
    result = await get_passport(passport_id=passport_id)
    if not result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or f"Content Passport '{passport_id}' not found.",
        )
    return result


@router.post(
    "/passports/verify",
    response_model=VerifyPassportResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Verify Passport",
    description="Cryptographically verify a Content Passport's SHA-256 hash against its canonical metadata snapshot. Returns status: VALID, TAMPERED, or NOT_FOUND.",
)
async def tool_verify_passport(payload: VerifyPassportInput) -> VerifyPassportResult:
    """Cryptographically verify Content Passport hash integrity."""
    result = await verify_passport(
        passport_id=payload.passport_id,
        passport_hash=payload.passport_hash,
        metadata_snapshot=payload.metadata_snapshot,
    )
    if result.status == "NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.explanation,
        )
    return result


@router.post(
    "/findings/explain",
    response_model=ExplainFindingResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Explain Finding",
    description="Explain a compliance finding, verify verbatim source quote provenance ('No receipt, no flag'), and provide actionable remediation guidance.",
)
async def tool_explain_finding(payload: ExplainFindingInput) -> ExplainFindingResult:
    """Explain finding and verify quote provenance."""
    result = await explain_finding(
        finding_id=payload.finding_id,
        scan_id=payload.scan_id,
        finding_index=payload.finding_index,
        finding=payload.finding,
    )
    if not result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or "Finding could not be found.",
        )
    return result


@router.get(
    "/findings/{finding_id}/explain",
    response_model=ExplainFindingResult,
    status_code=status.HTTP_200_OK,
    summary="Agent Tool: Explain Finding by ID",
    description="Explain an existing persisted finding by UUID.",
)
async def tool_explain_finding_by_id(finding_id: str) -> ExplainFindingResult:
    """Explain a specific finding by ID."""
    result = await explain_finding(finding_id=finding_id)
    if not result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or f"Finding '{finding_id}' not found.",
        )
    return result
