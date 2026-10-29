"""Automated Integration Tests for Authenticated CMS Publication Gate (Phase 2).

Tests execute against live FastAPI backend and PostgreSQL database (port 5433).
Verifies:
- HMAC-SHA256 signature verification (valid, missing, invalid signatures).
- Malformed and missing identifier requests.
- Valid publication decision (PASS when approved, verified, and 0 blockers).
- Active blocking findings resulting in BLOCK with verbatim policy receipts.
- Unapproved draft resulting in BLOCK.
- Missing, nonexistent, or tampered Content Passport resulting in BLOCK.
- Copy modified post-approval resulting in BLOCK.
- Duplicate-event protection and idempotency (cached decision with duplicate=True).
- Concurrent duplicate delivery safety.
- Strict prevention of gate overriding the authoritative compliance engine.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.db import db_manager
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """TestClient managing lifespan (DB connect and disconnect)."""
    with TestClient(app) as test_client:
        yield test_client


def _sign(body_bytes: bytes, secret: str = settings.CMS_WEBHOOK_SECRET) -> str:
    """Helper to compute HMAC-SHA256 signature for test requests."""
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ==============================================================================
# 1. AUTHENTICATION TESTS
# ==============================================================================

def test_missing_signature_header_returns_401(client: TestClient) -> None:
    """Verify that requests missing X-BrandLedger-Signature header are rejected with 401."""
    payload = json.dumps({"event_id": f"evt_{uuid.uuid4().hex[:8]}"}).encode("utf-8")
    response = client.post(
        "/api/gate/publish",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401
    assert "Missing X-BrandLedger-Signature" in response.json()["detail"]


def test_invalid_signature_returns_401(client: TestClient) -> None:
    """Verify that requests with invalid HMAC signatures are rejected with 401."""
    payload = json.dumps({"event_id": f"evt_{uuid.uuid4().hex[:8]}"}).encode("utf-8")
    response = client.post(
        "/api/gate/publish",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": "sha256=invalid_deadbeef_signature_00000000000000000000",
        },
    )
    assert response.status_code == 401
    assert "Invalid HMAC-SHA256" in response.json()["detail"]


def test_valid_signature_with_malformed_json_returns_400(client: TestClient) -> None:
    """Verify that authenticated requests with malformed JSON return 400 Bad Request."""
    malformed_body = b"not-a-valid-json-string{"
    sig = _sign(malformed_body)
    response = client.post(
        "/api/gate/publish",
        content=malformed_body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 400
    assert "Malformed request" in response.json()["detail"]


def test_missing_identifiers_returns_block_400(client: TestClient) -> None:
    """Verify that requests without draft_id or passport_id are cleanly blocked."""
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id}).encode("utf-8")
    sig = _sign(body)
    response = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["reason"] == "MISSING_IDENTIFIERS"


# ==============================================================================
# 2. VALID PUBLICATION PASS FLOW
# ==============================================================================

def test_valid_publication_decision_passes_when_approved_and_verified(client: TestClient) -> None:
    """Verify full end-to-end PASS when draft is compliant, reviewed, and passport verified."""
    # 1. Create and scan compliant draft
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Compliant Summer Launch",
            "content_text": "Welcome Members! Enjoy standard pricing across all our categories.",
            "scan_date": "2026-07-01",
        },
    )
    assert scan_res.status_code == 201
    scan_data = scan_res.json()
    scan_id = scan_data["scan_id"]
    draft_id = scan_data["draft_id"]
    assert scan_data["has_blockers"] is False

    # 2. Human Reviewer Approves
    review_res = client.post(
        "/api/reviews",
        json={
            "draft_id": draft_id,
            "scan_id": scan_id,
            "decision": "approved",
            "comment": "Full compliance cleared. Ready for digital publication.",
        },
        headers={
            "X-User-Role": "reviewer",
            "X-User-Id": "rev-101",
            "X-User-Name": "Compliance Director Sarah",
        },
    )
    assert review_res.status_code == 201
    passport_id = review_res.json()["passport_id"]
    assert passport_id is not None

    # 3. CMS Webhook triggers publication gate
    event_id = f"evt_pass_{uuid.uuid4().hex[:8]}"
    gate_payload = {
        "event_id": event_id,
        "draft_id": draft_id,
        "passport_id": passport_id,
        "scan_id": scan_id,
    }
    body = json.dumps(gate_payload).encode("utf-8")
    sig = _sign(body)

    gate_res = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert gate_res.status_code == 200
    gate_data = gate_res.json()
    assert gate_data["event_id"] == event_id
    assert gate_data["decision"] == "PASS"
    assert gate_data["reason"] == "PUBLICATION_AUTHORIZED"
    assert gate_data["passport_hash_verified"] is True
    assert gate_data["total_blockers"] == 0
    assert gate_data["duplicate"] is False


# ==============================================================================
# 3. COMPLIANCE BLOCK FLOWS
# ==============================================================================

def test_blocking_findings_results_in_block(client: TestClient) -> None:
    """Verify that a draft with active rule blockers returns BLOCK with exact policy citations."""
    # 1. Create and scan draft with violations (expired offer + prohibited terminology)
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Violating Promo Post",
            "content_text": "Our customers can access the exclusive Summer Discount today!",
            "scan_date": "2026-07-01",
        },
    )
    assert scan_res.status_code == 201
    scan_data = scan_res.json()
    draft_id = scan_data["draft_id"]
    scan_id = scan_data["scan_id"]
    assert scan_data["has_blockers"] is True
    assert scan_data["total_findings"] >= 2

    # 2. CMS Webhook evaluates publication
    event_id = f"evt_block_findings_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id, "draft_id": draft_id, "scan_id": scan_id}).encode("utf-8")
    sig = _sign(body)

    response = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["reason"] == "ACTIVE_BLOCKING_FINDINGS"
    assert data["total_blockers"] >= 2
    assert len(data["findings"]) >= 2

    # Verify exact policy receipts are included
    categories = {f["category"] for f in data["findings"]}
    assert "terminology" in categories
    assert "expired_offer" in categories
    for f in data["findings"]:
        assert f["source_quote"], "Must contain verbatim quoted receipt"
        assert f["policy_version"], "Must contain exact policy version"
        assert f["explanation"], "Must contain explanation"


def test_unapproved_draft_results_in_block(client: TestClient) -> None:
    """Verify that a compliant draft that has NOT received reviewer approval is BLOCKED."""
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Unapproved Clean Draft",
            "content_text": "Welcome Members! Enjoy standard pricing.",
        },
    )
    assert scan_res.status_code == 201
    draft_id = scan_res.json()["draft_id"]

    event_id = f"evt_unapproved_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id, "draft_id": draft_id}).encode("utf-8")
    sig = _sign(body)

    response = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["reason"] == "DRAFT_NOT_APPROVED"


def test_nonexistent_draft_results_in_block(client: TestClient) -> None:
    """Verify that querying a nonexistent draft returns a clear BLOCK."""
    fake_id = str(uuid.uuid4())
    event_id = f"evt_fake_draft_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id, "draft_id": fake_id}).encode("utf-8")
    sig = _sign(body)

    response = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["reason"] == "DRAFT_NOT_FOUND"


def test_nonexistent_passport_results_in_block(client: TestClient) -> None:
    """Verify that querying a nonexistent passport returns a clear BLOCK."""
    fake_id = str(uuid.uuid4())
    event_id = f"evt_fake_passport_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id, "passport_id": fake_id}).encode("utf-8")
    sig = _sign(body)

    response = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["reason"] == "PASSPORT_NOT_FOUND"


# ==============================================================================
# 4. CRYPTOGRAPHIC TAMPER DETECTION AND COPY MODIFICATION
# ==============================================================================

def test_tampered_passport_results_in_block(client: TestClient) -> None:
    """Verify that a tampered database row causes cryptographic hash failure and is BLOCKED."""
    # 1. Create compliant draft and get approved Content Passport
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Tamper Test Draft",
            "content_text": "Welcome Members! Enjoy standard pricing.",
        },
    )
    draft_id = scan_res.json()["draft_id"]
    scan_id = scan_res.json()["scan_id"]

    review_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved", "comment": "Approved"},
        headers={"X-User-Role": "reviewer"},
    )
    passport_id = review_res.json()["passport_id"]

    # 2. Simulate database tampering by modifying the stored snapshot
    tampered_snapshot = {
        "draft_id": str(draft_id),
        "draft_title": "Tampered Title",
        "draft_content": "Unauthorized altered copy",
        "decision": "approved",
    }
    # Direct database manipulation to simulate an attacker altering PostgreSQL records
    import asyncio
    import asyncpg
    async def _tamper():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            await conn.execute(
                "UPDATE passports SET metadata_snapshot = $1::jsonb WHERE id = $2;",
                json.dumps(tampered_snapshot),
                uuid.UUID(passport_id),
            )
        finally:
            await conn.close()
    asyncio.run(_tamper())

    # 3. Publish gate must catch cryptographic hash mismatch

    event_id = f"evt_tamper_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id, "passport_id": passport_id}).encode("utf-8")
    sig = _sign(body)

    response = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["reason"] == "PASSPORT_TAMPERED"
    assert data["passport_hash_verified"] is False


def test_content_modified_post_approval_results_in_block(client: TestClient) -> None:
    """Verify that submitting content text that does not match the approved passport copy is BLOCKED."""
    # 1. Create compliant draft and approve
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Copy Integrity Draft",
            "content_text": "Welcome Members! Enjoy standard pricing.",
        },
    )
    draft_id = scan_res.json()["draft_id"]
    scan_id = scan_res.json()["scan_id"]

    review_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved", "comment": "Approved"},
        headers={"X-User-Role": "reviewer"},
    )
    passport_id = review_res.json()["passport_id"]

    # 2. CMS tries to publish with modified copy
    event_id = f"evt_modified_copy_{uuid.uuid4().hex[:8]}"
    body = json.dumps({
        "event_id": event_id,
        "passport_id": passport_id,
        "content_text": "Sneaky modified text with unauthorized discount promises!",
    }).encode("utf-8")
    sig = _sign(body)

    response = client.post(
        "/api/gate/publish",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": sig,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["reason"] == "CONTENT_MODIFIED_POST_APPROVAL"


# ==============================================================================
# 5. DUPLICATE-EVENT PROTECTION & CONCURRENCY
# ==============================================================================

def test_duplicate_event_returns_previously_recorded_decision(client: TestClient) -> None:
    """Verify that re-delivering an identical event_id returns the cached decision without duplicate scan."""
    # 1. Create compliant approved asset
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Idempotency Test Asset",
            "content_text": "Welcome Members! Enjoy standard pricing.",
        },
    )
    draft_id = scan_res.json()["draft_id"]
    scan_id = scan_res.json()["scan_id"]

    review_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved", "comment": "Approved"},
        headers={"X-User-Role": "reviewer"},
    )
    passport_id = review_res.json()["passport_id"]

    event_id = f"evt_idempotency_{uuid.uuid4().hex[:8]}"
    body = json.dumps({
        "event_id": event_id,
        "draft_id": draft_id,
        "passport_id": passport_id,
    }).encode("utf-8")
    sig = _sign(body)

    # First delivery
    res_1 = client.post(
        "/api/gate/publish",
        content=body,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": sig},
    )
    assert res_1.status_code == 200
    data_1 = res_1.json()
    assert data_1["decision"] == "PASS"
    assert data_1["duplicate"] is False

    # Second delivery (Duplicate event)
    res_2 = client.post(
        "/api/gate/publish",
        content=body,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": sig},
    )
    assert res_2.status_code == 200
    data_2 = res_2.json()
    assert data_2["decision"] == "PASS"
    assert data_2["duplicate"] is True
    assert data_2["event_id"] == event_id

    # Verify only ONE row was written to publication_events table
    import asyncio
    import asyncpg
    async def _count_events():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM publication_events WHERE event_id = $1;",
                event_id,
            )
        finally:
            await conn.close()

    count = asyncio.run(_count_events())
    assert count == 1, "Database must store exactly 1 record per unique event_id"


def test_concurrent_duplicate_deliveries_safe(client: TestClient) -> None:
    """Verify that multiple concurrent deliveries of the same event_id are handled safely."""
    event_id = f"evt_concurrent_{uuid.uuid4().hex[:8]}"
    body = json.dumps({
        "event_id": event_id,
        "draft_id": str(uuid.uuid4()),  # nonexistent draft triggers consistent BLOCK
    }).encode("utf-8")
    sig = _sign(body)

    def _send_request():
        return client.post(
            "/api/gate/publish",
            content=body,
            headers={"Content-Type": "application/json", "X-BrandLedger-Signature": sig},
        )

    # Dispatch 5 simultaneous requests in parallel threads
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_send_request) for _ in range(5)]
        responses = [f.result() for f in futures]

    # All must return 200 with identical decision
    for r in responses:
        assert r.status_code == 200
        assert r.json()["decision"] == "BLOCK"
        assert r.json()["reason"] == "DRAFT_NOT_FOUND"

    # Exactly 1 row in database
    import asyncio
    import asyncpg
    async def _count_events_concurrent():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM publication_events WHERE event_id = $1;",
                event_id,
            )
        finally:
            await conn.close()

    count = asyncio.run(_count_events_concurrent())
    assert count == 1, "Concurrent requests must safely produce exactly 1 database record"



# ==============================================================================
# 6. ENGINE AUTHORITY PRESERVATION
# ==============================================================================

def test_gate_cannot_override_authoritative_engine_decision(client: TestClient) -> None:
    """Verify that the gate strictly respects backend review and scan results and cannot independently authorize unapproved content."""
    # 1. Create draft with violation
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Strict Engine Authority Draft",
            "content_text": "Hey customers, access Summer Discount now!",
            "scan_date": "2026-07-01",
        },
    )
    draft_id = scan_res.json()["draft_id"]
    scan_id = scan_res.json()["scan_id"]

    # 2. Reject draft in review gate
    client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "rejected", "comment": "Strictly rejected"},
        headers={"X-User-Role": "reviewer"},
    )

    # 3. Attempt to publish
    event_id = f"evt_strict_auth_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id, "draft_id": draft_id, "scan_id": scan_id}).encode("utf-8")
    sig = _sign(body)

    res = client.post(
        "/api/gate/publish",
        content=body,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": sig},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "BLOCK"
    # Gate cannot force a PASS on rejected or violating content
    assert data["decision"] != "PASS"


# ==============================================================================
# 7. GET /api/gate/{event_id} RETRIEVAL FOR AGENT EXPLANATIONS
# ==============================================================================

def test_get_gate_event_success(client: TestClient) -> None:
    """Verify that a recorded publication event can be retrieved by event_id."""
    event_id = f"evt_recorded_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id}).encode("utf-8")
    sig = _sign(body)

    # 1. Evaluate and record event
    post_res = client.post(
        "/api/gate/publish",
        content=body,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": sig},
    )
    assert post_res.status_code == 200
    expected_decision = post_res.json()["decision"]

    # 2. Retrieve event by event_id
    get_res = client.get(f"/api/gate/{event_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["event_id"] == event_id
    assert retrieved["decision"] == expected_decision


def test_get_gate_event_not_found(client: TestClient) -> None:
    """Verify that querying a nonexistent event_id returns 404."""
    res = client.get("/api/gate/evt_nonexistent_random_id_99999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
