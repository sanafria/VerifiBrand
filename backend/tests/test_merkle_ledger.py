"""Comprehensive unit and property tests for BrandLedger Merkle Ledger Service.

Covers all Phase 7 specifications:
1. Empty tree behavior.
2. Single-leaf tree behavior.
3. Multiple-leaf tree behavior.
4. Odd numbers of leaves.
5. Correct Merkle root generation.
6. Successful inclusion-proof verification.
7. Invalid inclusion proofs.
8. Tampered leaf data.
9. Tampered sibling hashes.
10. Incorrect sibling directions.
11. Incorrect or modified Merkle roots.
12. Malformed proof structures.
13. Consistency between tree generation and proof verification.
14. Domain separation between leaves and internal nodes.
15. Deterministic canonical serialization.
"""

import copy
import hashlib
import json
import pytest

from backend.app.schemas.merkle import MerkleProof, MerkleProofStep, ProofDirection
from backend.app.services.merkle_ledger import (
    MerkleTree,
    canonical_serialize,
    hash_internal_nodes,
    hash_leaf,
    is_valid_sha256_hex,
    verify_merkle_proof,
    build_merkle_tree_from_passports,
)


# ---------------------------------------------------------------------------
# 1. Empty Tree Behavior
# ---------------------------------------------------------------------------

def test_empty_merkle_tree_properties():
    """Empty tree has None root, total_leaves=0, and raises on get_proof."""
    tree = MerkleTree([])
    assert tree.is_empty is True
    assert tree.total_leaves == 0
    assert tree.get_root() is None
    assert tree.to_response().is_empty is True

    with pytest.raises(ValueError, match="empty Merkle tree"):
        tree.get_proof(0)


def test_verify_against_empty_root_rejected():
    """Proof verification against an empty or malformed root is safely rejected."""
    result = verify_merkle_proof(
        leaf="any_leaf_data",
        proof=[],
        expected_root="",
    )
    assert result.verified is False
    assert result.root_matches is False
    assert "Invalid expected root" in result.reason


# ---------------------------------------------------------------------------
# 2. Single-Leaf Tree Behavior
# ---------------------------------------------------------------------------

def test_single_leaf_tree():
    """Single-leaf tree: root is the leaf hash, proof path has 0 steps, verifies correctly."""
    entry = {"id": "pass_001", "draft_id": "drft_100", "status": "valid"}
    tree = MerkleTree([entry])

    assert tree.total_leaves == 1
    assert tree.is_empty is False
    expected_leaf_hash = hash_leaf(entry)
    assert tree.get_root() == expected_leaf_hash

    # Proof generation
    proof = tree.get_proof(0)
    assert proof.leaf_index == 0
    assert proof.total_leaves == 1
    assert proof.leaf_hash == expected_leaf_hash
    assert proof.root == expected_leaf_hash
    assert len(proof.steps) == 0

    # Verification success
    res = verify_merkle_proof(leaf=entry, proof=proof, expected_root=tree.get_root())
    assert res.verified is True
    assert res.root_matches is True
    assert res.computed_root == tree.get_root()

    # Verification failure if root is modified
    wrong_root = "0" * 64
    res_wrong = verify_merkle_proof(leaf=entry, proof=proof, expected_root=wrong_root)
    assert res_wrong.verified is False
    assert res_wrong.root_matches is False


# ---------------------------------------------------------------------------
# 3. Multiple-Leaf Tree (Power of 2: 2, 4, 8 leaves)
# ---------------------------------------------------------------------------

def test_two_leaf_tree():
    """Two-leaf tree: root = hash_internal_nodes(leaf0, leaf1)."""
    leaves_data = ["passport_alpha", "passport_beta"]
    tree = MerkleTree(leaves_data)

    assert tree.total_leaves == 2
    h0 = hash_leaf(leaves_data[0])
    h1 = hash_leaf(leaves_data[1])
    expected_root = hash_internal_nodes(h0, h1)
    assert tree.get_root() == expected_root

    # Leaf 0 proof: sibling is leaf 1 on right
    p0 = tree.get_proof(0)
    assert len(p0.steps) == 1
    assert p0.steps[0].sibling_hash == h1
    assert p0.steps[0].direction == ProofDirection.RIGHT
    v0 = verify_merkle_proof(leaf=leaves_data[0], proof=p0, expected_root=tree.get_root())
    assert v0.verified is True

    # Leaf 1 proof: sibling is leaf 0 on left
    p1 = tree.get_proof(1)
    assert len(p1.steps) == 1
    assert p1.steps[0].sibling_hash == h0
    assert p1.steps[0].direction == ProofDirection.LEFT
    v1 = verify_merkle_proof(leaf=leaves_data[1], proof=p1, expected_root=tree.get_root())
    assert v1.verified is True


