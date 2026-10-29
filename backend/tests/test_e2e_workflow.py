"""End-to-End Integrated Validation Workflow Tests (Phase 5).

Validates the complete integrated lifecycle against the real PostgreSQL database
and live FastAPI backend:
1. Start DB and FastAPI backend.
2. Load approved brand policies and create test drafts.
3. Execute authoritative compliance scan.
4. Verify both blocking and non-blocking content detection.
5. Exercise reviewer approval and Content Passport creation via existing APIs.
6. Cryptographically verify the Content Passport and its SHA-256 snapshot hash.
7. Send correctly signed publication-gate webhook requests (HMAC-SHA256).
8. Confirm PASS only when approval, clean scan, and valid passport are satisfied.
9. Confirm BLOCK when a blocker exists, approval is missing, or passport verification fails.
10. Resend an event and verify idempotency (same payload returns duplicate=True; different payload returns 409 Conflict).
11. Exercise Fetch.ai agent's three actions and ACP handler against the running backend.
12. Verify that unavailable services and malformed responses NEVER become false successes.
"""
import asyncio
from datetime import datetime
import hashlib
import hmac
import json
import os
import uuid
import asyncpg
import pytest
from fastapi.testclient import TestClient

from agent.client import (
    BackendClient,
    BackendConnectionError,
    BackendNotFoundError,
    BackendResponseError,
)
from agent.config import AgentConfig
from agent.models import (
    ComplianceCheckRequest,
    ExplainBlockRequest,
    VerifyPassportRequest,
)
from agent.chat import process_chat_query
from agent.service import VerifiBrandAgentService
from backend.app.config import settings
from backend.app.main import app

# Ensure deterministic evaluation during integration tests
os.environ["BRANDLEDGER_DISABLE_AI"] = "true"


@pytest.fixture(scope="module")
def client():
    """TestClient managing FastAPI application lifespan and database connection."""
    with TestClient(app) as test_client:
        yield test_client


def _sign(body_bytes: bytes, secret: str = settings.CMS_WEBHOOK_SECRET) -> str:
    """Helper to calculate HMAC-SHA256 signature for test requests."""
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ==============================================================================
# End-to-End Test 1: Full Happy Path Lifecycle (Steps 1 through 8)
# ==============================================================================

def test_e2e_happy_path_publication_lifecycle(client: TestClient) -> None:
    """Validate full compliant workflow from scan to approval, passport, and gate PASS."""
    # 1. Authoritative compliance scan on clean draft
    clean_title = f"E2E Summer Campaign {uuid.uuid4().hex[:6]}"
    clean_copy = "Welcome Members! Enjoy our approved standard pricing and services."

    scan_res = client.post(
        "/api/scans",
        json={"title": clean_title, "content_text": clean_copy},
    )
    assert scan_res.status_code == 201, scan_res.text
    scan_data = scan_res.json()
    assert scan_data["status"] == "completed"
    assert scan_data["has_blockers"] is False
    assert scan_data["total_findings"] == 0

    scan_id = scan_data["scan_id"]
    draft_id = scan_data["draft_id"]

    # 2. Human Reviewer Approval via POST /api/reviews
    review_headers = {
        "X-User-Role": "reviewer",
        "X-User-Id": "rev-e2e-001",
        "X-User-Name": "Lead Compliance Officer",
    }
    review_payload = {
        "draft_id": draft_id,
        "scan_id": scan_id,
        "decision": "approved",
        "comment": "All checks cleared. Copy conforms strictly to brand guidelines.",
    }
    review_res = client.post("/api/reviews", json=review_payload, headers=review_headers)
    assert review_res.status_code == 201, review_res.text
    review_data = review_res.json()
    assert review_data["decision"] == "approved"
    assert review_data["passport_id"] is not None

    passport_id = review_data["passport_id"]

    # 3. Verify Content Passport certificate via GET /api/passports/{passport_id}
    passport_res = client.get(f"/api/passports/{passport_id}")
    assert passport_res.status_code == 200, passport_res.text
    passport_data = passport_res.json()
    assert passport_data["status"] == "valid"
    assert passport_data["hash_verified"] is True
    assert len(passport_data["passport_hash"]) == 64

    # 4. Signed Publication Gate request via POST /api/gate/publish
    event_id = f"evt_e2e_pass_{uuid.uuid4().hex[:8]}"
    gate_payload = {
        "event_id": event_id,
        "draft_id": draft_id,
        "scan_id": scan_id,
        "passport_id": passport_id,
        "content_text": clean_copy,
    }
    raw_body = json.dumps(gate_payload).encode("utf-8")
    signature = _sign(raw_body)

    gate_res = client.post(
        "/api/gate/publish",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": signature,
        },
    )
    assert gate_res.status_code == 200, gate_res.text
    gate_data = gate_res.json()

    # Step 8: Confirm PASS only when all criteria are satisfied
    assert gate_data["decision"] == "PASS"
    assert gate_data["reason"] == "PUBLICATION_AUTHORIZED"
    assert gate_data["passport_hash_verified"] is True
    assert gate_data["total_blockers"] == 0
    assert gate_data["duplicate"] is False


