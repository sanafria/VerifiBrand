"""Integration tests for Human Reviews and Content Passport Generation (Phase 5).

Executed against the live PostgreSQL database (brandledger_postgres:5433).
Verifies:
- Authorized reviewer approval and Content Passport issuance.
- Cryptographic SHA-256 canonical snapshot hash verification.
- Rejection flow (no passport issued, draft marked rejected).
- Tamper detection (modified database row causes hash_verified=False).
- Authorization enforcement (403 on missing role or creator self-approval).
- Mismatched draft/scan, nonexistent IDs, and duplicate review rejections.
"""
import json
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


def test_1_authorized_approval_issues_valid_content_passport(client: TestClient) -> None:
    """Verify reviewer approval updates draft, saves review, and issues a valid Content Passport."""
    # 1. Create and scan a compliant draft
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Launch Banner Approved",
            "content_text": "Welcome Members! Enjoy standard pricing.",
        },
    )
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    # 2. Authorized Reviewer approves
    headers = {
        "X-User-Role": "reviewer",
        "X-User-Id": "rev-101",
        "X-User-Name": "Compliance Officer Sarah",
    }
    review_payload = {
        "draft_id": draft_id,
        "scan_id": scan_id,
        "decision": "approved",
        "comment": "All checks cleared. Copy conforms to brand standards.",
    }

    review_res = client.post("/api/reviews", json=review_payload, headers=headers)
    assert review_res.status_code == 201

    review_data = review_res.json()
    assert review_data["decision"] == "approved"
    assert review_data["reviewer_id"] == "rev-101"
    assert review_data["passport_id"] is not None
    passport_id = review_data["passport_id"]

    # 3. Retrieve Content Passport and verify cryptographic hash
    passport_res = client.get(f"/api/passports/{passport_id}")
    assert passport_res.status_code == 200

    passport_data = passport_res.json()
    assert passport_data["id"] == passport_id
    assert passport_data["status"] == "valid"
    assert len(passport_data["passport_hash"]) == 64
    assert passport_data["hash_verified"] is True
    assert passport_data["metadata_snapshot"]["decision"] == "approved"
    assert passport_data["metadata_snapshot"]["draft_title"] == "Launch Banner Approved"


def test_2_rejection_flow_does_not_issue_passport(client: TestClient) -> None:
    """Verify reviewer rejection updates draft status to 'rejected' and does NOT issue a passport."""
    # 1. Create and scan draft with violations
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Rejected Campaign",
            "content_text": "Hey customers, get expired offers now!",
            "scan_date": "2026-07-01",
        },
    )
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    # 2. Reviewer rejects
    headers = {"X-User-Role": "reviewer", "X-User-Id": "rev-102"}
    review_payload = {
        "draft_id": draft_id,
        "scan_id": scan_id,
        "decision": "rejected",
        "comment": "Violates terminology ('customers') and expired promotion.",
    }

    review_res = client.post("/api/reviews", json=review_payload, headers=headers)
    assert review_res.status_code == 201

    review_data = review_res.json()
    assert review_data["decision"] == "rejected"
    assert review_data["passport_id"] is None, "Rejections must never issue a valid Content Passport"


def test_3_authorization_blocks_unauthorized_users(client: TestClient) -> None:
    """Verify missing role or creator role is rejected with 403 Forbidden."""
    # 1. Create scan
    scan_res = client.post(
        "/api/scans",
        json={"title": "RBAC Test", "content_text": "Sample text for testing."},
    )
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    review_payload = {
        "draft_id": draft_id,
        "scan_id": scan_id,
        "decision": "approved",
    }

    # Case A: Missing X-User-Role header
    res_no_role = client.post("/api/reviews", json=review_payload)
    assert res_no_role.status_code == 403
    assert "Authentication required" in res_no_role.json()["detail"]

    # Case B: Creator attempts self-approval
    res_creator = client.post(
        "/api/reviews",
        json=review_payload,
        headers={"X-User-Role": "creator"},
    )
    assert res_creator.status_code == 403
    assert "Creators are not authorized" in res_creator.json()["detail"]

    # Case C: Unknown role
    res_unknown = client.post(
        "/api/reviews",
        json=review_payload,
        headers={"X-User-Role": "guest"},
    )
    assert res_unknown.status_code == 403


