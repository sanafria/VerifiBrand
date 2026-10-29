"""Tests for VerifiBrand Fetch.ai Agent Core (Phase 3).

Validates:
1. Agent startup, configuration, and sensitive secret masking.
2. Action A: Creative compliance checks (PASS, FLAG, BLOCK, input validation, backend down/timeout).
3. Action B: Publication block explanations (BLOCK with evidence, PASS with no block, tampered passport, 404 not found, scan fallback).
4. Action C: Brand Passport verification (VERIFIED, TAMPERED, REVOKED, NOT_FOUND, invalid UUID, backend down).
5. Confirmation that agent does not fabricate findings or override backend decisions.
6. Local test isolation without requiring Agentverse or external network dependencies.
"""
import uuid
from typing import Any, Dict
from unittest.mock import AsyncMock, patch
import pytest

from agent.agent import create_verifibrand_agent, create_verifibrand_protocol
from agent.client import (
    BackendClient,
    BackendConnectionError,
    BackendNotFoundError,
    BackendResponseError,
    BackendTimeoutError,
)
from agent.config import AgentConfig
from agent.models import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ExplainBlockRequest,
    ExplainBlockResponse,
    VerifyPassportRequest,
    VerifyPassportResponse,
)
from agent.chat import create_agent_chat_protocol, process_chat_query
from agent.register import register_agent_with_agentverse
from agent.service import VerifiBrandAgentService
from uagents.mailbox import RegistrationResponse
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
)


# ==============================================================================
# 1. Configuration, Startup, and Secret Masking Tests
# ==============================================================================

def test_agent_config_masking_secrets():
    """Verify that agent secrets are safely redacted in summaries and logs."""
    config = AgentConfig(
        AGENT_SEED="super-secret-mnemonic-phrase-brandledger-2026",
        BACKEND_URL="http://127.0.0.1:8000",
        AGENT_PORT=8001,
    )
    safe_summary = config.get_safe_summary()

    # Secret phrase must NEVER appear unredacted
    assert "super-secret-mnemonic-phrase-brandledger-2026" not in str(safe_summary)
    assert safe_summary["AGENT_SEED"].startswith("supe***")
    assert safe_summary["AGENT_PORT"] == 8001
    assert safe_summary["BACKEND_URL"] == "http://127.0.0.1:8000"


def test_agent_instantiation_and_protocol_mounting():
    """Verify Fetch.ai Agent initializes with deterministic identity and protocol."""
    config = AgentConfig(
        AGENT_NAME="test_verifibrand_agent",
        AGENT_PORT=8005,
        AGENT_SEED="consistent-test-seed-for-unit-tests-only",
    )
    agent = create_verifibrand_agent(config=config)

    assert agent.name == "test_verifibrand_agent"
    assert agent.address.startswith("agent1")
    assert agent.identifier.startswith("agent://agent1")
    assert hasattr(agent, "service")
    assert "VerifiBrandAgentProtocol" in [p.name for p in agent.protocols.values()]