# ==============================================================================
# End-to-End Test 2: Blocking Content & Gate Rejection (Steps 4 & 9)
# ==============================================================================

def test_e2e_blocking_content_rejected_at_scan_and_gate(client: TestClient) -> None:
    """Validate that policy violations are caught by scanner and blocked by gate."""
    # 1. Authoritative scan on non-compliant draft (uses prohibited term "Customers")
    bad_title = f"E2E Violation Campaign {uuid.uuid4().hex[:6]}"
    bad_copy = "Attention Customers! This is our exclusive promotion."

    scan_res = client.post(
        "/api/scans",
        json={"title": bad_title, "content_text": bad_copy},
    )
    assert scan_res.status_code == 201, scan_res.text
    scan_data = scan_res.json()
    assert scan_data["has_blockers"] is True
    assert scan_data["total_findings"] >= 1

    # Verify policy evidence citation
    blocker = next(f for f in scan_data["findings"] if f["severity"] in ("blocker", "high"))
    assert blocker["category"] == "terminology"
    assert blocker["matched_text"].lower() == "customers"
    assert "Members" in blocker["suggested_fix"]

    draft_id = scan_data["draft_id"]
    scan_id = scan_data["scan_id"]

    # 2. Gate evaluation directly on blocking draft (without approval) -> BLOCK
    event_id = f"evt_e2e_block_{uuid.uuid4().hex[:8]}"
    gate_payload = {
        "event_id": event_id,
        "draft_id": draft_id,
        "scan_id": scan_id,
    }
    raw_body = json.dumps(gate_payload).encode("utf-8")
    gate_res = client.post(
        "/api/gate/publish",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": _sign(raw_body),
        },
    )
    assert gate_res.status_code == 200
    gate_data = gate_res.json()
    assert gate_data["decision"] == "BLOCK"
    assert gate_data["reason"] == "ACTIVE_BLOCKING_FINDINGS"
    assert gate_data["total_blockers"] >= 1
    assert len(gate_data["findings"]) >= 1


def test_e2e_unapproved_draft_blocked_at_gate(client: TestClient) -> None:
    """Validate that clean draft without human reviewer approval is rejected."""
    # Create clean scan, but do NOT call /api/reviews
    scan_res = client.post(
        "/api/scans",
        json={
            "title": "Clean But Unapproved Draft",
            "content_text": "Members receive premium concierge support.",
        },
    )
    assert scan_res.status_code == 201
    draft_id = scan_res.json()["draft_id"]

    event_id = f"evt_e2e_unapproved_{uuid.uuid4().hex[:8]}"
    gate_payload = {"event_id": event_id, "draft_id": draft_id}
    raw_body = json.dumps(gate_payload).encode("utf-8")

    gate_res = client.post(
        "/api/gate/publish",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": _sign(raw_body),
        },
    )
    assert gate_res.status_code == 200
    gate_data = gate_res.json()
    assert gate_data["decision"] == "BLOCK"
    assert gate_data["reason"] == "DRAFT_NOT_APPROVED"


