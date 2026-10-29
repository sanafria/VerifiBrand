"""Merkle Ledger Schemas and Types for BrandLedger.

Defines Pydantic models for Merkle tree structures, inclusion proofs,
and verification results.
"""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class ProofDirection(str, Enum):
    """Direction of sibling hash in Merkle tree path."""
    LEFT = "left"
    RIGHT = "right"


class MerkleProofStep(BaseModel):
    """Single step along an inclusion proof path to the Merkle root."""
    sibling_hash: str = Field(
        ...,
        description="64-character SHA-256 hex string of the sibling node",
        min_length=64,
        max_length=64,
    )
    direction: ProofDirection = Field(
        ...,
        description="Position of the sibling relative to the current path node ('left' or 'right')",
    )

    @field_validator("sibling_hash")
    @classmethod
    def validate_hex_hash(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if len(v_clean) != 64:
            raise ValueError(f"sibling_hash must be exactly 64 hex characters, got length {len(v_clean)}")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError(f"sibling_hash contains invalid hexadecimal characters: '{v}'")
        return v_clean


class MerkleProof(BaseModel):
    """Cryptographic inclusion proof demonstrating a leaf is part of the Merkle root."""
    leaf_hash: str = Field(
        ...,
        description="64-character SHA-256 hex string of the target leaf",
        min_length=64,
        max_length=64,
    )
    leaf_index: int = Field(
        ...,
        ge=0,
        description="Zero-based index of the leaf in the Merkle tree",
    )
    total_leaves: int = Field(
        ...,
        ge=1,
        description="Total number of leaves in the tree at proof generation time",
    )
    root: str = Field(
        ...,
        description="Expected Merkle root calculated at proof generation time",
        min_length=64,
        max_length=64,
    )
    steps: List[MerkleProofStep] = Field(
        default_factory=list,
        description="Sequential proof steps from leaf to root",
    )

    @field_validator("leaf_hash", "root")
    @classmethod
    def validate_hex_hash(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if len(v_clean) != 64:
            raise ValueError(f"Hash must be exactly 64 hex characters, got length {len(v_clean)}")
        try:
            int(v_clean, 16)
        except ValueError:
            raise ValueError(f"Hash contains invalid hexadecimal characters: '{v}'")
        return v_clean


class MerkleProofVerificationResult(BaseModel):
    """Machine-readable result of Merkle inclusion proof verification."""
    verified: bool = Field(
        ...,
        description="True if mathematically proven that leaf is included in the expected root",
    )
    leaf_hash: str = Field(
        ...,
        description="The normalized leaf hash that was verified",
    )
    computed_root: str = Field(
        ...,
        description="The Merkle root computed step-by-step from the leaf and proof path",
    )
    expected_root: str = Field(
        ...,
        description="The target Merkle root against which verification was performed",
    )
    root_matches: bool = Field(
        ...,
        description="True if computed_root == expected_root",
    )
    reason: str = Field(
        ...,
        description="Detailed human-readable explanation of verification outcome",
    )


class MerkleTreeResponse(BaseModel):
    """Public representation of a constructed Merkle tree and its root."""
    root: Optional[str] = Field(
        None,
        description="64-character SHA-256 Merkle root (or None if tree is empty)",
    )
    total_leaves: int = Field(
        ...,
        ge=0,
        description="Total number of leaves in the tree",
    )
    leaf_hashes: List[str] = Field(
        default_factory=list,
        description="Ordered list of leaf hashes in the tree",
    )
    is_empty: bool = Field(
        default=False,
        description="True if the tree has zero entries",
    )