def test_4_mismatched_draft_and_scan_rejected(client: TestClient) -> None:
    """Verify review is rejected if scan does not belong to specified draft."""
    # Create two separate scans
    res1 = client.post("/api/scans", json={"title": "Draft 1", "content_text": "Text 1"})
    res2 = client.post("/api/scans", json={"title": "Draft 2", "content_text": "Text 2"})

    draft_id_1 = res1.json()["draft_id"]
    scan_id_2 = res2.json()["scan_id"]

    # Attempt to pair Draft 1 with Scan 2
    res = client.post(
        "/api/reviews",
        json={
            "draft_id": draft_id_1,
            "scan_id": scan_id_2,
            "decision": "approved",
        },
        headers={"X-User-Role": "reviewer"},
    )
    assert res.status_code == 400
    assert "does not belong to Draft" in res.json()["detail"]


def test_5_duplicate_review_rejected_with_409(client: TestClient) -> None:
    """Verify duplicate reviews on the same scan return 409 Conflict."""
    scan_res = client.post("/api/scans", json={"title": "Dup Test", "content_text": "Text"})
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    headers = {"X-User-Role": "reviewer"}
    payload = {"draft_id": draft_id, "scan_id": scan_id, "decision": "approved"}

    # First review
    first_res = client.post("/api/reviews", json=payload, headers=headers)
    assert first_res.status_code == 201

    # Second review on same scan
    second_res = client.post("/api/reviews", json=payload, headers=headers)
    assert second_res.status_code == 409
    assert "already been reviewed" in second_res.json()["detail"]


def test_6_passport_tampering_detected(client: TestClient) -> None:
    """Verify that manually tampering with database snapshot causes hash_verified=False."""
    # 1. Create approved passport
    scan_res = client.post("/api/scans", json={"title": "Tamper Test", "content_text": "Text"})
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    review_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved"},
        headers={"X-User-Role": "reviewer"},
    )
    passport_id = review_res.json()["passport_id"]

    # 2. Check initial valid state
    initial_res = client.get(f"/api/passports/{passport_id}")
    assert initial_res.status_code == 200
    assert initial_res.json()["hash_verified"] is True

    # 3. Simulate database tampering: alter snapshot title without updating passport_hash
    import asyncio
    import asyncpg
    from backend.app.config import settings

    async def tamper():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            tampered_snapshot = dict(initial_res.json()["metadata_snapshot"])
            tampered_snapshot["draft_title"] = "TAMPERED HACKED TITLE"
            await conn.execute(
                "UPDATE passports SET metadata_snapshot = $1::jsonb WHERE id = $2;",
                json.dumps(tampered_snapshot),
                uuid.UUID(passport_id),
            )
        finally:
            await conn.close()

    asyncio.run(tamper())

    # 4. Verify detection on retrieval
    tampered_res = client.get(f"/api/passports/{passport_id}")
    assert tampered_res.status_code == 200
    assert tampered_res.json()["hash_verified"] is False, "Tampering must trigger hash_verified=False"


def test_7_get_nonexistent_passport_returns_404(client: TestClient) -> None:
    """Verify GET /api/passports/{fake_id} returns 404."""
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/passports/{fake_id}")
    assert res.status_code == 404
    assert f"'{fake_id}' not found" in res.json()["detail"]


