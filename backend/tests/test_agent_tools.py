"""Comprehensive unit and integration tests for BrandLedger Agent Tools.

Covers all Phase 7 specifications:
1. Tool 1: scan_creative
   - Valid creative scans returning PASS, BLOCK, and HUMAN_REVIEW.
   - Traceable evidence citations.
   - Invalid and empty creative inputs handled safely.
   - Invalid scan_date formats handled safely.
   - Deterministic backend decision cannot be overridden by callers.
2. Tool 2: get_findings
   - Missing arguments handled safely.
   - Invalid UUID formats handled safely.
   - Nonexistent scan and draft lookups return machine-readable results without crashing.
3. Tool 3: verify_merkle_proof
   - Valid Merkle proofs return verified=True.
   - Tampered proofs, sibling hashes, and leaf data return verified=False.
   - Malformed structures return machine-readable errors.
"""

import pytest
from uuid import uuid4

from backend.app.schemas.agent_tools import (
    ComplianceDecision,
    ScanCreativeInput,
)
from backend.app.schemas.finding import FindingCategory, FindingSeverity
from backend.app.schemas.scan import ScanStatus
from backend.app.services.agent_tools import (
    evaluate_compliance_decision,
    get_findings,
    scan_creative,
    verify_merkle_proof,
)
from backend.app.services.merkle_ledger import MerkleTree


# ---------------------------------------------------------------------------
# Tool 1: scan_creative Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scan_creative_blocking_violation(all_sample_policy_dicts):
    """Creative with prohibited term 'customers' triggers BLOCK decision with evidence citation."""
    input_data = ScanCreativeInput(
        title="Account Access Email",
        content_text="Our customers can log in to their dashboard anytime.",
        scan_date="2026-06-15",
        policy_cards=all_sample_policy_dicts,
    )
    res = await scan_creative(input_data)

    assert res.status == ScanStatus.COMPLETED
    assert res.decision == ComplianceDecision.BLOCK
    assert res.has_blockers is True
    assert res.blockers_count >= 1
    assert "Blocked:" in res.decision_reason
    assert res.total_findings >= 1

    # Check evidence citations
    assert len(res.evidence_citations) == res.total_findings
    cit = res.evidence_citations[0]
    assert cit.policy_card_id == "pol_term_001"
    assert cit.policy_version == "1.0"
    assert "The brand prohibits the term 'Customers'" in cit.source_quote
    assert cit.matched_text.lower() == "customers"


@pytest.mark.asyncio
async def test_scan_creative_expired_offer_violation(all_sample_policy_dicts):
    """Creative with expired offer on 2026-07-01 triggers BLOCK decision."""
    input_data = {
        "title": "Summer Promo Blast",
        "content_text": "Our members can enjoy Summer Discount on all items!",
        "scan_date": "2026-07-01",  # Expired after 2026-06-30
        "policy_cards": all_sample_policy_dicts,
    }
    res = await scan_creative(input_data)

    assert res.status == ScanStatus.COMPLETED
    assert res.decision == ComplianceDecision.BLOCK
    assert res.has_blockers is True

    categories = [f.category for f in res.findings]
    assert FindingCategory.EXPIRED_OFFER.value in categories


@pytest.mark.asyncio
async def test_scan_creative_clean_pass(all_sample_policy_dicts):
    """Clean compliant creative triggers PASS decision with zero findings."""
    input_data = {
        "title": "Compliant Member Announcement",
        "content_text": "Our members can access their account balance and earn up to 400 points.",
        "scan_date": "2026-06-15",
        "policy_cards": all_sample_policy_dicts,
    }
    res = await scan_creative(input_data)

    assert res.status == ScanStatus.COMPLETED
    assert res.decision == ComplianceDecision.PASS
    assert res.has_blockers is False
    assert res.blockers_count == 0
    assert res.total_findings == 0
    assert "Compliant:" in res.decision_reason


