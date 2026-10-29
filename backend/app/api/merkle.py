"""Merkle Ledger API Router for BrandLedger.

Exposes endpoints for:
- GET /api/merkle/tree: Inspect the authoritative Merkle tree for all valid Passports.
- GET /api/merkle/proof/{passport_id}: Retrieve cryptographic inclusion proof for a passport.
- POST /api/merkle/verify: Independently verify a Merkle inclusion proof.
"""

from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.schemas.merkle import (
    MerkleProof,
    MerkleProofVerificationResult,
    MerkleTreeResponse,
)
from backend.app.services.merkle_ledger import (
    get_database_passport_ledger,
    verify_merkle_proof,
)

router = APIRouter(prefix="/merkle", tags=["Merkle Ledger"])


class VerifyProofRequest(BaseModel):
    """Payload to independently verify a Merkle inclusion proof."""
    leaf: Any = Field(..., description="64-character SHA-256 leaf hash OR original ledger entry")
    proof: Any = Field(..., description="MerkleProof object or dictionary containing steps")
    expected_root: str = Field(..., description="Expected 64-character Merkle root")


@router.get(
    "/tree",
    response_model=MerkleTreeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Merkle Ledger Tree",
    description="Retrieve the current Merkle tree root and leaf hashes computed over all valid Content Passports.",
)
async def get_merkle_tree() -> MerkleTreeResponse:
    """Construct and return the current Merkle ledger tree."""
    tree = await get_database_passport_ledger()
    return tree.to_response()


@router.get(
    "/proof/{passport_id}",
    response_model=MerkleProof,
    status_code=status.HTTP_200_OK,
    summary="Get Passport Merkle Proof",
    description="Retrieve the cryptographic Merkle inclusion proof for a specific issued Content Passport.",
)
async def get_passport_proof(passport_id: UUID) -> MerkleProof:
    """Generate and return inclusion proof for a specific passport."""
    tree = await get_database_passport_ledger()
    if tree.is_empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merkle ledger has zero valid passport entries.",
        )

    # In database passport tree, entries are passport hashes or IDs
    # Query passport hash first
    from backend.app.db import db_manager
    if not db_manager.is_connected:
        try:
            await db_manager.connect()
        except Exception:
            pass

    row = await db_manager.fetchrow(
        "SELECT passport_hash FROM passports WHERE id = $1 AND status = 'valid';",
        passport_id,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valid Content Passport with ID '{passport_id}' not found.",
        )

    passport_hash = row["passport_hash"]
    try:
        return tree.get_proof_by_entry(passport_hash)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to generate proof for passport: {str(exc)}",
        )


@router.post(
    "/verify",
    response_model=MerkleProofVerificationResult,
    status_code=status.HTTP_200_OK,
    summary="Verify Merkle Proof",
    description="Independently verify a Merkle inclusion proof mathematically against a root.",
)
def verify_proof_endpoint(payload: VerifyProofRequest) -> MerkleProofVerificationResult:
    """Independently calculate and verify inclusion proof."""
    return verify_merkle_proof(
        leaf=payload.leaf,
        proof=payload.proof,
        expected_root=payload.expected_root,
    )
