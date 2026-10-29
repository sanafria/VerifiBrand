"""Merkle Ledger Service for BrandLedger.

Provides a deterministic, cryptographic Merkle tree implementation for
content passports and compliance audit records.

Architecture & Cryptographic Principles:
1. Hashing & Domain Separation:
   - Uses SHA-256 (hashlib.sha256).
   - Domain separation prevents second-preimage attacks:
     * Leaf hashes: H(0x00 || canonical_payload)
     * Internal node hashes: H(0x01 || left_hash || right_hash)
2. Deterministic Serialization:
   - Structured JSON objects are serialized canonically:
     * Alphabetically sorted keys (sort_keys=True)
     * Compact separators (',', ':')
     * Strict UTF-8 encoding
   - Compatible with compute_canonical_passport_hash in review_service.py.
3. Odd-Node Handling:
   - If a tree layer has an odd number of nodes, the last node is paired with
     a duplicate of itself: H(0x01 || last_node || last_node).
   - The inclusion proof for the last node includes its duplicate sibling with
     direction='right'.
4. Empty & Single-Leaf Trees:
   - Empty tree: total_leaves=0, root=None. Proof generation raises ValueError.
   - Single-leaf tree: root is the leaf hash itself; proof path is empty ([]).
5. Ledger Integrity & Limitations:
   - A Merkle root acts as a cryptographic accumulator over all current ledger entries.
   - Any modification or tampering with a leaf alters the computed root, allowing
     instant mathematical detection.
   - Note on Security: Storing a Merkle root in PostgreSQL provides tamper-evidence
     against row-level manipulation, but does not provide decentralized immutability
     without external witness anchoring (e.g., transparency log or external timestamping).
"""

from datetime import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from backend.app.db import db_manager
from backend.app.schemas.merkle import (
    MerkleProof,
    MerkleProofStep,
    MerkleProofVerificationResult,
    MerkleTreeResponse,
    ProofDirection,
)

logger = logging.getLogger(__name__)

# Domain separation prefixes
LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


# ---------------------------------------------------------------------------
# Cryptographic Hashing Utilities
# ---------------------------------------------------------------------------