# ==============================================================================
# End-to-End Test 3: Tampered Passport Detection (Step 9)
# ==============================================================================

def test_e2e_tampered_passport_blocked_at_gate(client: TestClient) -> None:
    """Validate that cryptographically tampered passports are immediately rejected."""
    # 1. Create compliant approved draft with passport
    scan_res = client.post(
        "/api/scans",
        json={"title": "Tamper Target", "content_text": "Members only exclusive offer."},
    )
    assert scan_res.status_code == 201
    draft_id = scan_res.json()["draft_id"]
    scan_id = scan_res.json()["scan_id"]

    review_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved", "comment": "OK"},
        headers={"X-User-Role": "reviewer"},
    )
    assert review_res.status_code == 201
    passport_id = review_res.json()["passport_id"]

    # 2. Corrupt passport hash in database using direct independent connection
    fake_hash = "deadbeef" * 8

    async def corrupt_db():
        conn = await asyncpg.connect(settings.DATABASE_URL)
        try:
            await conn.execute(
                "UPDATE passports SET passport_hash = $1 WHERE id = $2;",
                fake_hash,
                uuid.UUID(passport_id),
            )
        finally:
            await conn.close()

    asyncio.run(corrupt_db())

    # 3. Gate request with tampered passport -> BLOCK
    event_id = f"evt_e2e_tamper_{uuid.uuid4().hex[:8]}"
    gate_payload = {
        "event_id": event_id,
        "draft_id": draft_id,
        "passport_id": passport_id,
    }
    raw_body = json.dumps(gate_payload).encode("utf-8")
    gate_res = client.post(
        "/api/gate/publish",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-BrandLedger-Signature": _sign(raw_body),
        },
    )
    assert gate_res.status_code == 200
    gate_data = gate_res.json()
    assert gate_data["decision"] == "BLOCK"
    assert gate_data["reason"] == "PASSPORT_TAMPERED"
    assert gate_data["passport_hash_verified"] is False


# ==============================================================================
# End-to-End Test 4: Idempotency & Conflict Protection (Step 10)
# ==============================================================================

def test_e2e_idempotency_and_conflict_protection(client: TestClient) -> None:
    """Confirm idempotency on repeated events and conflict rejection for different payloads."""
    # 1. Create compliant approved draft
    scan_res = client.post(
        "/api/scans",
        json={"title": "Idempotency Draft", "content_text": "Members welcome!"},
    )
    draft_id = scan_res.json()["draft_id"]
    scan_id = scan_res.json()["scan_id"]

    review_res = client.post(
        "/api/reviews",
        json={"draft_id": draft_id, "scan_id": scan_id, "decision": "approved", "comment": "Approved"},
        headers={"X-User-Role": "reviewer"},
    )
    passport_id = review_res.json()["passport_id"]

    event_id = f"evt_e2e_idem_{uuid.uuid4().hex[:8]}"
    initial_payload = {
        "event_id": event_id,
        "draft_id": draft_id,
        "scan_id": scan_id,
        "passport_id": passport_id,
    }
    raw_body_1 = json.dumps(initial_payload).encode("utf-8")

    # Initial delivery -> 200 PASS
    r1 = client.post(
        "/api/gate/publish",
        content=raw_body_1,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": _sign(raw_body_1)},
    )
    assert r1.status_code == 200
    assert r1.json()["decision"] == "PASS"
    assert r1.json()["duplicate"] is False

    # Exact duplicate delivery -> 200 with duplicate=True
    r2 = client.post(
        "/api/gate/publish",
        content=raw_body_1,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": _sign(raw_body_1)},
    )
    assert r2.status_code == 200
    assert r2.json()["decision"] == "PASS"
    assert r2.json()["duplicate"] is True

    # Same event_id with DIFFERENT payload (different draft_id) -> 409 Conflict
    different_payload = {
        "event_id": event_id,
        "draft_id": str(uuid.uuid4()),  # Altered draft ID
        "scan_id": scan_id,
        "passport_id": passport_id,
    }
    raw_body_diff = json.dumps(different_payload).encode("utf-8")
    r3 = client.post(
        "/api/gate/publish",
        content=raw_body_diff,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": _sign(raw_body_diff)},
    )
    assert r3.status_code == 409, r3.text
    assert "Repeated event IDs cannot cause duplicate processing" in r3.json()["detail"]


