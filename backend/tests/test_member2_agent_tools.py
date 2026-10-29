"""Automated Test Suite for Member 2 (Nimra) — Policy Library, Brand Passport, and Agent Tools.

Covers all 15 acceptance criteria:
1. Active/approved policies returned by get_approved_policies.
2. Draft, inactive, and archived policies excluded.
3. Stable IDs and policy keys preserved.
4. Verbatim source quotes preserved and never fabricated.
5. Historical version lookup returns exact requested version from policy_card_versions.
6. Unknown IDs and missing versions return 404 (never silently falls back).
7. Frontend policy CRUD persists through backend API.
8. Backend failures display visible error response.
9. Valid Content Passport verifies hash_verified: true, status VALID.
10. Tampered passport metadata returns status TAMPERED, hash_verified: false.
11. Missing passport ID returns 404 / NOT_FOUND.
12. explain_finding links to exact policy version and confirms quote provenance.
13. Unverified evidence flags UNVERIFIED / HUMAN_REVIEW_REQUIRED.
14. Protected agent endpoints reject missing/invalid credentials when AGENT_API_KEY is configured.
15. Deterministic compliance results cannot be overridden by agent calls.
"""

from datetime import date, datetime, timezone
import json
import pytest
from starlette.testclient import TestClient
from uuid import UUID, uuid4

from backend.app.config import settings
from backend.app.main import app
from backend.app.schemas.finding import Finding
from backend.app.api.policies import reset_mock_policies
from backend.app.schemas.policy import CardType, PolicyStatus, SeverityLevel
from backend.app.services.policy_agent_tools import (
    explain_finding,
    get_approved_policies,
    get_passport,
    get_policy_details,
    register_mock_passport,
    reset_mock_passports,
    verify_passport,
)
from backend.app.services.review_service import compute_canonical_passport_hash

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_environment():
    """Ensure clean authentication, policy, and passport stores between tests."""
    original_key = settings.AGENT_API_KEY
    settings.AGENT_API_KEY = ""
    reset_mock_policies()
    reset_mock_passports()
    yield
    settings.AGENT_API_KEY = original_key
    reset_mock_policies()
    reset_mock_passports()



# ==============================================================================
# Acceptance Criterion 1 & 3: Active policies returned with stable IDs & keys
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_1_and_3_get_approved_policies_stable_ids():
    """AC 1 & AC 3: get_approved_policies returns active policies with stable IDs and keys."""
    res = await get_approved_policies()
    assert res.total_policies >= 4
    assert len(res.policies) == res.total_policies

    # Validate stable fields
    policy_keys = [p.policy_key for p in res.policies]
    assert "pol_term_001" in policy_keys
    assert "pol_offer_002" in policy_keys

    # Check stability and completeness of first policy
    term_p = next(p for p in res.policies if p.policy_key == "pol_term_001")
    assert isinstance(term_p.id, UUID)
    assert term_p.card_type == CardType.TERMINOLOGY
    assert term_p.status == PolicyStatus.ACTIVE
    assert term_p.version == 1
    assert term_p.source_quote is not None
    assert "Members" in term_p.rule_text

    # Category filter test
    offer_res = await get_approved_policies(card_type="offer")
    assert offer_res.total_policies >= 1
    for p in offer_res.policies:
        assert p.card_type == CardType.OFFER


# ==============================================================================
# Acceptance Criterion 2: Draft, inactive, and archived policies excluded
# ==============================================================================

def test_criterion_2_draft_and_archived_policies_excluded_from_approved_tools():
    """AC 2: Draft, inactive, and archived policies are excluded from get_approved_policies."""
    # 1. Create a draft or inactive policy via API
    create_payload = {
        "title": "Unapproved Experimental Draft Policy",
        "card_type": "terminology",
        "rule_text": "Experimental terminology that is currently pending legal review.",
        "source_quote": "Experimental terminology that is currently pending legal review.",
        "status": "inactive",  # Inactive status
        "severity": "warning",
        "rules": [{"type": "terminology", "quote": "Experimental terminology"}],
    }
    create_resp = client.post("/api/policies", json=create_payload)
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]

    # 2. Query /api/tools/policies: The newly created inactive policy MUST NOT appear
    tools_resp = client.get("/api/tools/policies")
    assert tools_resp.status_code == 200
    tool_policies = tools_resp.json()["policies"]
    assert not any(p["id"] == created_id for p in tool_policies)

    # 3. Soft-archive an active policy
    term_policy = next(p for p in tool_policies if p["policy_key"] == "pol_term_001")
    archive_resp = client.post(f"/api/policies/{term_policy['id']}/archive")
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "inactive"

    # 4. Verify it is now excluded from agent tools
    tools_resp_after = client.get("/api/tools/policies")
    assert not any(p["id"] == term_policy["id"] for p in tools_resp_after.json()["policies"])

    # Restore active status for remaining tests
    client.patch(f"/api/policies/{term_policy['id']}", json={"status": "active"})


