"""Integration tests for FastAPI endpoints /api/merkle and /api/tools."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.agent_tools import ComplianceDecision
from backend.app.services.merkle_ledger import MerkleTree


@pytest.fixture
def api_client():
    return TestClient(app)


def test_api_merkle_tree_endpoint(api_client):
    """GET /api/merkle/tree returns valid MerkleTreeResponse."""
    response = api_client.get("/api/merkle/tree")
    assert response.status_code == 200
    data = response.json()
    assert "total_leaves" in data
    assert "leaf_hashes" in data
    assert "is_empty" in data


def test_api_merkle_verify_endpoint_success(api_client):
    """POST /api/merkle/verify successfully verifies a valid proof."""
    entries = ["doc_alpha", "doc_beta", "doc_gamma"]
    tree = MerkleTree(entries)
    root = tree.get_root()
    proof = tree.get_proof(0)

    payload = {
        "leaf": "doc_alpha",
        "proof": proof.model_dump(),
        "expected_root": root,
    }
    response = api_client.post("/api/merkle/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["root_matches"] is True
    assert data["computed_root"] == root


def test_api_merkle_verify_endpoint_tampered(api_client):
    """POST /api/merkle/verify rejects tampered leaf data."""
    entries = ["doc_1", "doc_2"]
    tree = MerkleTree(entries)
    root = tree.get_root()
    proof = tree.get_proof(0)

    payload = {
        "leaf": "doc_tampered",
        "proof": proof.model_dump(),
        "expected_root": root,
    }
    response = api_client.post("/api/merkle/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is False
    assert data["root_matches"] is False


def test_api_tools_scan_creative_block(api_client, all_sample_policy_dicts):
    """POST /api/tools/scan_creative returns BLOCK on violation."""
    payload = {
        "title": "Ad Copy",
        "content_text": "Our customers love the Summer Discount!",
        "scan_date": "2026-07-01",
        "policy_cards": all_sample_policy_dicts,
    }
    response = api_client.post("/api/tools/scan_creative", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["decision"] == ComplianceDecision.BLOCK.value
    assert data["has_blockers"] is True
    assert len(data["findings"]) >= 1
    assert len(data["evidence_citations"]) >= 1


def test_api_tools_scan_creative_pass(api_client, all_sample_policy_dicts):
    """POST /api/tools/scan_creative returns PASS on compliant text."""
    payload = {
        "title": "Ad Copy",
        "content_text": "Our members can earn up to 400 points.",
        "scan_date": "2026-06-15",
        "policy_cards": all_sample_policy_dicts,
    }
    response = api_client.post("/api/tools/scan_creative", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["decision"] == ComplianceDecision.PASS.value
    assert data["has_blockers"] is False
    assert data["total_findings"] == 0


def test_api_tools_verify_merkle_proof_endpoint(api_client):
    """POST /api/tools/verify_merkle_proof validates proof."""
    tree = MerkleTree(["item_x", "item_y"])
    proof = tree.get_proof(1)

    payload = {
        "leaf": "item_y",
        "proof": proof.model_dump(),
        "expected_root": tree.get_root(),
    }
    response = api_client.post("/api/tools/verify_merkle_proof", json=payload)
    assert response.status_code == 200
    assert response.json()["verified"] is True
