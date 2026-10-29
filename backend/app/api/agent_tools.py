"""Agent Tools API Router for BrandLedger.

Exposes REST endpoints for the three authoritative agent tools:
- POST /api/tools/scan_creative: Run deterministic compliance scan with evidence citations.
- GET  /api/tools/findings: Retrieve findings by scan_id or draft_id.
- POST /api/tools/verify_merkle_proof: Independently verify Merkle inclusion proof.
"""

from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.schemas.agent_tools import (
    GetFindingsResult,
    ScanCreativeInput,
    ScanCreativeResult,
)
from backend.app.schemas.merkle import MerkleProofVerificationResult
from backend.app.services.agent_tools import (
    get_findings,
    scan_creative,
    verify_merkle_proof,
)

router = APIRouter(prefix="/tools", tags=["Agent Tools"])


class VerifyMerkleProofRequest(BaseModel):
    """Payload to independently verify a Merkle inclusion proof."""
    leaf: Any = Field(..., description="64-character SHA-256 leaf hash OR original ledger entry dict/string")
    proof: Any = Field(..., description="MerkleProof object, dict, or list of proof steps")
    expected_root: str = Field(..., description="Expected 64-character SHA-256 Merkle root")


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