# ==============================================================================
# End-to-End Test 5: Agent Actions & ACP Protocol (Step 11)
# ==============================================================================

class LiveBackendAdapter(BackendClient):
    """Adapter delegating BackendClient methods directly to the live FastAPI TestClient."""

    def __init__(self, test_client: TestClient, config: AgentConfig):
        super().__init__(config)
        self.test_client = test_client

    async def submit_scan(self, title: str, content_text: str, draft_id=None, scan_date=None):
        payload = {"title": title, "content_text": content_text}
        if draft_id:
            payload["draft_id"] = draft_id
        if scan_date:
            payload["scan_date"] = scan_date
        r = self.test_client.post("/api/scans", json=payload)
        if r.status_code in (200, 201):
            return r.json()
        raise BackendResponseError(r.status_code, self._extract_error_detail(r))

    async def get_scan(self, scan_id: str):
        r = self.test_client.get(f"/api/scans/{scan_id.strip()}")
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            raise BackendNotFoundError(f"Scan attempt '{scan_id}' not found.")
        raise BackendResponseError(r.status_code, self._extract_error_detail(r))

    async def get_gate_event(self, event_id: str):
        r = self.test_client.get(f"/api/gate/{event_id.strip()}")
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            raise BackendNotFoundError(f"Publication event '{event_id}' not found.")
        raise BackendResponseError(r.status_code, self._extract_error_detail(r))

    async def get_passport(self, passport_id: str):
        r = self.test_client.get(f"/api/passports/{passport_id.strip()}")
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            raise BackendNotFoundError(f"Content Passport '{passport_id}' not found.")
        raise BackendResponseError(r.status_code, self._extract_error_detail(r))


@pytest.mark.asyncio
async def test_e2e_agent_actions_and_acp_against_backend(client: TestClient) -> None:
    """Exercise the Fetch.ai agent's three actions and ACP handler against the backend."""
    agent_config = AgentConfig(
        BACKEND_URL="http://127.0.0.1:8000",
        ENVIRONMENT="testing",
        AGENT_PORT=8001,
        AGENT_SEED="test-agent-seed-for-e2e-testing-only-phrase",
    )
    backend_adapter = LiveBackendAdapter(client, agent_config)
    agent_service = VerifiBrandAgentService(config=agent_config, client=backend_adapter)

    # 1. Action A: Check Creative Compliance via agent
    # Compliant check -> PASS
    comp_req = ComplianceCheckRequest(
        title="Agent Clean Ad",
        content_text="Welcome Members to our new experience.",
    )
    comp_res = await agent_service.check_creative_compliance(comp_req)
    assert comp_res.success is True
    assert comp_res.decision == "PASS"
    assert comp_res.has_blockers is False

    # Non-compliant check -> BLOCK
    bad_comp_req = ComplianceCheckRequest(
        title="Agent Bad Ad",
        content_text="Welcome Customers to our new experience.",
    )
    bad_comp_res = await agent_service.check_creative_compliance(bad_comp_req)
    assert bad_comp_res.success is True
    assert bad_comp_res.decision == "BLOCK"
    assert bad_comp_res.has_blockers is True
    assert len(bad_comp_res.findings) >= 1

    # 2. Action B: Explain Publication Block via agent
    # First create and record a blocked gate event
    scan_res = client.post(
        "/api/scans",
        json={"title": "Blocked Event For Agent", "content_text": "Special deals for Customers."},
    )
    draft_id = scan_res.json()["draft_id"]
    scan_id = scan_res.json()["scan_id"]

    event_id = f"evt_agent_explain_{uuid.uuid4().hex[:8]}"
    body = json.dumps({"event_id": event_id, "draft_id": draft_id, "scan_id": scan_id}).encode("utf-8")
    client.post(
        "/api/gate/publish",
        content=body,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": _sign(body)},
    )

    explain_req = ExplainBlockRequest(event_id=event_id)
    explain_res = await agent_service.explain_publication_blocks(explain_req)
    assert explain_res.success is True
    assert explain_res.decision == "BLOCK"
    assert "Customers" in str(explain_res.detailed_breakdown)
    assert len(explain_res.findings) >= 1

    # 3. Action C: Verify Brand Passport via agent
    # Create an approved draft with valid passport
    good_scan = client.post(
        "/api/scans",
        json={"title": "Passport for Agent", "content_text": "Members receive 100% satisfaction."},
    )
    rev_res = client.post(
        "/api/reviews",
        json={"draft_id": good_scan.json()["draft_id"], "scan_id": good_scan.json()["scan_id"], "decision": "approved", "comment": "OK"},
        headers={"X-User-Role": "reviewer"},
    )
    passport_id = rev_res.json()["passport_id"]

    verify_req = VerifyPassportRequest(passport_id=passport_id)
    verify_res = await agent_service.verify_brand_passport(verify_req)
    assert verify_res.success is True
    assert verify_res.verification_status == "VERIFIED"
    assert verify_res.hash_verified is True

    # 4. Agent Chat Protocol (ACP) query handling
    chat_query = f"Verify brand passport {passport_id}"
    chat_reply = await process_chat_query(chat_query, agent_service)
    assert "VERIFIED" in chat_reply
    assert passport_id in chat_reply