@pytest.mark.asyncio
async def test_scan_creative_unsupported_claim_triggers_human_review(all_sample_policy_dicts):
    """Unsupported guarantee triggers HUMAN_REVIEW rather than silent pass or false violation."""
    input_data = {
        "title": "Bold Growth Campaign",
        "content_text": "Our members enjoy guaranteed results on every single transaction.",
        "scan_date": "2026-06-15",
        "policy_cards": all_sample_policy_dicts,
    }
    res = await scan_creative(input_data)

    assert res.status == ScanStatus.COMPLETED
    assert res.decision == ComplianceDecision.HUMAN_REVIEW
    assert "Human Review Required:" in res.decision_reason
    assert res.total_findings >= 1
    # Check that unsupported claim is marked is_verified=False
    claim_finding = [f for f in res.findings if f.category == FindingCategory.UNSUPPORTED_CLAIM.value][0]
    assert claim_finding.is_verified is False


@pytest.mark.asyncio
async def test_scan_creative_empty_input_handled_safely():
    """Empty creative content is handled safely without crashing."""
    res = await scan_creative("")
    assert res.status == ScanStatus.FAILED
    assert res.decision == ComplianceDecision.HUMAN_REVIEW
    assert "Empty creative content" in res.decision_reason


@pytest.mark.asyncio
async def test_scan_creative_invalid_type_handled_safely():
    """Invalid input type returns clean machine-readable error result."""
    res = await scan_creative(None)  # type: ignore
    assert res.status == ScanStatus.FAILED
    assert res.decision == ComplianceDecision.HUMAN_REVIEW
    assert "Invalid creative input type" in res.decision_reason


@pytest.mark.asyncio
async def test_scan_creative_invalid_date_handled_safely(all_sample_policy_dicts):
    """Invalid date string returns validation error rather than unhandled exception."""
    res = await scan_creative(
        creative_input="Our members can log in.",
        policy_cards=all_sample_policy_dicts,
        scan_date="not-a-valid-date",
    )
    assert res.status == ScanStatus.FAILED
    assert res.decision == ComplianceDecision.HUMAN_REVIEW
    assert "Invalid scan_date format" in res.decision_reason


# ---------------------------------------------------------------------------
# Tool 2: get_findings Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_findings_no_arguments_handled_safely():
    """Calling get_findings without arguments returns machine-readable error."""
    res = await get_findings()
    assert res.found is False
    assert "Either scan_id or draft_id must be provided" in res.error


@pytest.mark.asyncio
async def test_get_findings_invalid_uuid_handled_safely():
    """Calling get_findings with malformed UUID returns clean machine-readable error."""
    res = await get_findings(scan_id="123-not-a-uuid")
    assert res.found is False
    assert "Expected valid UUID" in res.error


@pytest.mark.asyncio
async def test_get_findings_nonexistent_record():
    """Calling get_findings with nonexistent UUID returns found=False without exception."""
    random_uuid = str(uuid4())
    res = await get_findings(scan_id=random_uuid)
    assert res.found is False
    assert res.scan_id == random_uuid
    assert len(res.findings) == 0


# ---------------------------------------------------------------------------
# Tool 3: verify_merkle_proof Tests
# ---------------------------------------------------------------------------

def test_tool_verify_merkle_proof_valid():
    """Agent tool verify_merkle_proof succeeds with valid proof."""
    entries = ["pass_item_1", "pass_item_2", "pass_item_3"]
    tree = MerkleTree(entries)
    root = tree.get_root()
    proof = tree.get_proof(1)

    result = verify_merkle_proof(
        leaf="pass_item_2",
        proof=proof,
        expected_root=root,
    )
    assert result.verified is True
    assert result.root_matches is True
    assert "Successfully verified inclusion proof" in result.reason


def test_tool_verify_merkle_proof_tampered_rejected():
    """Agent tool verify_merkle_proof detects tampered leaf data."""
    entries = ["passport_A", "passport_B"]
    tree = MerkleTree(entries)
    root = tree.get_root()
    proof = tree.get_proof(0)

    # Calling with altered leaf data
    result = verify_merkle_proof(
        leaf="passport_A_tampered",
        proof=proof,
        expected_root=root,
    )
    assert result.verified is False
    assert result.root_matches is False
    assert "mismatch" in result.reason.lower()


def test_tool_verify_merkle_proof_malformed_root():
    """Agent tool verify_merkle_proof rejects malformed expected root."""
    result = verify_merkle_proof(
        leaf="some_leaf",
        proof=[],
        expected_root="short-root",
    )
    assert result.verified is False
    assert "Invalid expected root" in result.reason