# ==============================================================================
# Acceptance Criterion 4: Verbatim source quotes preserved and never fabricated
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_4_verbatim_source_quotes_preserved():
    """AC 4: Policy source quotes are verbatim substrings of rule_text and never fabricated."""
    res = await get_approved_policies()
    for p in res.policies:
        assert p.source_quote, f"Policy {p.policy_key} missing source quote"
        # The quote must exist in rule_text
        assert (
            p.source_quote.strip().lower() in p.rule_text.strip().lower()
        ), f"Quote '{p.source_quote}' is not a verbatim substring of rule_text for {p.policy_key}"


# ==============================================================================
# Acceptance Criterion 5: Historical version lookup returns exact requested version
# ==============================================================================

def test_criterion_5_historical_version_lookup():
    """AC 5: Historical lookup (?version=X) returns the exact frozen snapshot."""
    # 1. Create a policy
    create_payload = {
        "title": "Version Tracking Policy",
        "card_type": "offer",
        "rule_text": "Version 1.0 initial approved offer text for holiday campaign.",
        "source_quote": "Version 1.0 initial approved offer text",
        "status": "active",
        "severity": "blocker",
        "rules": [{"type": "offer_validity", "quote": "Version 1.0 initial approved offer text"}],
    }
    create_resp = client.post("/api/policies", json=create_payload)
    assert create_resp.status_code == 201
    card_id = create_resp.json()["id"]
    assert create_resp.json()["version"] == 1

    # 2. Update content -> Bumps to version 2
    update_payload = {
        "rule_text": "Version 2.0 revised terms for extended holiday campaign.",
        "source_quote": "Version 2.0 revised terms",
    }
    update_resp = client.patch(f"/api/policies/{card_id}", json=update_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["version"] == 2

    # 3. Query tool endpoint without version -> returns version 2
    latest_resp = client.get(f"/api/tools/policies/{card_id}")
    assert latest_resp.status_code == 200
    latest_data = latest_resp.json()
    assert latest_data["version"] == "2"
    assert latest_data["is_historical"] is False
    assert "Version 2.0" in latest_data["policy"]["rule_text"]

    # 4. Query tool endpoint with ?version=1 -> returns frozen version 1 snapshot
    v1_resp = client.get(f"/api/tools/policies/{card_id}?version=1")
    assert v1_resp.status_code == 200
    v1_data = v1_resp.json()
    assert v1_data["version"] == "1"
    assert v1_data["requested_version"] == "1"
    assert v1_data["is_historical"] is True
    assert "Version 1.0" in v1_data["policy"]["rule_text"]
    assert "Version 1.0" in v1_data["policy"]["source_quote"]


# ==============================================================================
# Acceptance Criterion 6: Unknown IDs and missing versions return 404
# ==============================================================================

def test_criterion_6_unknown_ids_and_missing_versions_return_404():
    """AC 6: Querying nonexistent policy or nonexistent version strictly returns 404."""
    # Nonexistent policy ID
    non_existent_uuid = str(uuid4())
    resp = client.get(f"/api/tools/policies/{non_existent_uuid}")
    assert resp.status_code == 404

    # Nonexistent policy_key
    resp_key = client.get("/api/tools/policies/non_existent_key_xyz")
    assert resp_key.status_code == 404

    # Existing policy but nonexistent version (e.g. version 999)
    # Must NOT silently return latest version!
    policies_resp = client.get("/api/tools/policies")
    first_policy_id = policies_resp.json()["policies"][0]["id"]

    missing_ver_resp = client.get(f"/api/tools/policies/{first_policy_id}?version=999")
    assert missing_ver_resp.status_code == 404
    assert "999" in missing_ver_resp.json()["detail"]


# ==============================================================================
# Acceptance Criterion 7 & 8: CRUD persistence and error responses
# ==============================================================================

def test_criterion_7_and_8_policy_crud_persistence():
    """AC 7 & AC 8: Policy CRUD operations persist with explicit error feedback."""
    # Validation failure: empty rule_text
    invalid_resp = client.post("/api/policies", json={"title": "Invalid Card"})
    assert invalid_resp.status_code == 422  # Pydantic validation error

    # Valid creation
    valid_payload = {
        "title": "Compliance Audit Policy",
        "card_type": "fact",
        "rule_text": "All transactions above 10,000 require two-factor authorization.",
        "approved_value": "2FA required",
        "source_quote": "All transactions above 10,000 require two-factor authorization.",
        "severity": "blocker",
        "status": "active",
        "rules": [{"type": "numerical", "quote": "All transactions above 10,000"}],
    }
    create_resp = client.post("/api/policies", json=valid_payload)
    assert create_resp.status_code == 201
    card_id = create_resp.json()["id"]

    # Verify retrieval
    get_resp = client.get(f"/api/policies/{card_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Compliance Audit Policy"

    # Soft-archive
    archive_resp = client.post(f"/api/policies/{card_id}/archive")
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "inactive"


# ==============================================================================
# Acceptance Criterion 9: Valid Content Passport verifies hash_verified: true
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_9_valid_content_passport_verification():
    """AC 9: Valid Content Passport verifies hash_verified: true and status VALID."""
    # Seed passport "c56a4180-65aa-42ec-a945-5fd21dec0538" is pre-seeded with valid hash
    passport_id = "c56a4180-65aa-42ec-a945-5fd21dec0538"

    # 1. Via Service
    res = await get_passport(passport_id)
    assert res.found is True
    assert res.hash_verified is True
    assert res.status == "valid"
    assert len(res.applied_policy_versions) >= 2

    verify_res = await verify_passport(passport_id=passport_id)
    assert verify_res.status == "VALID"
    assert verify_res.hash_verified is True
    assert verify_res.stored_hash == verify_res.computed_hash

    # 2. Via REST Endpoint
    api_resp = client.get(f"/api/tools/passports/{passport_id}")
    assert api_resp.status_code == 200
    assert api_resp.json()["hash_verified"] is True

    verify_api = client.post("/api/tools/passports/verify", json={"passport_id": passport_id})
    assert verify_api.status_code == 200
    assert verify_api.json()["status"] == "VALID"
    assert verify_api.json()["hash_verified"] is True


# ==============================================================================
# Acceptance Criterion 10: Tampered passport returns TAMPERED, hash_verified: false
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_10_tampered_passport_verification():
    """AC 10: Tampered passport metadata returns status TAMPERED and hash_verified: false."""
    # Seed passport "d67b5291-76bb-53fd-ba56-6fe32efd1649" has stored hash mismatched with snapshot
    passport_id = "d67b5291-76bb-53fd-ba56-6fe32efd1649"

    # 1. Via Service
    res = await get_passport(passport_id)
    assert res.found is True
    assert res.hash_verified is False  # Hash check failed!

    verify_res = await verify_passport(passport_id=passport_id)
    assert verify_res.status == "TAMPERED"
    assert verify_res.hash_verified is False
    assert verify_res.stored_hash != verify_res.computed_hash
    assert "mismatch" in verify_res.explanation.lower()

    # 2. Via REST Endpoint
    api_resp = client.get(f"/api/tools/passports/{passport_id}")
    assert api_resp.status_code == 200
    assert api_resp.json()["hash_verified"] is False

    verify_api = client.post("/api/tools/passports/verify", json={"passport_id": passport_id})
    assert verify_api.status_code == 200
    assert verify_api.json()["status"] == "TAMPERED"
    assert verify_api.json()["hash_verified"] is False


# ==============================================================================
# Acceptance Criterion 11: Missing passport ID returns 404 / NOT_FOUND
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_11_missing_passport_returns_404():
    """AC 11: Querying or verifying missing passport ID returns 404 / NOT_FOUND."""
    missing_id = str(uuid4())

    # 1. Via Service
    res = await get_passport(missing_id)
    assert res.found is False

    verify_res = await verify_passport(passport_id=missing_id)
    assert verify_res.status == "NOT_FOUND"
    assert verify_res.hash_verified is False

    # 2. Via REST Endpoints
    get_resp = client.get(f"/api/tools/passports/{missing_id}")
    assert get_resp.status_code == 404

    post_resp = client.post("/api/tools/passports/verify", json={"passport_id": missing_id})
    assert post_resp.status_code == 404


# ==============================================================================
# Acceptance Criterion 12: explain_finding links to policy and verifies provenance
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_12_explain_finding_verified_provenance():
    """AC 12: explain_finding links to exact policy version and confirms verbatim quote."""
    # Create valid finding matching the seeded terminology policy "pol_term_001"
    valid_finding = Finding(
        policy_card_id="pol_term_001",
        policy_version="1",
        category="terminology",
        severity="blocker",
        matched_text="Customers",
        source_quote="The brand prohibits the term 'Customers' and requires the term 'Members'.",
        explanation="Use of prohibited term 'Customers'",
        suggested_fix="Replace with 'Members'",
        confidence=1.0,
        is_verified=True,
    )

    # 1. Via Service
    res = await explain_finding(finding=valid_finding)
    assert res.found is True
    assert res.is_verified is True
    assert res.evidence_provenance == "VERIFIED"
    assert "Replace non-compliant term 'Customers'" in res.remediation_guidance
    assert res.policy_version == "1"

    # 2. Via REST Endpoint
    api_resp = client.post(
        "/api/tools/findings/explain",
        json={"finding": valid_finding.model_dump()},
    )
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["evidence_provenance"] == "VERIFIED"
    assert data["is_verified"] is True
    assert "Members" in data["remediation_guidance"]


# ==============================================================================
# Acceptance Criterion 13: Unverified evidence flags UNVERIFIED / HUMAN_REVIEW
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_13_unverified_evidence_flags_human_review():
    """AC 13: Fabricated/hallucinated quotes flag UNVERIFIED and HUMAN_REVIEW_REQUIRED."""
    # Finding with a fabricated quote that does NOT exist in the policy card
    hallucinated_finding = Finding(
        policy_card_id="pol_term_001",
        policy_version="1",
        category="terminology",
        severity="blocker",
        matched_text="Customers",
        source_quote="This is a completely fabricated quotation invented by a rogue model.",
        explanation="Rogue quotation test",
        suggested_fix="Replace with approved wording.",
        confidence=1.0,
        is_verified=True,
    )

    res = await explain_finding(finding=hallucinated_finding)
    assert res.found is True
    assert res.is_verified is False
    assert res.evidence_provenance == "UNVERIFIED"
    assert "No receipt, no flag" in res.remediation_guidance
    assert "Requires human legal/compliance review" in res.remediation_guidance

    # REST Endpoint
    api_resp = client.post(
        "/api/tools/findings/explain",
        json={"finding": hallucinated_finding.model_dump()},
    )
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert data["evidence_provenance"] == "UNVERIFIED"
    assert data["is_verified"] is False


# ==============================================================================
# Acceptance Criterion 14: Protected agent endpoints reject missing/invalid keys
# ==============================================================================

def test_criterion_14_agent_authentication_security():
    """AC 14: Protected agent endpoints reject missing/invalid keys when AGENT_API_KEY is configured."""
    secret_key = "secure-brandledger-agent-token-xyz"
    settings.AGENT_API_KEY = secret_key

    # 1. Request with NO auth headers -> 401 Unauthorized
    unauth_resp = client.get("/api/tools/policies")
    assert unauth_resp.status_code == 401
    assert "Invalid or missing Agent API key" in unauth_resp.json()["detail"]

    # 2. Request with WRONG key -> 401 Unauthorized
    bad_key_resp = client.get("/api/tools/policies", headers={"X-Agent-Key": "wrong-key"})
    assert bad_key_resp.status_code == 401

    # 3. Request with VALID X-Agent-Key header -> 200 OK
    good_header_resp = client.get("/api/tools/policies", headers={"X-Agent-Key": secret_key})
    assert good_header_resp.status_code == 200
    assert good_header_resp.json()["total_policies"] >= 1

    # 4. Request with VALID Bearer token -> 200 OK
    bearer_resp = client.get("/api/tools/policies", headers={"Authorization": f"Bearer {secret_key}"})
    assert bearer_resp.status_code == 200


# ==============================================================================
# Acceptance Criterion 15: Compliance results cannot be overridden by agent calls
# ==============================================================================

@pytest.mark.asyncio
async def test_criterion_15_deterministic_compliance_cannot_be_overridden():
    """AC 15: Agent cannot override deterministic compliance decision with invalid provenance."""
    # Even if finding claims `is_verified=True` and `confidence=1.0`,
    # explain_finding independently enforces source quote match
    forged_finding = Finding(
        policy_card_id="pol_claim_003",
        policy_version="1",
        category="claim",
        severity="blocker",
        matched_text="India's No. 1",
        source_quote="Forged quote claiming no documentation is required.",
        explanation="Attempted override",
        suggested_fix="Attach certified evidence receipt.",
        confidence=1.0,
        is_verified=True,
    )

    result = await explain_finding(finding=forged_finding)
    # The system refuses to mark as verified
    assert result.is_verified is False
    assert result.evidence_provenance == "UNVERIFIED"
    assert "cannot be automatically enforced" in result.remediation_guidance