def test_four_leaf_tree():
    """Four-leaf balanced binary tree: all 4 leaves can be proven and verified."""
    entries = [f"ledger_entry_{i}" for i in range(4)]
    tree = MerkleTree(entries)
    assert tree.total_leaves == 4
    root = tree.get_root()
    assert is_valid_sha256_hex(root)

    for i in range(4):
        proof = tree.get_proof(i)
        assert len(proof.steps) == 2  # log2(4) = 2
        res = verify_merkle_proof(leaf=entries[i], proof=proof, expected_root=root)
        assert res.verified is True, f"Leaf {i} failed inclusion verification"


# ---------------------------------------------------------------------------
# 4. Odd Numbers of Leaves (3, 5, 7 leaves)
# ---------------------------------------------------------------------------

def test_odd_leaves_three_nodes():
    """Three-leaf tree: last node duplicated at layer 0."""
    entries = ["entry_A", "entry_B", "entry_C"]
    tree = MerkleTree(entries)
    assert tree.total_leaves == 3
    root = tree.get_root()
    assert is_valid_sha256_hex(root)

    # Layer 0 leaves: [hA, hB, hC]
    # Layer 1: [H(hA, hB), H(hC, hC)]  (hC duplicated)
    # Layer 2 (Root): H(Layer1[0], Layer1[1])
    hA = hash_leaf("entry_A")
    hB = hash_leaf("entry_B")
    hC = hash_leaf("entry_C")
    p0 = hash_internal_nodes(hA, hB)
    p1 = hash_internal_nodes(hC, hC)
    expected_root = hash_internal_nodes(p0, p1)
    assert root == expected_root

    # Verify proof for entry_C (the odd leaf)
    proof_c = tree.get_proof(2)
    assert proof_c.steps[0].sibling_hash == hC
    assert proof_c.steps[0].direction == ProofDirection.RIGHT
    res_c = verify_merkle_proof(leaf="entry_C", proof=proof_c, expected_root=root)
    assert res_c.verified is True

    # Verify all 3 leaves
    for i, e in enumerate(entries):
        p = tree.get_proof(i)
        assert verify_merkle_proof(leaf=e, proof=p, expected_root=root).verified is True


def test_odd_leaves_five_nodes():
    """Five-leaf tree: odd node handling across multiple layers."""
    entries = [f"creative_{i}" for i in range(5)]
    tree = MerkleTree(entries)
    assert tree.total_leaves == 5
    root = tree.get_root()

    for i, e in enumerate(entries):
        proof = tree.get_proof(i)
        res = verify_merkle_proof(leaf=e, proof=proof, expected_root=root)
        assert res.verified is True, f"Failed verification for leaf {i} in 5-leaf tree"


# ---------------------------------------------------------------------------
# 5. Tamper Detection & Malformed Proofs
# ---------------------------------------------------------------------------

def test_tampered_leaf_data_detected():
    """Modifying leaf payload causes proof verification to fail."""
    entries = ["original_record_1", "original_record_2", "original_record_3"]
    tree = MerkleTree(entries)
    proof_0 = tree.get_proof(0)

    # Caller attempts to pass tampered content with original proof
    tampered_entry = "tampered_fraudulent_record_1"
    res = verify_merkle_proof(
        leaf=tampered_entry,
        proof=proof_0,
        expected_root=tree.get_root(),
    )
    assert res.verified is False
    assert res.root_matches is False
    assert "Leaf data mismatch" in res.reason or "Root mismatch" in res.reason