# ==============================================================================
# End-to-End Test 6: Resiliency & Failure Handling (Step 12)
# ==============================================================================

@pytest.mark.asyncio
async def test_e2e_unavailable_services_never_become_false_success(client: TestClient) -> None:
    """Verify that service outages and malformed requests never report false successes."""
    # 1. Agent targeting offline backend (port 9999)
    offline_config = AgentConfig(
        BACKEND_URL="http://127.0.0.1:9999",
        BACKEND_TIMEOUT_SECONDS=1.0,
        ENVIRONMENT="testing",
        AGENT_PORT=8001,
        AGENT_SEED="offline-test-agent-seed-mnemonic-safeguard",
    )
    offline_service = VerifiBrandAgentService(config=offline_config)

    # Compliance check when backend is offline -> BLOCK with success=False, NEVER PASS
    res_a = await offline_service.check_creative_compliance(
        ComplianceCheckRequest(title="Test", content_text="Members only.")
    )
    assert res_a.success is False
    assert res_a.decision == "BLOCK"
    assert "unreachable" in res_a.error.lower()

    # Explain block when backend is offline -> UNKNOWN with success=False
    res_b = await offline_service.explain_publication_blocks(
        ExplainBlockRequest(event_id="evt_nonexistent_offline")
    )
    assert res_b.success is False
    assert res_b.decision == "UNKNOWN"

    # Verify passport when backend is offline -> ERROR with verified=False, NEVER VERIFIED
    res_c = await offline_service.verify_brand_passport(
        VerifyPassportRequest(passport_id=str(uuid.uuid4()))
    )
    assert res_c.success is False
    assert res_c.verification_status == "ERROR"
    assert res_c.hash_verified is None

    # 2. Gate API security rejections:
    # Missing signature -> 401
    bad_sig_res = client.post(
        "/api/gate/publish",
        json={"event_id": "evt_no_sig"},
    )
    assert bad_sig_res.status_code == 401

    # Invalid signature -> 401
    invalid_sig_res = client.post(
        "/api/gate/publish",
        json={"event_id": "evt_bad_sig"},
        headers={"X-BrandLedger-Signature": "sha256=invalidhex000000000000000000000000"},
    )
    assert invalid_sig_res.status_code == 401

    # Malformed JSON with valid signature -> 400
    raw_bad = b"This is not JSON at all"
    malformed_res = client.post(
        "/api/gate/publish",
        content=raw_bad,
        headers={"Content-Type": "application/json", "X-BrandLedger-Signature": _sign(raw_bad)},
    )
    assert malformed_res.status_code == 400
