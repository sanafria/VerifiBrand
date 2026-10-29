"""Unit tests for Evidence Verification Reports and edge cases.

Verifies:
1. Verification failures produce clear machine-readable reports.
2. Missing evidence, invalid policy references, and mismatched versions are recorded.
3. Unsupported claims retain unverified status without being classified as proven false.
4. Agent/AI cannot override authoritative evidence requirements.
"""

import pytest

from backend.app.schemas.finding import Finding, FindingCategory, FindingSeverity
from backend.app.schemas.policy import PolicyCard
from backend.app.services.evidence_verifier import (
    verify_findings_with_report,
    filter_and_verify_findings,
    verify_finding,
)


def test_verification_report_with_mixed_findings(
    terminology_policy_card,
    offer_policy_card,
):
    """Test verification report produces detailed, machine-readable output for both valid and invalid citations."""
    valid_finding = Finding(
        policy_card_id=terminology_policy_card.id,
        policy_version=terminology_policy_card.version,
        category=FindingCategory.TERMINOLOGY.value,
        severity=FindingSeverity.HIGH.value,
        matched_text="customers",
        source_quote="The brand prohibits the term 'Customers' and requires the term 'Members'.",
        explanation="Prohibited term used.",
        suggested_fix="Use Members.",
        confidence=1.0,
        is_verified=True,
    )

    fabricated_finding = Finding(
        policy_card_id=terminology_policy_card.id,
        policy_version=terminology_policy_card.version,
        category=FindingCategory.TERMINOLOGY.value,
        severity=FindingSeverity.HIGH.value,
        matched_text="clients",
        source_quote="This quote does not exist in the policy card content at all.",
        explanation="Fabricated finding.",
        suggested_fix="None",
        confidence=0.9,
        is_verified=True,
    )

    nonexistent_policy_finding = Finding(
        policy_card_id="pol_ghost_999",
        policy_version="1.0",
        category=FindingCategory.EXPIRED_OFFER.value,
        severity=FindingSeverity.HIGH.value,
        matched_text="Winter Special",
        source_quote="Winter Special expires on 2026-01-01.",
        explanation="References non-existent policy.",
        suggested_fix="None",
        confidence=0.8,
        is_verified=True,
    )

    findings = [valid_finding, fabricated_finding, nonexistent_policy_finding]
    policy_cards = [terminology_policy_card, offer_policy_card]

    verified_list, report = verify_findings_with_report(findings, policy_cards)

    assert len(verified_list) == 1
    assert verified_list[0].matched_text == "customers"
    assert verified_list[0].is_verified is True

    assert report.total_findings == 3
    assert report.verified_count == 1
    assert report.rejected_count == 2
    assert report.is_fully_verified is False

    # Check details
    assert len(report.details) == 3

    # Valid detail
    d0 = report.details[0]
    assert d0.is_verified is True
    assert d0.rejection_reason is None

    # Fabricated detail
    d1 = report.details[1]
    assert d1.is_verified is False
    assert "was not found in approved policy card" in d1.rejection_reason

    # Nonexistent policy detail
    d2 = report.details[2]
    assert d2.is_verified is False
    assert "does not exist in approved policy library" in d2.rejection_reason


def test_unsupported_claim_retains_unverified_status(claims_policy_card):
    """Unsupported claims pass evidence validation of policy quote, but retain is_verified=False."""
    unsupported_claim = Finding(
        policy_card_id=claims_policy_card.id,
        policy_version=claims_policy_card.version,
        category=FindingCategory.UNSUPPORTED_CLAIM.value,
        severity=FindingSeverity.MEDIUM.value,
        matched_text="guaranteed results",
        source_quote="All performance guarantees and promises of guaranteed results require prior approved evidence from legal compliance.",
        explanation="Requires approved legal substantiation.",
        suggested_fix="Soften claim or provide legal documentation.",
        confidence=0.7,
        is_verified=True,  # Caller asserted true
    )

    verified_list, report = verify_findings_with_report([unsupported_claim], [claims_policy_card])

    # Must be retained in findings, but is_verified forced to False
    assert len(verified_list) == 1
    assert verified_list[0].is_verified is False

    # In report, it is recorded with explicit note
    assert report.details[0].is_verified is False
    assert "unverified claim" in report.details[0].rejection_reason.lower()


def test_agent_cannot_override_missing_policy_evidence():
    """An agent cannot fabricate a finding and mark it verified without actual policy evidence."""
    fake_finding = Finding(
        policy_card_id="pol_fabricated",
        policy_version="1.0",
        category=FindingCategory.TERMINOLOGY.value,
        severity=FindingSeverity.HIGH.value,
        matched_text="invented_term",
        source_quote="Invented quote not in policy library.",
        explanation="Fabricated rule violation.",
        suggested_fix="Do something else.",
        confidence=1.0,
        is_verified=True,
    )

    cards_by_id = {}
    is_valid, reason = verify_finding(fake_finding, cards_by_id)
    assert is_valid is False
    assert "does not exist in approved policy library" in reason

    filtered = filter_and_verify_findings([fake_finding], [])
    assert len(filtered) == 0  # Completely suppressed