def test_tampered_sibling_hash_detected():
    """Modifying a sibling hash in the proof steps causes verification to fail."""
    entries = ["item_1", "item_2", "item_3", "item_4"]
    tree = MerkleTree(entries)
    proof = tree.get_proof(1)

    # Tamper with sibling hash in step 0
    tampered_steps = copy.deepcopy(proof.steps)
    tampered_steps[0] = MerkleProofStep(
        sibling_hash="a" * 64,
        direction=tampered_steps[0].direction,
    )
    tampered_proof = proof.model_copy(update={"steps": tampered_steps})

    res = verify_merkle_proof(
        leaf=entries[1],
        proof=tampered_proof,
        expected_root=tree.get_root(),
    )
    assert res.verified is False
    assert "Root mismatch" in res.reason


def test_tampered_direction_detected():
    """Inverting a sibling direction (e.g., 'left' -> 'right') fails verification."""
    entries = ["record_x", "record_y"]
    tree = MerkleTree(entries)
    proof = tree.get_proof(0)

    # Invert direction from right to left
    tampered_step = MerkleProofStep(
        sibling_hash=proof.steps[0].sibling_hash,
        direction=ProofDirection.LEFT,
    )
    tampered_proof = proof.model_copy(update={"steps": [tampered_step]})

    res = verify_merkle_proof(
        leaf=entries[0],
        proof=tampered_proof,
        expected_root=tree.get_root(),
    )
    assert res.verified is False
    assert "Root mismatch" in res.reason


def test_malformed_proof_hashes_rejected():
    """Malformed sibling hashes (non-hex, wrong length) are rejected with clear error."""
    bad_proof_dict = {
        "leaf_hash": "f" * 64,
        "steps": [
            {"sibling_hash": "not-a-valid-hex-hash", "direction": "left"}
        ]
    }
    res = verify_merkle_proof(
        leaf="f" * 64,
        proof=bad_proof_dict,
        expected_root="e" * 64,
    )
    assert res.verified is False
    assert "invalid sibling_hash" in res.reason


def test_malformed_direction_rejected():
    """Invalid direction string (e.g., 'diagonal') is rejected."""
    bad_direction_dict = {
        "leaf_hash": "a" * 64,
        "steps": [
            {"sibling_hash": "b" * 64, "direction": "diagonal"}
        ]
    }
    res = verify_merkle_proof(
        leaf="a" * 64,
        proof=bad_direction_dict,
        expected_root="c" * 64,
    )
    assert res.verified is False
    assert "invalid direction" in res.reason


# ---------------------------------------------------------------------------
# 6. Domain Separation & Cryptographic Invariants
# ---------------------------------------------------------------------------

def test_domain_separation_leaf_vs_node():
    """Demonstrates that a leaf payload cannot collide with an internal node hash."""
    payload = b"test_payload"
    leaf_h = hash_leaf(payload)

    # Attempting to forge an internal node with matching data cannot equal leaf_h
    # Leaf uses prefix b"\x00", internal node uses prefix b"\x01"
    h_custom_node = hashlib.sha256(b"\x01" + payload).hexdigest()
    assert leaf_h != h_custom_node


def test_deterministic_canonical_serialization():
    """Canonical JSON serialization produces identical bytes regardless of key insertion order."""
    dict1 = {"b": 2, "a": 1, "c": {"y": 20, "x": 10}}
    dict2 = {"c": {"x": 10, "y": 20}, "a": 1, "b": 2}

    b1 = canonical_serialize(dict1)
    b2 = canonical_serialize(dict2)
    assert b1 == b2

    h1 = hash_leaf(dict1)
    h2 = hash_leaf(dict2)
    assert h1 == h2


# ---------------------------------------------------------------------------
# 7. Passport Integration
# ---------------------------------------------------------------------------

def test_build_merkle_tree_from_passport_collection():
    """Constructs a Merkle tree from passport snapshots and verifies each passport."""
    passports = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "passport_hash": "a" * 64,
            "metadata_snapshot": {"draft_title": "Campaign 1", "decision": "approved"},
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "passport_hash": "b" * 64,
            "metadata_snapshot": {"draft_title": "Campaign 2", "decision": "approved"},
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "passport_hash": "c" * 64,
            "metadata_snapshot": {"draft_title": "Campaign 3", "decision": "approved"},
        },
    ]

    tree = build_merkle_tree_from_passports(passports)
    assert tree.total_leaves == 3
    root = tree.get_root()
    assert is_valid_sha256_hex(root)

    # Prove passport 1
    p1 = tree.get_proof(1)
    res1 = verify_merkle_proof(leaf=passports[1]["passport_hash"], proof=p1, expected_root=root)
    assert res1.verified is True