# ==============================================================================
# 2. Action A: Check Creative Compliance Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_compliance_check_success_pass():
    """Verify creative compliance check passes when backend detects zero findings."""
    mock_client = AsyncMock(spec=BackendClient)
    mock_client.submit_scan.return_value = {
        "scan_id": str(uuid.uuid4()),
        "draft_id": str(uuid.uuid4()),
        "status": "completed",
        "has_blockers": False,
        "total_findings": 0,
        "findings": [],
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = ComplianceCheckRequest(
        title="Spring Collection Launch",
        content_text="Check out our new sustainably crafted spring collection available today.",
    )
    resp: ComplianceCheckResponse = await service.check_creative_compliance(req)

    assert resp.success is True
    assert resp.decision == "PASS"
    assert resp.has_blockers is False
    assert resp.total_findings == 0
    assert len(resp.findings) == 0
    assert "zero violations" in resp.summary.lower()


@pytest.mark.asyncio
async def test_compliance_check_with_blocking_findings():
    """Verify creative compliance check returns BLOCK with verbatim policy receipts."""
    mock_client = AsyncMock(spec=BackendClient)
    scan_id = str(uuid.uuid4())
    draft_id = str(uuid.uuid4())

    mock_client.submit_scan.return_value = {
        "scan_id": scan_id,
        "draft_id": draft_id,
        "status": "completed",
        "has_blockers": True,
        "total_findings": 2,
        "findings": [
            {
                "policy_card_id": "PC-TERM-001",
                "policy_version": "1.0.0",
                "category": "terminology",
                "severity": "high",
                "matched_text": "eco-friendly guarantee",
                "source_quote": "Do not claim 'eco-friendly guarantee' without certified third-party audit.",
                "explanation": "Unsubstantiated green claim violates terminology guideline.",
                "suggested_fix": "Use 'sustainably sourced' with certification badge link.",
                "confidence": 0.95,
                "is_verified": True,
            },
            {
                "policy_card_id": "PC-EXP-002",
                "policy_version": "1.1.0",
                "category": "expired_offer",
                "severity": "high",
                "matched_text": "50% off holiday special",
                "source_quote": "Holiday promotional campaign concluded on January 15.",
                "explanation": "Promotional offer has expired.",
                "suggested_fix": "Remove expired discount language.",
                "confidence": 1.0,
                "is_verified": True,
            },
        ],
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = ComplianceCheckRequest(
        title="Promotional Banner Copy",
        content_text="Get our eco-friendly guarantee with 50% off holiday special!",
    )
    resp: ComplianceCheckResponse = await service.check_creative_compliance(req)

    assert resp.success is True
    assert resp.decision == "BLOCK"
    assert resp.has_blockers is True
    assert resp.total_findings == 2
    assert len(resp.findings) == 2

    # Check verbatim policy citation retention
    f1 = resp.findings[0]
    assert f1["policy_card_id"] == "PC-TERM-001"
    assert f1["matched_text"] == "eco-friendly guarantee"
    assert "Do not claim" in f1["source_quote"]
    assert f1["suggested_fix"] == "Use 'sustainably sourced' with certification badge link."

    f2 = resp.findings[1]
    assert f2["policy_card_id"] == "PC-EXP-002"
    assert f2["matched_text"] == "50% off holiday special"


@pytest.mark.asyncio
async def test_compliance_check_advisory_flag():
    """Verify non-blocking advisory findings result in FLAG decision."""
    mock_client = AsyncMock(spec=BackendClient)
    mock_client.submit_scan.return_value = {
        "scan_id": str(uuid.uuid4()),
        "draft_id": str(uuid.uuid4()),
        "status": "completed",
        "has_blockers": False,
        "total_findings": 1,
        "findings": [
            {
                "policy_card_id": "PC-TONE-003",
                "policy_version": "1.0.0",
                "category": "tone",
                "severity": "low",
                "matched_text": "hurry up guys",
                "source_quote": "Maintain professional, inclusive tone across marketing channels.",
                "explanation": "Informal phrasing flagged for advisory tone review.",
                "suggested_fix": "Consider 'Explore our latest arrivals'.",
                "confidence": 0.8,
                "is_verified": True,
            }
        ],
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = ComplianceCheckRequest(
        title="Casual Announcement",
        content_text="Hurry up guys and see our new store!",
    )
    resp = await service.check_creative_compliance(req)

    assert resp.success is True
    assert resp.decision == "FLAG"
    assert resp.has_blockers is False
    assert resp.total_findings == 1
    assert "advisory finding(s)" in resp.summary


@pytest.mark.asyncio
async def test_compliance_check_input_validation():
    """Verify input validation rejects empty titles, whitespace, and empty creative text."""
    service = VerifiBrandAgentService(client=AsyncMock(spec=BackendClient))

    # Pydantic schema validation rejects empty string (min_length=1)
    with pytest.raises(Exception):
        ComplianceCheckRequest(title="", content_text="Valid text")

    with pytest.raises(Exception):
        ComplianceCheckRequest(title="Valid Title", content_text="")

    # Service-level validation catches whitespace-only inputs
    resp_whitespace_title = await service.check_creative_compliance(
        ComplianceCheckRequest(title="   ", content_text="Valid text")
    )
    assert resp_whitespace_title.success is False
    assert resp_whitespace_title.decision == "BLOCK"
    assert "Title is required" in resp_whitespace_title.error

    resp_whitespace_content = await service.check_creative_compliance(
        ComplianceCheckRequest(title="Valid Title", content_text="   ")
    )
    assert resp_whitespace_content.success is False
    assert resp_whitespace_content.decision == "BLOCK"
    assert "Creative text is required" in resp_whitespace_content.error


@pytest.mark.asyncio
async def test_compliance_check_backend_timeout_and_offline():
    """Verify graceful handling when backend is unreachable or times out."""
    mock_client = AsyncMock(spec=BackendClient)

    # Backend Connection Error
    mock_client.submit_scan.side_effect = BackendConnectionError("Connection refused")
    service = VerifiBrandAgentService(client=mock_client)

    resp_offline = await service.check_creative_compliance(
        ComplianceCheckRequest(title="Test", content_text="Some copy")
    )
    assert resp_offline.success is False
    assert resp_offline.decision == "BLOCK"
    assert "unreachable" in resp_offline.summary.lower()

    # Backend Timeout Error
    mock_client.submit_scan.side_effect = BackendTimeoutError("Timed out after 10s")
    resp_timeout = await service.check_creative_compliance(
        ComplianceCheckRequest(title="Test", content_text="Some copy")
    )
    assert resp_timeout.success is False
    assert resp_timeout.decision == "BLOCK"
    assert "timed out" in resp_timeout.summary.lower()


# ==============================================================================
# 3. Action B: Explain Publication Blocks Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_explain_publication_block_with_evidence():
    """Verify explanation of blocked publication event translates reasons and evidence clearly."""
    mock_client = AsyncMock(spec=BackendClient)
    event_id = "cms_evt_blocked_9876"

    mock_client.get_gate_event.return_value = {
        "event_id": event_id,
        "decision": "BLOCK",
        "reason": "BLOCK_COMPLIANCE_FINDINGS",
        "explanation": "Asset has 1 active compliance blocker.",
        "passport_id": None,
        "passport_hash_verified": None,
        "scan_id": str(uuid.uuid4()),
        "findings": [
            {
                "policy_card_id": "PC-CLAIM-004",
                "policy_version": "2.0.0",
                "category": "unsupported_claim",
                "severity": "high",
                "matched_text": "100% cure rate guaranteed",
                "source_quote": "Medical claims require FDA approval certification reference.",
                "explanation": "Unverified clinical claim prohibited.",
                "suggested_fix": "Remove curative statement or cite approved clinical study.",
            }
        ],
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = ExplainBlockRequest(event_id=event_id)
    resp: ExplainBlockResponse = await service.explain_publication_blocks(req)

    assert resp.success is True
    assert resp.decision == "BLOCK"
    assert resp.event_id == event_id
    assert resp.reason == "BLOCK_COMPLIANCE_FINDINGS"
    assert "active compliance policy violations" in resp.explanation.lower()
    assert len(resp.detailed_breakdown) >= 2
    assert any("PC-CLAIM-004" in b for b in resp.detailed_breakdown)
    assert any("100% cure rate guaranteed" in b for b in resp.detailed_breakdown)
    assert any("Medical claims require" in b for b in resp.detailed_breakdown)


@pytest.mark.asyncio
async def test_explain_publication_event_passed_does_not_claim_block():
    """Verify that an approved (PASS) publication event is never falsely reported as blocked."""
    mock_client = AsyncMock(spec=BackendClient)
    event_id = "cms_evt_approved_1122"

    mock_client.get_gate_event.return_value = {
        "event_id": event_id,
        "decision": "PASS",
        "reason": "PASS_APPROVED_PASSPORT",
        "explanation": "Authorized Content Passport verified with zero blockers.",
        "passport_id": str(uuid.uuid4()),
        "passport_hash_verified": True,
        "findings": [],
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = ExplainBlockRequest(event_id=event_id)
    resp: ExplainBlockResponse = await service.explain_publication_blocks(req)

    assert resp.success is True
    assert resp.decision == "PASS"
    assert "no publication block occurred" in resp.explanation.lower()
    assert resp.passport_hash_verified is True
    assert any("APPROVED (PASS)" in b for b in resp.detailed_breakdown)


@pytest.mark.asyncio
async def test_explain_publication_block_passport_tampered():
    """Verify explanation specifically highlights cryptographic hash mismatch."""
    mock_client = AsyncMock(spec=BackendClient)
    event_id = "cms_evt_tampered_3344"
    passport_id = str(uuid.uuid4())

    mock_client.get_gate_event.return_value = {
        "event_id": event_id,
        "decision": "BLOCK",
        "reason": "BLOCK_PASSPORT_TAMPERED",
        "explanation": "Cryptographic signature check failed.",
        "passport_id": passport_id,
        "passport_hash_verified": False,
        "findings": [],
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = ExplainBlockRequest(event_id=event_id)
    resp: ExplainBlockResponse = await service.explain_publication_blocks(req)

    assert resp.success is True
    assert resp.decision == "BLOCK"
    assert resp.reason == "BLOCK_PASSPORT_TAMPERED"
    assert resp.passport_hash_verified is False
    assert any("Cryptographic Integrity Alert" in b for b in resp.detailed_breakdown)


@pytest.mark.asyncio
async def test_explain_publication_event_not_found():
    """Verify 404 from backend returns clean error message without guessing."""
    mock_client = AsyncMock(spec=BackendClient)
    mock_client.get_gate_event.side_effect = BackendNotFoundError("Event not found")

    service = VerifiBrandAgentService(client=mock_client)
    req = ExplainBlockRequest(event_id="cms_evt_nonexistent_9999")
    resp = await service.explain_publication_blocks(req)

    assert resp.success is False
    assert resp.decision == "UNKNOWN"
    assert "was not found" in resp.explanation
    assert "not found" in resp.error.lower()


@pytest.mark.asyncio
async def test_explain_block_fallback_to_scan_id():
    """Verify fallback to scan ID when event ID is not provided."""
    mock_client = AsyncMock(spec=BackendClient)
    scan_id = str(uuid.uuid4())

    mock_client.get_scan.return_value = {
        "scan_id": scan_id,
        "draft_id": str(uuid.uuid4()),
        "has_blockers": True,
        "total_findings": 1,
        "findings": [
            {
                "policy_card_id": "PC-EXP-001",
                "policy_version": "1.0.0",
                "category": "expired_offer",
                "matched_text": "expired code XMAS2025",
                "source_quote": "Promotional codes expire after 30 days.",
                "explanation": "Code has expired.",
                "suggested_fix": "Use current promo code.",
            }
        ],
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = ExplainBlockRequest(scan_id=scan_id)
    resp = await service.explain_publication_blocks(req)

    assert resp.success is True
    assert resp.decision == "BLOCK"
    assert resp.scan_id == scan_id
    assert any("PC-EXP-001" in b for b in resp.detailed_breakdown)


@pytest.mark.asyncio
async def test_explain_block_missing_identifiers():
    """Verify validation when neither event_id nor scan_id is provided."""
    service = VerifiBrandAgentService(client=AsyncMock(spec=BackendClient))
    resp = await service.explain_publication_blocks(ExplainBlockRequest())

    assert resp.success is False
    assert resp.decision == "UNKNOWN"
    assert "event_id or scan_id required" in resp.error


# ==============================================================================
# 4. Action C: Verify Brand Passport Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_verify_passport_verified_and_valid():
    """Verify passport with valid status and verified canonical hash returns VERIFIED."""
    mock_client = AsyncMock(spec=BackendClient)
    passport_id = str(uuid.uuid4())
    draft_id = str(uuid.uuid4())
    scan_id = str(uuid.uuid4())
    review_id = str(uuid.uuid4())

    mock_client.get_passport.return_value = {
        "id": passport_id,
        "draft_id": draft_id,
        "scan_id": scan_id,
        "review_id": review_id,
        "passport_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "status": "valid",
        "hash_verified": True,
        "created_at": "2026-10-29T12:00:00Z",
        "metadata_snapshot": {
            "reviewer_id": "rev_admin_1",
            "draft_title": "Certified Campaign Copy",
            "total_findings": 0,
            "policy_versions": {"PC-TERM-001": "1.0.0"},
        },
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = VerifyPassportRequest(passport_id=passport_id)
    resp: VerifyPassportResponse = await service.verify_brand_passport(req)

    assert resp.success is True
    assert resp.verification_status == "VERIFIED"
    assert resp.hash_verified is True
    assert resp.passport_id == passport_id
    assert resp.status == "valid"
    assert "verified" in resp.message.lower()
    assert "cryptographically authentic" in resp.message.lower()
    assert resp.metadata_summary["reviewer_id"] == "rev_admin_1"


@pytest.mark.asyncio
async def test_verify_passport_tampered_hash_mismatch():
    """Verify passport with hash mismatch is strictly classified as TAMPERED."""
    mock_client = AsyncMock(spec=BackendClient)
    passport_id = str(uuid.uuid4())

    mock_client.get_passport.return_value = {
        "id": passport_id,
        "draft_id": str(uuid.uuid4()),
        "scan_id": str(uuid.uuid4()),
        "review_id": str(uuid.uuid4()),
        "passport_hash": "tampered_hash_value_1234567890abcdef",
        "status": "valid",
        "hash_verified": False,  # Backend detected hash divergence!
        "created_at": "2026-10-29T12:00:00Z",
        "metadata_snapshot": {},
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = VerifyPassportRequest(passport_id=passport_id)
    resp: VerifyPassportResponse = await service.verify_brand_passport(req)

    assert resp.success is True
    assert resp.verification_status == "TAMPERED"
    assert resp.hash_verified is False
    assert "critical integrity failure" in resp.message.lower()
    assert "tampered" in resp.message.lower()


@pytest.mark.asyncio
async def test_verify_passport_revoked():
    """Verify revoked passport is classified as REVOKED even if hash is intact."""
    mock_client = AsyncMock(spec=BackendClient)
    passport_id = str(uuid.uuid4())

    mock_client.get_passport.return_value = {
        "id": passport_id,
        "draft_id": str(uuid.uuid4()),
        "scan_id": str(uuid.uuid4()),
        "review_id": str(uuid.uuid4()),
        "passport_hash": "valid_hash_9876543210abcdef",
        "status": "revoked",
        "hash_verified": True,
        "created_at": "2026-10-29T12:00:00Z",
        "metadata_snapshot": {},
    }

    service = VerifiBrandAgentService(client=mock_client)
    req = VerifyPassportRequest(passport_id=passport_id)
    resp = await service.verify_brand_passport(req)

    assert resp.success is True
    assert resp.verification_status == "REVOKED"
    assert resp.status == "revoked"
    assert "revoked by brand governance" in resp.message.lower()


@pytest.mark.asyncio
async def test_verify_passport_not_found():
    """Verify nonexistent passport ID returns NOT_FOUND status."""
    mock_client = AsyncMock(spec=BackendClient)
    passport_id = str(uuid.uuid4())
    mock_client.get_passport.side_effect = BackendNotFoundError("Passport not found")

    service = VerifiBrandAgentService(client=mock_client)
    req = VerifyPassportRequest(passport_id=passport_id)
    resp = await service.verify_brand_passport(req)

    assert resp.success is False
    assert resp.verification_status == "NOT_FOUND"
    assert "was not found" in resp.message.lower()
    assert "passport not found" in resp.error.lower()


@pytest.mark.asyncio
async def test_verify_passport_invalid_uuid():
    """Verify malformed non-UUID input is rejected with clear ERROR status."""
    service = VerifiBrandAgentService(client=AsyncMock(spec=BackendClient))
    req = VerifyPassportRequest(passport_id="malformed-not-a-uuid")
    resp = await service.verify_brand_passport(req)

    assert resp.success is False
    assert resp.verification_status == "ERROR"
    assert "Invalid UUID format" in resp.error


@pytest.mark.asyncio
async def test_verify_passport_backend_offline():
    """Verify backend connection error returns clean ERROR status."""
    mock_client = AsyncMock(spec=BackendClient)
    mock_client.get_passport.side_effect = BackendConnectionError("Connection refused")

    service = VerifiBrandAgentService(client=mock_client)
    req = VerifyPassportRequest(passport_id=str(uuid.uuid4()))
    resp = await service.verify_brand_passport(req)

    assert resp.success is False
    assert resp.verification_status == "ERROR"
    assert "unreachable" in resp.message.lower()


# ==============================================================================
# 5. Integrity & Non-Fabrication Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_agent_does_not_fabricate_findings_or_override_decisions():
    """Verify that agent strictly reflects backend data without fabricating rules."""
    mock_client = AsyncMock(spec=BackendClient)

    # Backend reports clean draft
    mock_client.submit_scan.return_value = {
        "scan_id": str(uuid.uuid4()),
        "draft_id": str(uuid.uuid4()),
        "status": "completed",
        "has_blockers": False,
        "total_findings": 0,
        "findings": [],
    }

    service = VerifiBrandAgentService(client=mock_client)
    resp = await service.check_creative_compliance(
        ComplianceCheckRequest(title="Clean Draft", content_text="Clean content.")
    )

    # Agent MUST NOT fabricate findings
    assert resp.decision == "PASS"
    assert resp.findings == []
    assert resp.total_findings == 0

    # Backend reports blocker
    mock_client.submit_scan.return_value["has_blockers"] = True
    mock_client.submit_scan.return_value["total_findings"] = 1
    mock_client.submit_scan.return_value["findings"] = [
        {
            "policy_card_id": "REAL-PC-01",
            "policy_version": "1.0",
            "category": "factual_accuracy",
            "matched_text": "real match",
            "source_quote": "real quote",
            "explanation": "real expl",
            "suggested_fix": "real fix",
        }
    ]

    resp_blocked = await service.check_creative_compliance(
        ComplianceCheckRequest(title="Blocked Draft", content_text="Bad content.")
    )

    # Agent MUST NOT downgrade blocker to PASS
    assert resp_blocked.decision == "BLOCK"
    assert len(resp_blocked.findings) == 1
    assert resp_blocked.findings[0]["policy_card_id"] == "REAL-PC-01"


# ==============================================================================
# 6. Phase 4: Agent Chat Protocol (ACP) & ASI:One Interaction Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_chat_protocol_compliance_check_pass():
    """Verify ASI:One chat query for creative compliance returns formatted report."""
    mock_client = AsyncMock(spec=BackendClient)
    mock_client.submit_scan.return_value = {
        "scan_id": str(uuid.uuid4()),
        "draft_id": str(uuid.uuid4()),
        "status": "completed",
        "has_blockers": False,
        "total_findings": 0,
        "findings": [],
    }

    service = VerifiBrandAgentService(client=mock_client)
    prompt = "Check compliance: title='Spring Launch' text='Sustainably crafted artisan boots.'"
    response_text = await process_chat_query(prompt, service)

    assert "Creative Compliance Report" in response_text
    assert "`PASS`" in response_text
    assert "Blockers Detected:** NO" in response_text


@pytest.mark.asyncio
async def test_chat_protocol_compliance_check_blocking_evidence():
    """Verify ASI:One chat query with blockers returns formatted receipts and fixes."""
    mock_client = AsyncMock(spec=BackendClient)
    mock_client.submit_scan.return_value = {
        "scan_id": str(uuid.uuid4()),
        "draft_id": str(uuid.uuid4()),
        "status": "completed",
        "has_blockers": True,
        "total_findings": 1,
        "findings": [
            {
                "policy_card_id": "PC-TERM-001",
                "policy_version": "1.0.0",
                "category": "terminology",
                "severity": "high",
                "matched_text": "eco-friendly guaranteed",
                "source_quote": "Do not claim 'eco-friendly guaranteed' without third-party audit.",
                "explanation": "Unsubstantiated environmental claim prohibited.",
                "suggested_fix": "Use 'sustainably sourced' with certification link.",
            }
        ],
    }

    service = VerifiBrandAgentService(client=mock_client)
    prompt = "Check compliance: title='Promo' text='Our eco-friendly guaranteed sneakers.'"
    response_text = await process_chat_query(prompt, service)

    assert "`BLOCK`" in response_text
    assert "PC-TERM-001 v1.0.0" in response_text
    assert "eco-friendly guaranteed" in response_text
    assert "Do not claim" in response_text
    assert "sustainably sourced" in response_text


@pytest.mark.asyncio
async def test_chat_protocol_json_input():
    """Verify structured JSON chat input from ASI:One is handled accurately."""
    mock_client = AsyncMock(spec=BackendClient)
    mock_client.submit_scan.return_value = {
        "scan_id": str(uuid.uuid4()),
        "draft_id": str(uuid.uuid4()),
        "status": "completed",
        "has_blockers": False,
        "total_findings": 0,
        "findings": [],
    }

    service = VerifiBrandAgentService(client=mock_client)
    json_prompt = '{"action": "check_compliance", "title": "JSON Post", "content_text": "Approved copy."}'
    response_text = await process_chat_query(json_prompt, service)

    assert "Creative Compliance Report" in response_text
    assert "`PASS`" in response_text


@pytest.mark.asyncio
async def test_chat_protocol_explain_block():
    """Verify ASI:One conversational query for block explanation returns breakdown."""
    mock_client = AsyncMock(spec=BackendClient)
    event_id = "evt_cms_blocked_9988"

    mock_client.get_gate_event.return_value = {
        "event_id": event_id,
        "decision": "BLOCK",
        "reason": "BLOCK_COMPLIANCE_FINDINGS",
        "explanation": "Draft copy contains 1 active compliance blocker.",
        "findings": [
            {
                "policy_card_id": "PC-CLAIM-002",
                "policy_version": "1.0.0",
                "category": "unsupported_claim",
                "matched_text": "100% cure rate",
                "source_quote": "Health claims require FDA certification.",
                "explanation": "Unsupported claim.",
                "suggested_fix": "Remove curative statement.",
            }
        ],
    }

    service = VerifiBrandAgentService(client=mock_client)
    prompt = f"Why was event {event_id} blocked?"
    response_text = await process_chat_query(prompt, service)

    assert "Publication Gate Explanation" in response_text
    assert "`BLOCK`" in response_text
    assert event_id in response_text
    assert "BLOCK_COMPLIANCE_FINDINGS" in response_text
    assert "PC-CLAIM-002" in response_text


@pytest.mark.asyncio
async def test_chat_protocol_explain_event_approved_pass():
    """Verify ASI:One query for passed event accurately reflects non-blocked status."""
    mock_client = AsyncMock(spec=BackendClient)
    event_id = "evt_approved_3344"

    mock_client.get_gate_event.return_value = {
        "event_id": event_id,
        "decision": "PASS",
        "reason": "PASS_APPROVED_PASSPORT",
        "explanation": "Asset approved with valid Content Passport.",
        "passport_hash_verified": True,
        "findings": [],
    }

    service = VerifiBrandAgentService(client=mock_client)
    prompt = f"Explain gate decision for event {event_id}"
    response_text = await process_chat_query(prompt, service)

    assert "`PASS`" in response_text
    assert "No publication block occurred" in response_text
    assert "SHA-256 hash valid" in response_text


@pytest.mark.asyncio
async def test_chat_protocol_verify_passport():
    """Verify ASI:One passport verification query returns cryptographic proof status."""
    mock_client = AsyncMock(spec=BackendClient)
    passport_id = str(uuid.uuid4())

    mock_client.get_passport.return_value = {
        "id": passport_id,
        "draft_id": str(uuid.uuid4()),
        "scan_id": str(uuid.uuid4()),
        "review_id": str(uuid.uuid4()),
        "passport_hash": "c4ca4238a0b923820dcc509a6f75849b",
        "status": "valid",
        "hash_verified": True,
        "created_at": "2026-10-29T14:00:00Z",
        "metadata_snapshot": {"reviewer_id": "auditor_1"},
    }

    service = VerifiBrandAgentService(client=mock_client)
    prompt = f"Verify passport {passport_id}"
    response_text = await process_chat_query(prompt, service)

    assert "Content Passport Certificate Verification" in response_text
    assert "`VERIFIED`" in response_text
    assert passport_id in response_text
    assert "c4ca4238a0b923820dcc509a6f75849b" in response_text


@pytest.mark.asyncio
async def test_chat_protocol_help_menu():
    """Verify greeting or unknown query returns interactive capabilities guide."""
    service = VerifiBrandAgentService(client=AsyncMock(spec=BackendClient))
    response_text = await process_chat_query("Hello! What can you do?", service)

    assert "VerifiBrand Governance Agent (ASI:One Interface)" in response_text
    assert "Check Creative Compliance" in response_text
    assert "Explain Publication Blocks" in response_text
    assert "Verify Brand Passport" in response_text


def test_agent_chat_protocol_mounting_and_verification():
    """Verify that create_agent_chat_protocol conforms to official chat_protocol_spec."""
    protocol = create_agent_chat_protocol()
    assert protocol.name == "AgentChatProtocol"
    assert protocol.version == "0.3.0"
    assert protocol.verify() is True


# ==============================================================================
# 7. Phase 4: Production Security & Strict Validation Tests
# ==============================================================================

def test_production_rejects_default_development_seed():
    """Verify that ENVIRONMENT=production strictly rejects development seeds."""
    with pytest.raises(ValueError) as exc_info:
        AgentConfig(
            ENVIRONMENT="production",
            AGENT_SEED="verifibrand-agent-development-seed-do-not-use-in-prod",
        )
    assert "Insecure development AGENT_SEED detected" in str(exc_info.value)

    # Reject dev-containing seed phrases
    with pytest.raises(ValueError):
        AgentConfig(
            ENVIRONMENT="production",
            AGENT_SEED="my-test-dev-seed-phrase",
        )


def test_production_rejects_insecure_http_endpoint():
    """Verify that ENVIRONMENT=production strictly rejects non-HTTPS public endpoints."""
    with pytest.raises(ValueError) as exc_info:
        AgentConfig(
            ENVIRONMENT="production",
            AGENT_SEED="strong-unique-secret-production-mnemonic-seed-phrase-2026",
            AGENT_ENDPOINT="http://insecure.brandledger.com/submit",
        )
    assert "must use HTTPS" in str(exc_info.value)


def test_production_accepts_valid_secure_configuration():
    """Verify production configuration succeeds with secure seed and HTTPS endpoint."""
    config = AgentConfig(
        ENVIRONMENT="production",
        AGENT_SEED="strong-unique-secret-production-mnemonic-seed-phrase-2026",
        AGENT_ENDPOINT="https://agent.brandledger.com/submit",
        AGENTVERSE_API_KEY="av_live_99887766554433221100",
    )
    assert config.ENVIRONMENT == "production"
    summary = config.get_safe_summary()
    assert "strong-unique" not in str(summary)
    assert summary["AGENT_ENDPOINT"] == "https://agent.brandledger.com/submit"
    assert summary["AGENTVERSE_API_KEY"].startswith("av_l***")


# ==============================================================================
# 8. Phase 4: Agentverse Registration Readiness Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_agentverse_registration_missing_api_key():
    """Verify registration fails safely with guidance when AGENTVERSE_API_KEY is unset."""
    config = AgentConfig(AGENTVERSE_API_KEY=None)
    result = await register_agent_with_agentverse(config)

    assert result["registered"] is False
    assert result["detail"] == "PREREQUISITES_MISSING"
    assert "https://agentverse.ai" in result["message"]
    assert "agent1" in result["agent_address"]


@pytest.mark.asyncio
async def test_agentverse_registration_mocked_success():
    """Verify challenge-response registration flow succeeds with valid credentials."""
    config = AgentConfig(
        AGENTVERSE_API_KEY="av_live_mock_api_token_12345678",
        AGENTVERSE_MAILBOX=True,
    )

    with patch("agent.register.register_in_agentverse", new_callable=AsyncMock) as mock_reg:
        mock_reg.return_value = RegistrationResponse(success=True)
        result = await register_agent_with_agentverse(config)

        assert result["registered"] is True
        assert result["detail"] == "SUCCESS"
        assert result["agent_type"] == "mailbox"
        assert mock_reg.called


@pytest.mark.asyncio
async def test_agentverse_registration_network_exception_handled():
    """Verify network exceptions during Agentverse registration are safely caught."""
    config = AgentConfig(
        AGENTVERSE_API_KEY="av_live_mock_api_token_12345678",
    )

    with patch("agent.register.register_in_agentverse", new_callable=AsyncMock) as mock_reg:
        mock_reg.side_effect = RuntimeError("Connection dropped by remote server")
        result = await register_agent_with_agentverse(config)

        assert result["registered"] is False
        assert "NETWORK_ERROR" in result["detail"]