def test_8_passport_creation_failure_rolls_back_review_and_draft_status(client: TestClient, monkeypatch) -> None:
    """Verify that if passport creation fails, the entire transaction rolls back cleanly.

    No review row remains, draft status is not changed to approved, and subsequent
    clean reviews can still succeed.
    """
    import asyncio
    import asyncpg
    from backend.app.config import settings

    # 1. Create and scan compliant draft
    scan_res = client.post(
        "/api/scans",
        json={"title": "Rollback Test Draft", "content_text": "Sample text for rollback test."},
    )
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    # 2. Inject failure during passport computation
    from backend.app.services import review_service

    def fail_hash(snapshot):
        raise RuntimeError("Simulated failure during passport generation")

    monkeypatch.setattr(review_service, "compute_canonical_passport_hash", fail_hash)

    headers = {"X-User-Role": "reviewer", "X-User-Id": "rev-rollback"}
    review_payload = {
        "draft_id": draft_id,
        "scan_id": scan_id,
        "decision": "approved",
        "comment": "Should fail and roll back.",
    }

    # 3. Submit review; must fail with 500
    res = client.post("/api/reviews", json=review_payload, headers=headers)
    assert res.status_code == 500

    # 4. Verify database state: NO review saved, draft status NOT approved, NO passport
    async def verify_db():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            review_row = await conn.fetchrow("SELECT id FROM reviews WHERE scan_id = $1;", uuid.UUID(scan_id))
            draft_row = await conn.fetchrow("SELECT status FROM content_drafts WHERE id = $1;", uuid.UUID(draft_id))
            passport_row = await conn.fetchrow("SELECT id FROM passports WHERE scan_id = $1;", uuid.UUID(scan_id))
            return review_row, draft_row, passport_row
        finally:
            await conn.close()

    review_row, draft_row, passport_row = asyncio.run(verify_db())
    assert review_row is None, "Rollback failed: review row was persisted despite failure"
    assert draft_row["status"] != "approved", "Rollback failed: draft status was updated to approved"
    assert passport_row is None, "Rollback failed: passport was created"

    # 5. Restore function and verify the scan can now be reviewed cleanly
    monkeypatch.undo()
    clean_res = client.post("/api/reviews", json=review_payload, headers=headers)
    assert clean_res.status_code == 201
    assert clean_res.json()["passport_id"] is not None


def test_9_concurrent_review_race_condition_prevented(client: TestClient) -> None:
    """Verify concurrent competing reviews for the same scan cannot both succeed."""
    import asyncio
    import asyncpg
    import httpx
    from backend.app.config import settings

    scan_res = client.post(
        "/api/scans",
        json={"title": "Concurrency Test Draft", "content_text": "Sample text for concurrency test."},
    )
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    headers = {"X-User-Role": "reviewer"}

    async def run_concurrent():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            req1 = ac.post(
                "/api/reviews",
                json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved", "comment": "First decision"},
                headers=headers,
            )
            req2 = ac.post(
                "/api/reviews",
                json={"draft_id": draft_id, "scan_id": scan_id, "decision": "rejected", "comment": "Second decision"},
                headers=headers,
            )
            return await asyncio.gather(req1, req2)

    r1, r2 = asyncio.run(run_concurrent())
    statuses = [r1.status_code, r2.status_code]
    assert 201 in statuses, f"Expected one 201 Created, got statuses: {statuses}"
    assert 409 in statuses, f"Expected one 409 Conflict, got statuses: {statuses}"

    # Verify database state has exactly 1 review for this scan
    async def count_reviews():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            return await conn.fetch("SELECT id, decision FROM reviews WHERE scan_id = $1;", uuid.UUID(scan_id))
        finally:
            await conn.close()

    reviews = asyncio.run(count_reviews())
    assert len(reviews) == 1, f"Expected exactly 1 review row, found {len(reviews)}"


