import pytest
from pydantic import ValidationError
from brandledger_extraction.visual_schema import VisualFinding, VisualResult


def _make(**kw):
    base = dict(policy_card_id="VIS-COLOUR-001", policy_version="1.0",
                category="visual_colour", status="fail", severity="medium",
                matched_text="#FF0000", source_quote="Use palette colours only.",
                explanation="Off palette", suggested_fix="Use Brand Blue", confidence=0.95)
    base.update(kw)
    return VisualFinding(**base)


def test_high_confidence_fail_stays_fail():
    assert _make().status == "fail"


def test_low_confidence_forced_to_needs_review():
    assert _make(confidence=0.5).status == "needs_review"


def test_missing_rule_quote_rejected():
    with pytest.raises(ValidationError):
        _make(source_quote="")


def test_result_defaults_not_processed_claims():
    r = VisualResult(processed=False, errors=["corrupt file"])
    assert r.processed is False and r.findings == []


def test_result_has_skipped_field():
    assert VisualResult(processed=True).skipped == []
