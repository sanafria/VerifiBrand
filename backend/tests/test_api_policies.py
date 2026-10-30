"""Integration tests for Policy Card CRUD APIs (Phase 3).

Tested directly against the live PostgreSQL database container (brandledger_postgres:5433).
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db import db_manager


@pytest.fixture(scope="module")
def client():
    """TestClient managing lifespan (DB connect and disconnect)."""
    with TestClient(app) as test_client:
        yield test_client


def test_1_list_policies_from_live_database(client: TestClient) -> None:
    """Verify GET /api/policies retrieves seeded policy cards from the database."""
    response = client.get("/api/policies")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 4

    titles = [p["title"] for p in data["items"]]
    assert any("Terminology" in t for t in titles)
    assert any("Discount" in t for t in titles)


def test_2_filter_policies_by_category(client: TestClient) -> None:
    """Verify GET /api/policies?card_type=terminology returns only terminology rules."""
    response = client.get("/api/policies?card_type=terminology")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["card_type"] == "terminology"


def test_3_create_policy_success(client: TestClient) -> None:
    """Verify POST /api/policies creates a new policy card and initial version 1."""
    payload = {
        "title": "Social Media Disclaimer Requirement",
        "card_type": "claim",
        "rule_text": "All sponsored influencer posts must include #ad or #sponsored in the first three lines.",
        "approved_value": "#ad or #sponsored",
        "source_quote": "Sponsored influencer content must prominently display #ad in compliance with advertising standards.",
        "severity": "blocker",
    }

    response = client.post("/api/policies", json=payload)
    assert response.status_code == 201

    created = response.json()
    assert created["title"] == payload["title"]
    assert created["version"] == 1
    assert created["status"] == "active"
    assert created["card_type"] == "claim"
    assert "id" in created


def test_4_create_policy_validation_failure(client: TestClient) -> None:
    """Verify POST /api/policies rejects invalid input (empty rule_text)."""
    invalid_payload = {
        "title": "Broken Policy",
        "card_type": "terminology",
        "rule_text": "",  # Empty rule text violates min_length=3
        "source_quote": "Some quote",
    }

    response = client.post("/api/policies", json=invalid_payload)
    assert response.status_code == 422


def test_5_patch_policy_increments_version(client: TestClient) -> None:
    """Verify PATCH /api/policies/{id} updates rule text and increments version without rewriting history."""
    # 1. Create a policy first
    initial_payload = {
        "title": "Temporary Discount Policy",
        "card_type": "offer",
        "rule_text": "Summer offer allows 20% discount.",
        "approved_value": "20%",
        "source_quote": "Summer offer allows 20% discount.",
        "severity": "blocker",
    }
    create_res = client.post("/api/policies", json=initial_payload)
    assert create_res.status_code == 201
    policy_id = create_res.json()["id"]
    assert create_res.json()["version"] == 1

    # 2. Update the offer value (triggers version increment to 2)
    update_payload = {
        "rule_text": "Summer offer reduced to 15% discount.",
        "approved_value": "15%",
        "source_quote": "Summer offer reduced to 15% discount.",
    }
    patch_res = client.patch(f"/api/policies/{policy_id}", json=update_payload)
    assert patch_res.status_code == 200

    updated = patch_res.json()
    assert updated["version"] == 2
    assert updated["approved_value"] == "15%"
    assert updated["rule_text"] == "Summer offer reduced to 15% discount."


def test_6_patch_nonexistent_policy_returns_404(client: TestClient) -> None:
    """Verify PATCH /api/policies/{nonexistent_id} returns 404 Not Found."""
    fake_id = str(uuid.uuid4())
    response = client.patch(f"/api/policies/{fake_id}", json={"title": "New Title"})
    assert response.status_code == 404
    assert f"'{fake_id}' not found" in response.json()["detail"]


def test_7_deactivate_policy(client: TestClient) -> None:
    """Verify PATCH /api/policies/{id} with status='inactive' marks policy inactive."""
    # Create
    create_res = client.post(
        "/api/policies",
        json={
            "title": "Expiring Policy",
            "card_type": "tone",
            "rule_text": "Use formal tone.",
            "source_quote": "Tone should be formal.",
        },
    )
    policy_id = create_res.json()["id"]

    # Deactivate
    patch_res = client.patch(
        f"/api/policies/{policy_id}",
        json={"status": "inactive"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "inactive"


def test_8_json_string_decoding_resilience() -> None:
    """Verify rules and metadata are decoded safely from single and double-encoded JSON strings."""
    from backend.app.api.policies import _parse_json_rules, _parse_json_metadata, _row_to_response
    import datetime

    # 1. Native Python list and dict
    assert _parse_json_rules([{"type": "claim"}]) == [{"type": "claim"}]
    assert _parse_json_metadata({"author": "Nimra"}) == {"author": "Nimra"}

    # 2. Single-encoded JSON strings (as returned by asyncpg from PostgreSQL JSONB)
    assert _parse_json_rules('[{"type": "claim"}]') == [{"type": "claim"}]
    assert _parse_json_metadata('{"author": "Nimra"}') == {"author": "Nimra"}
    assert _parse_json_rules('[]') == []
    assert _parse_json_metadata('{}') == {}

    # 3. Double-encoded JSON strings (regression for double-serialization defect)
    assert _parse_json_rules('"[]"') == []
    assert _parse_json_metadata('"{}"') == {}
    assert _parse_json_rules('"[{\\"type\\": \\"claim\\"}]"') == [{"type": "claim"}]

    # 4. None and empty strings safely default
    assert _parse_json_rules(None) == []
    assert _parse_json_metadata(None) == {}
    assert _parse_json_rules("") == []
    assert _parse_json_metadata("") == {}

    # 5. Full _row_to_response with double-encoded JSON succeeds without Pydantic validation error
    dummy_row = {
        "id": uuid.uuid4(),
        "policy_key": "pol_test_json",
        "title": "JSON Decoding Test Policy",
        "card_type": "offer",
        "rule_text": "Valid rule text for test.",
        "approved_value": "100%",
        "source_quote": "Valid rule text for test.",
        "valid_from": None,
        "valid_until": None,
        "severity": "blocker",
        "status": "active",
        "version": 1,
        "rules": '"[]"',  # double-serialized string
        "metadata": '"{}"',  # double-serialized string
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }
    response_model = _row_to_response(dummy_row)
    assert isinstance(response_model.rules, list)
    assert isinstance(response_model.metadata, dict)
    assert response_model.rules == []
    assert response_model.metadata == {}


def test_9_database_update_error_reports_500_not_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that an unexpected database failure during PATCH is reported as HTTP 500, NOT 404."""
    import backend.app.api.policies as policy_module
    import datetime

    dummy_id = uuid.uuid4()
    dummy_existing = {
        "id": dummy_id,
        "policy_key": "pol_existing",
        "title": "Existing Policy",
        "card_type": "offer",
        "rule_text": "Rule text",
        "approved_value": None,
        "source_quote": "Source quote",
        "valid_from": None,
        "valid_until": None,
        "severity": "blocker",
        "status": "active",
        "version": 1,
        "rules": "[]",
        "metadata": "{}",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "updated_at": datetime.datetime.now(datetime.timezone.utc),
    }

    # Simulate active database connection
    monkeypatch.setattr(policy_module, "_is_db_connected", lambda: True)

    async def mock_fetchrow(query, *args):
        if "SELECT * FROM policy_cards" in query:
            return dummy_existing
        # Simulate unexpected database error during UPDATE statement
        raise RuntimeError("Simulated database connection drop")

    monkeypatch.setattr(policy_module.db_manager, "fetchrow", mock_fetchrow)

    res = client.patch(f"/api/policies/{dummy_id}", json={"rule_text": "Updated rule text."})
    # Must be 500 server error, NEVER misreported as 404 "not found"
    assert res.status_code == 500
    assert "Database update failed" in res.json()["detail"]