def canonical_serialize(data: Any) -> bytes:
    """Deterministically serialize structured data into canonical UTF-8 bytes.

    Matches canonical JSON rules:
    - Dict keys sorted recursively
    - Compact separators without whitespace
    - UTF-8 encoding
    """
    if isinstance(data, bytes):
        return data

    def _canonical_obj(item: Any) -> Any:
        if isinstance(item, dict):
            return {str(k): _canonical_obj(v) for k, v in sorted(item.items())}
        if isinstance(item, (list, tuple)):
            return [_canonical_obj(x) for x in item]
        if isinstance(item, (datetime,)):
            return item.isoformat()
        if isinstance(item, UUID):
            return str(item)
        return item

    clean_obj = _canonical_obj(data)
    canonical_str = json.dumps(
        clean_obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return canonical_str.encode("utf-8")


def is_valid_sha256_hex(val: Any) -> bool:
    """Check if value is a valid 64-character hexadecimal SHA-256 string."""
    if not isinstance(val, str) or len(val.strip()) != 64:
        return False
    try:
        int(val.strip(), 16)
        return True
    except ValueError:
        return False


def hash_leaf(data: Any) -> str:
    """Compute domain-separated SHA-256 leaf hash: SHA-256(0x00 || payload).

    Supports:
    - Structured dicts / models (canonically serialized)
    - Raw strings
    - Raw bytes
    - Pre-existing passport hashes (treated as 32-byte hex digests or normalized strings)
    """
    if isinstance(data, str) and is_valid_sha256_hex(data):
        # Already a 64-char hex hash (e.g. passport_hash)
        payload_bytes = bytes.fromhex(data.strip().lower())
    elif isinstance(data, (dict, list)):
        payload_bytes = canonical_serialize(data)
    elif isinstance(data, str):
        payload_bytes = data.encode("utf-8")
    elif isinstance(data, bytes):
        payload_bytes = data
    else:
        payload_bytes = str(data).encode("utf-8")

    hasher = hashlib.sha256()
    hasher.update(LEAF_PREFIX)
    hasher.update(payload_bytes)
    return hasher.hexdigest().lower()


def hash_internal_nodes(left_hex: str, right_hex: str) -> str:
    """Compute domain-separated internal node hash: SHA-256(0x01 || left || right).

    Both inputs must be valid 64-character hex strings.
    """
    if not is_valid_sha256_hex(left_hex):
        raise ValueError(f"Invalid left child hash for internal node: '{left_hex}'")
    if not is_valid_sha256_hex(right_hex):
        raise ValueError(f"Invalid right child hash for internal node: '{right_hex}'")

    left_bytes = bytes.fromhex(left_hex.strip().lower())
    right_bytes = bytes.fromhex(right_hex.strip().lower())

    hasher = hashlib.sha256()
    hasher.update(NODE_PREFIX)
    hasher.update(left_bytes)
    hasher.update(right_bytes)
    return hasher.hexdigest().lower()


# ---------------------------------------------------------------------------
# Merkle Tree Implementation
# ---------------------------------------------------------------------------

class MerkleTree:
    """Deterministic binary Merkle Tree for verifiable ledger entries."""

    def __init__(self, entries: Optional[List[Any]] = None) -> None:
        """Construct a Merkle tree from an ordered collection of ledger entries."""
        self.raw_entries: List[Any] = list(entries) if entries else []
        self.leaves: List[str] = []
        self.levels: List[List[str]] = []
        self.root: Optional[str] = None

        if self.raw_entries:
            self._build_tree()

    def _build_tree(self) -> None:
        """Build the binary Merkle tree layer by layer."""
        self.leaves = [hash_leaf(e) for e in self.raw_entries]
        current_level = list(self.leaves)
        self.levels = [current_level]

        if len(current_level) == 1:
            self.root = current_level[0]
            return

        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd count, duplicate the last node
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = current_level[i]
                parent = hash_internal_nodes(left, right)
                next_level.append(parent)

            self.levels.append(next_level)
            current_level = next_level

        self.root = self.levels[-1][0] if self.levels else None

    @property
    def total_leaves(self) -> int:
        """Return total number of leaves in the tree."""
        return len(self.leaves)

    @property
    def is_empty(self) -> bool:
        """Return True if the tree has no entries."""
        return len(self.leaves) == 0

    def get_root(self) -> Optional[str]:
        """Return 64-character hex Merkle root, or None if tree is empty."""
        return self.root

    def get_proof(self, leaf_index: int) -> MerkleProof:
        """Generate a cryptographic inclusion proof for a leaf by index."""
        if self.is_empty:
            raise ValueError("Cannot generate inclusion proof for an empty Merkle tree.")

        if leaf_index < 0 or leaf_index >= self.total_leaves:
            raise IndexError(
                f"Leaf index {leaf_index} out of bounds. Valid range: [0, {self.total_leaves - 1}]."
            )

        target_leaf = self.leaves[leaf_index]

        # Single-leaf tree: root is the leaf hash, proof path has zero steps
        if self.total_leaves == 1:
            return MerkleProof(
                leaf_hash=target_leaf,
                leaf_index=0,
                total_leaves=1,
                root=self.root or target_leaf,
                steps=[],
            )

        steps: List[MerkleProofStep] = []
        current_idx = leaf_index

        for level in self.levels[:-1]:
            if current_idx % 2 == 0:
                # Target is left child, sibling is on the right
                if current_idx + 1 < len(level):
                    sibling = level[current_idx + 1]
                else:
                    sibling = level[current_idx]  # duplicated self
                direction = ProofDirection.RIGHT
            else:
                # Target is right child, sibling is on the left
                sibling = level[current_idx - 1]
                direction = ProofDirection.LEFT

            steps.append(MerkleProofStep(
                sibling_hash=sibling,
                direction=direction,
            ))
            current_idx = current_idx // 2

        return MerkleProof(
            leaf_hash=target_leaf,
            leaf_index=leaf_index,
            total_leaves=self.total_leaves,
            root=self.root or "",
            steps=steps,
        )

    def get_proof_by_leaf_hash(self, leaf_hash: str) -> MerkleProof:
        """Find leaf by hash and return its inclusion proof."""
        clean_hash = leaf_hash.strip().lower()
        try:
            idx = self.leaves.index(clean_hash)
            return self.get_proof(idx)
        except ValueError:
            raise ValueError(f"Leaf hash '{clean_hash}' does not exist in Merkle tree.")

    def get_proof_by_entry(self, entry: Any) -> MerkleProof:
        """Compute leaf hash for entry and return its inclusion proof."""
        target_hash = hash_leaf(entry)
        return self.get_proof_by_leaf_hash(target_hash)

    def to_response(self) -> MerkleTreeResponse:
        """Return Pydantic response representing the tree state."""
        return MerkleTreeResponse(
            root=self.root,
            total_leaves=self.total_leaves,
            leaf_hashes=list(self.leaves),
            is_empty=self.is_empty,
        )


# ---------------------------------------------------------------------------
# Proof Verification Logic
# ---------------------------------------------------------------------------

def verify_merkle_proof(
    leaf: Union[str, dict, Any],
    proof: Union[MerkleProof, dict, list],
    expected_root: str,
) -> MerkleProofVerificationResult:
    """Independently verify an inclusion proof against an expected Merkle root.

    Security Guarantees:
    - Never trusts caller-asserted results.
    - Independently recalculates the root step-by-step using domain separation.
    - Validates hash format (64 hex characters) and proof directions ('left'/'right').
    - Rejects malformed structures, tampered leaf data, tampered siblings, and mismatched roots.
    """
    # 1. Validate expected root format
    if not is_valid_sha256_hex(expected_root):
        return MerkleProofVerificationResult(
            verified=False,
            leaf_hash="",
            computed_root="",
            expected_root=str(expected_root),
            root_matches=False,
            reason=f"Invalid expected root: '{expected_root}'. Must be a 64-character hexadecimal SHA-256 hash.",
        )

    norm_expected_root = expected_root.strip().lower()

    # 2. Extract proof steps and target leaf hash
    steps_data: List[Union[MerkleProofStep, dict]] = []
    claimed_leaf_hash: Optional[str] = None

    if isinstance(proof, MerkleProof):
        steps_data = proof.steps
        claimed_leaf_hash = proof.leaf_hash
    elif isinstance(proof, dict):
        claimed_leaf_hash = proof.get("leaf_hash")
        raw_steps = proof.get("steps", [])
        if not isinstance(raw_steps, list):
            return MerkleProofVerificationResult(
                verified=False,
                leaf_hash=str(claimed_leaf_hash or ""),
                computed_root="",
                expected_root=norm_expected_root,
                root_matches=False,
                reason="Proof 'steps' field must be a list of step objects.",
            )
        steps_data = raw_steps
    elif isinstance(proof, list):
        steps_data = proof
    else:
        return MerkleProofVerificationResult(
            verified=False,
            leaf_hash="",
            computed_root="",
            expected_root=norm_expected_root,
            root_matches=False,
            reason=f"Unsupported proof format: {type(proof)}. Expected MerkleProof, dict, or list.",
        )

    # 3. Determine starting leaf hash
    norm_claimed = claimed_leaf_hash.strip().lower() if claimed_leaf_hash and is_valid_sha256_hex(claimed_leaf_hash) else None

    if norm_claimed:
        if isinstance(leaf, str) and leaf.strip().lower() == norm_claimed:
            # Caller provided the precomputed leaf hash directly
            current_hash = norm_claimed
        elif hash_leaf(leaf) == norm_claimed:
            # Caller provided the raw entry whose domain-separated hash matches
            current_hash = norm_claimed
        else:
            # Tampered or mismatched leaf data
            computed = hash_leaf(leaf)
            return MerkleProofVerificationResult(
                verified=False,
                leaf_hash=computed,
                computed_root="",
                expected_root=norm_expected_root,
                root_matches=False,
                reason=(
                    f"Leaf data mismatch: computed leaf hash '{computed}' "
                    f"does not match proof leaf hash '{norm_claimed}'."
                ),
            )
    else:
        # No claimed leaf hash in proof (e.g. raw list of steps):
        # If leaf is 64-char hex, use as leaf hash, else compute hash_leaf
        if isinstance(leaf, str) and is_valid_sha256_hex(leaf):
            current_hash = leaf.strip().lower()
        else:
            current_hash = hash_leaf(leaf)

    starting_leaf_hash = current_hash

    # 4. Handle zero-step proof (single leaf tree)
    if len(steps_data) == 0:
        matches = (current_hash == norm_expected_root)
        return MerkleProofVerificationResult(
            verified=matches,
            leaf_hash=starting_leaf_hash,
            computed_root=current_hash,
            expected_root=norm_expected_root,
            root_matches=matches,
            reason="Verified single-leaf Merkle root." if matches else "Leaf hash does not match expected single-leaf root.",
        )

    # 5. Iteratively compute root up the proof path
    for idx, step in enumerate(steps_data):
        if isinstance(step, MerkleProofStep):
            sibling = step.sibling_hash
            direction = step.direction.value if hasattr(step.direction, "value") else str(step.direction)
        elif isinstance(step, dict):
            sibling = step.get("sibling_hash")
            direction = step.get("direction")
        else:
            return MerkleProofVerificationResult(
                verified=False,
                leaf_hash=starting_leaf_hash,
                computed_root="",
                expected_root=norm_expected_root,
                root_matches=False,
                reason=f"Step at index {idx} is not a valid proof step object.",
            )

        if not sibling or not is_valid_sha256_hex(str(sibling)):
            return MerkleProofVerificationResult(
                verified=False,
                leaf_hash=starting_leaf_hash,
                computed_root="",
                expected_root=norm_expected_root,
                root_matches=False,
                reason=f"Step at index {idx} has invalid sibling_hash: '{sibling}'. Must be 64 hex characters.",
            )

        norm_direction = str(direction).strip().lower()
        if norm_direction not in ("left", "right"):
            return MerkleProofVerificationResult(
                verified=False,
                leaf_hash=starting_leaf_hash,
                computed_root="",
                expected_root=norm_expected_root,
                root_matches=False,
                reason=f"Step at index {idx} has invalid direction: '{direction}'. Must be 'left' or 'right'.",
            )

        try:
            if norm_direction == "left":
                current_hash = hash_internal_nodes(str(sibling).strip().lower(), current_hash)
            else:
                current_hash = hash_internal_nodes(current_hash, str(sibling).strip().lower())
        except Exception as exc:
            return MerkleProofVerificationResult(
                verified=False,
                leaf_hash=starting_leaf_hash,
                computed_root="",
                expected_root=norm_expected_root,
                root_matches=False,
                reason=f"Cryptographic error calculating step {idx}: {str(exc)}",
            )

    computed_root = current_hash
    matches = (computed_root == norm_expected_root)

    if matches:
        reason = (
            f"Successfully verified inclusion proof for leaf {starting_leaf_hash[:12]}... "
            f"against root {norm_expected_root[:12]}... across {len(steps_data)} steps."
        )
    else:
        reason = (
            f"Root mismatch: computed root '{computed_root}' != expected root '{norm_expected_root}'. "
            f"Record or proof path has been tampered with or does not belong to this tree."
        )

    return MerkleProofVerificationResult(
        verified=matches,
        leaf_hash=starting_leaf_hash,
        computed_root=computed_root,
        expected_root=norm_expected_root,
        root_matches=matches,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Database & Passport Integration
# ---------------------------------------------------------------------------

def build_merkle_tree_from_passports(passports: List[Dict[str, Any]]) -> MerkleTree:
    """Construct a Merkle tree from a collection of passport records or snapshots."""
    entries: List[Any] = []
    for p in passports:
        if isinstance(p, dict):
            # Prefer passport_hash if available, or metadata_snapshot
            if p.get("passport_hash"):
                entries.append(p["passport_hash"])
            elif p.get("metadata_snapshot"):
                entries.append(p["metadata_snapshot"])
            else:
                entries.append(p)
        else:
            entries.append(p)

    return MerkleTree(entries)


async def get_database_passport_ledger() -> MerkleTree:
    """Retrieve all issued passports from PostgreSQL and construct the authoritative Merkle tree.

    If database pool is unavailable or no passports exist, returns an empty MerkleTree.
    """
    if not db_manager.is_connected:
        try:
            await db_manager.connect()
        except Exception as exc:
            logger.warning("Could not connect to database pool for Merkle ledger: %s", exc)
            return MerkleTree([])

    try:
        rows = await db_manager.fetch(
            """
            SELECT id, draft_id, scan_id, review_id, passport_hash, status, created_at
            FROM passports
            WHERE status = 'valid'
            ORDER BY created_at ASC;
            """
        )
        passports = [dict(r) for r in rows]
        return build_merkle_tree_from_passports(passports)
    except Exception as exc:
        logger.error("Failed to query passports from database for Merkle ledger: %s", exc)
        return MerkleTree([])