def test_10_database_rejects_duplicate_review_for_same_scan(client: TestClient) -> None:
    """Verify PostgreSQL rejects a second review for the same scan via uq_reviews_scan_id."""
    import asyncio
    import asyncpg
    from backend.app.config import settings

    # 1. Create a compliant draft and scan
    scan_res = client.post(
        "/api/scans",
        json={"title": "Unique Review Test", "content_text": "Sample text for review uniqueness test."},
    )
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["scan_id"]
    draft_id = scan_res.json()["draft_id"]

    # 2. Submit initial valid review through normal API flow
    headers = {"X-User-Role": "reviewer", "X-User-Id": "rev-primary"}
    review_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved", "comment": "First approved review."},
        headers=headers,
    )
    assert review_res.status_code == 201

    # 3. Attempt direct SQL insertion of second review with identical scan_id
    async def insert_duplicate_review():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO reviews (id, draft_id, scan_id, reviewer_id, reviewer_name, decision, comment, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW());
                """,
                uuid.uuid4(),
                uuid.UUID(draft_id),
                uuid.UUID(scan_id),
                "rev-duplicate",
                "Secondary Reviewer",
                "rejected",
                "Direct SQL insert that must trigger unique constraint violation.",
            )
        finally:
            await conn.close()

    # 4. Assert PostgreSQL raises UniqueViolationError referencing uq_reviews_scan_id
    with pytest.raises(asyncpg.UniqueViolationError) as exc_info:
        asyncio.run(insert_duplicate_review())

    err_msg = str(exc_info.value)
    assert "uq_reviews_scan_id" in err_msg or "scan_id" in err_msg

    # 5. Verify exactly 1 review remains in database
    async def count_reviews():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            return await conn.fetch("SELECT id FROM reviews WHERE scan_id = $1;", uuid.UUID(scan_id))
        finally:
            await conn.close()

    reviews = asyncio.run(count_reviews())
    assert len(reviews) == 1


def test_11_database_rejects_duplicate_passport_for_same_scan(client: TestClient) -> None:
    """Verify PostgreSQL rejects a second Passport for the same scan via uq_passports_scan_id."""
    import asyncio
    import asyncpg
    from backend.app.config import settings

    # 1. Create draft 1 and scan 1
    scan_1_res = client.post(
        "/api/scans",
        json={"title": "Passport Uniqueness Draft 1", "content_text": "Content for draft 1."},
    )
    assert scan_1_res.status_code == 201
    scan_1_id = scan_1_res.json()["scan_id"]
    draft_1_id = scan_1_res.json()["draft_id"]

    # 2. Approve draft 1 / scan 1 to generate valid passport 1
    headers = {"X-User-Role": "reviewer", "X-User-Id": "rev-pass-1"}
    review_1_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_1_id, "scan_id": scan_1_id, "decision": "approved", "comment": "Approved scan 1."},
        headers=headers,
    )
    assert review_1_res.status_code == 201
    assert review_1_res.json()["passport_id"] is not None

    # 3. Create draft 2 and scan 2 to obtain a distinct valid review_id with FK integrity
    scan_2_res = client.post(
        "/api/scans",
        json={"title": "Passport Uniqueness Draft 2", "content_text": "Content for draft 2."},
    )
    assert scan_2_res.status_code == 201
    scan_2_id = scan_2_res.json()["scan_id"]
    draft_2_id = scan_2_res.json()["draft_id"]

    review_2_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_2_id, "scan_id": scan_2_id, "decision": "rejected", "comment": "Rejected scan 2."},
        headers={"X-User-Role": "reviewer", "X-User-Id": "rev-pass-2"},
    )
    assert review_2_res.status_code == 201
    review_2_id = review_2_res.json()["id"]

    # 4. Attempt direct SQL insertion of second passport targeting scan_1_id with review_2_id
    async def insert_duplicate_passport():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO passports (id, draft_id, scan_id, review_id, passport_hash, status, metadata_snapshot, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, NOW());
                """,
                uuid.uuid4(),
                uuid.UUID(draft_1_id),
                uuid.UUID(scan_1_id),
                uuid.UUID(review_2_id),
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "valid",
                json.dumps({"test": "attempt_duplicate_passport_for_same_scan"}),
            )
        finally:
            await conn.close()

    # 5. Assert PostgreSQL raises UniqueViolationError referencing uq_passports_scan_id
    with pytest.raises(asyncpg.UniqueViolationError) as exc_info:
        asyncio.run(insert_duplicate_passport())

    err_msg = str(exc_info.value)
    assert "uq_passports_scan_id" in err_msg or "scan_id" in err_msg

    # 6. Verify exactly 1 passport remains in database for scan_1_id
    async def count_passports():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            return await conn.fetch("SELECT id FROM passports WHERE scan_id = $1;", uuid.UUID(scan_1_id))
        finally:
            await conn.close()

    passports = asyncio.run(count_passports())
    assert len(passports) == 1
