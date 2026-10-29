"""Agent Chat Protocol (ACP) Adapter for ASI:One Compatibility.

Implements the official Fetch.ai Agent Chat Protocol (chat_protocol_spec) allowing
the VerifiBrand agent to receive natural language and structured messages from ASI:One,
dispatch them to the authoritative VerifiBrand backend service, and reply with
formatted evidence, citations, and status receipts.
"""
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from agent.models import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ExplainBlockRequest,
    ExplainBlockResponse,
    VerifyPassportRequest,
    VerifyPassportResponse,
)
from agent.service import VerifiBrandAgentService

logger = logging.getLogger(__name__)


def create_agent_chat_protocol(
    service: Optional[VerifiBrandAgentService] = None,
) -> Protocol:
    """Instantiate and configure the official Agent Chat Protocol (ACP) for ASI:One."""
    svc = service or VerifiBrandAgentService()
    protocol = Protocol(spec=chat_protocol_spec)

    # 1. Incoming ChatMessage handler (ASI:One conversation loop)
    @protocol.on_message(ChatMessage)
    async def handle_chat_message(
        ctx: Context,
        sender: str,
        msg: ChatMessage,
    ) -> None:
        ctx.logger.info(f"Received ACP ChatMessage from {sender} (msg_id={msg.msg_id})")

        # Step 1: Immediately acknowledge message receipt
        ack = ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
            metadata={"status": "processing"},
        )
        await ctx.send(sender, ack)

        # Step 2: Extract text content from message envelope
        incoming_text = ""
        for content in msg.content:
            if isinstance(content, TextContent):
                incoming_text = content.text
                break

        ctx.logger.debug(f"Processing message content from {sender}: {incoming_text[:120]}...")

        # Step 3: Authoritative service execution
        response_text = await process_chat_query(incoming_text, svc)

        # Step 4: Transmit structured reply back to ASI:One
        reply_message = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid.uuid4(),
            content=[TextContent(type="text", text=response_text)],
        )
        await ctx.send(sender, reply_message)
        ctx.logger.info(f"Dispatched ACP response to {sender}")

    # 2. ChatAcknowledgement handler (for delivery receipts)
    @protocol.on_message(ChatAcknowledgement)
    async def handle_chat_acknowledgement(
        ctx: Context,
        sender: str,
        msg: ChatAcknowledgement,
    ) -> None:
        ctx.logger.debug(
            f"Received ACP delivery acknowledgement from {sender} "
            f"for message {msg.acknowledged_msg_id}"
        )

    # Verify protocol implements official spec
    assert protocol.verify(), "AgentChatProtocol failed verification against official specification."
    return protocol


# ==============================================================================
# Query Routing & Response Formatting for ASI:One
# ==============================================================================

async def process_chat_query(
    raw_text: str,
    service: VerifiBrandAgentService,
) -> str:
    """Parse incoming prompt from ASI:One, execute backend action, and format response."""
    text = (raw_text or "").strip()
    if not text:
        return _format_help_menu("Received empty request.")

    # 1. Attempt JSON Payload Parsing
    parsed_json = _try_parse_json(text)
    if parsed_json:
        action = str(parsed_json.get("action", "")).lower()
        if action in ("check_compliance", "compliance", "scan"):
            return await _handle_compliance_action(parsed_json, service)
        if action in ("explain_block", "explain", "gate"):
            return await _handle_explain_action(parsed_json, service)
        if action in ("verify_passport", "passport"):
            return await _handle_passport_action(parsed_json, service)

    # 2. Conversational & Keyword Matching
    lower_text = text.lower()

    # Action C: Verify Passport (UUID detection)
    uuid_match = re.search(
        r"([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
        text,
    )
    if "passport" in lower_text or (uuid_match and ("verify" in lower_text or "check" in lower_text)):
        passport_id = uuid_match.group(1) if uuid_match else text.split()[-1]
        return await _handle_passport_action({"passport_id": passport_id}, service)

    # Action B: Explain Publication Block
    if any(k in lower_text for k in ("explain block", "why was", "gate decision", "block reason", "why blocked")):
        event_match = re.search(r"(?:event_id|event)\s*[:=]?\s*([a-zA-Z0-9_\-]+)", text, re.I)
        scan_match = re.search(r"(?:scan_id|scan)\s*[:=]?\s*([a-fA-F0-9\-]{36})", text, re.I)
        event_id = event_match.group(1) if event_match else None
        scan_id = scan_match.group(1) if scan_match else None

        # Fallback if bare event id like evt_... is present
        if not event_id and not scan_id:
            bare_event = re.search(r"(evt_[a-zA-Z0-9_\-]+)", text)
            if bare_event:
                event_id = bare_event.group(1)

        if event_id or scan_id:
            return await _handle_explain_action({"event_id": event_id, "scan_id": scan_id}, service)

    # Action A: Check Creative Compliance
    if any(k in lower_text for k in ("check compliance", "scan creative", "compliance check", "verify creative", "check copy")):
        title_match = re.search(r'title\s*[:=]\s*["\']?([^"\'\n,]+)["\']?', text, re.I)
        text_match = re.search(r'(?:content|text|copy)\s*[:=]\s*["\']?([^"\'\n]+)["\']?', text, re.I)

        title = title_match.group(1).strip() if title_match else "Marketing Creative"
        content_text = text_match.group(1).strip() if text_match else text
        return await _handle_compliance_action({"title": title, "content_text": content_text}, service)

    # Default: Show Interactive Capabilities Menu
    return _format_help_menu()


# ==============================================================================
# Action Handlers & Markdown Formatters
# ==============================================================================

async def _handle_compliance_action(
    payload: Dict[str, Any],
    service: VerifiBrandAgentService,
) -> str:
    """Execute Action A and format for ASI:One."""
    title = str(payload.get("title", "Marketing Creative"))
    content_text = str(payload.get("content_text", payload.get("text", "")))
    draft_id = payload.get("draft_id")
    scan_date = payload.get("scan_date")

    req = ComplianceCheckRequest(
        title=title,
        content_text=content_text,
        draft_id=draft_id,
        scan_date=scan_date,
    )
    resp: ComplianceCheckResponse = await service.check_creative_compliance(req)

    # Markdown formatting
    status_emoji = "✅" if resp.decision == "PASS" else ("⚠️" if resp.decision == "FLAG" else "🚫")
    lines = [
        f"### {status_emoji} VerifiBrand Creative Compliance Report",
        f"- **Compliance Decision:** **`{resp.decision}`**",
        f"- **Execution Status:** {resp.status}",
        f"- **Blockers Detected:** {'YES (publication blocked)' if resp.has_blockers else 'NO'}",
        f"- **Total Findings:** {resp.total_findings}",
        f"- **Summary:** {resp.summary}",
    ]

    if resp.scan_id:
        lines.append(f"- **Scan ID:** `{resp.scan_id}`")

    if resp.findings:
        lines.append("\n#### 📜 Authoritative Policy Receipts & Evidence:")
        for idx, f in enumerate(resp.findings, start=1):
            p_id = f.get("policy_card_id", "Unknown")
            p_ver = f.get("policy_version", "1.0.0")
            cat = f.get("category", "violation")
            sev = f.get("severity", "info")
            matched = f.get("matched_text", "")
            quote = f.get("source_quote", "")
            expl = f.get("explanation", "")
            fix = f.get("suggested_fix", "")

            lines.append(f"\n**{idx}. [{p_id} v{p_ver}] ({cat.upper()} | Severity: {sev.upper()})**")
            lines.append(f"- **Offending Copy:** \"{matched}\"")
            lines.append(f"- **Approved Policy Rule:** \"{quote}\"")
            lines.append(f"- **Violation Analysis:** {expl}")
            if fix:
                lines.append(f"- **Actionable Correction:** {fix}")

    if resp.error:
        lines.append(f"\n> **Warning / Error:** {resp.error}")

    return "\n".join(lines)


async def _handle_explain_action(
    payload: Dict[str, Any],
    service: VerifiBrandAgentService,
) -> str:
    """Execute Action B and format for ASI:One."""
    event_id = payload.get("event_id")
    scan_id = payload.get("scan_id")

    req = ExplainBlockRequest(event_id=event_id, scan_id=scan_id)
    resp: ExplainBlockResponse = await service.explain_publication_blocks(req)

    status_emoji = "🚫" if resp.decision == "BLOCK" else "✅"
    lines = [
        f"### {status_emoji} VerifiBrand Publication Gate Explanation",
        f"- **Gate Decision:** **`{resp.decision}`**",
    ]
    if resp.event_id:
        lines.append(f"- **Event Identifier:** `{resp.event_id}`")
    if resp.reason:
        lines.append(f"- **Machine Reason Code:** `{resp.reason}`")

    lines.append(f"- **Primary Explanation:** {resp.explanation}")

    if resp.passport_hash_verified is not None:
        hash_status = "VERIFIED (Valid SHA-256 snapshot)" if resp.passport_hash_verified else "FAILED (Tampered / Hash Mismatch)"
        lines.append(f"- **Cryptographic Passport Check:** {hash_status}")

    if resp.detailed_breakdown:
        lines.append("\n#### 🔍 Detailed Evidence & Breakdown:")
        for item in resp.detailed_breakdown:
            lines.append(f"- {item}")

    if resp.error:
        lines.append(f"\n> **Status Detail:** {resp.error}")

    return "\n".join(lines)


async def _handle_passport_action(
    payload: Dict[str, Any],
    service: VerifiBrandAgentService,
) -> str:
    """Execute Action C and format for ASI:One."""
    passport_id = str(payload.get("passport_id", "")).strip()

    req = VerifyPassportRequest(passport_id=passport_id)
    resp: VerifyPassportResponse = await service.verify_brand_passport(req)

    status_emoji = "🛡️" if resp.verification_status == "VERIFIED" else "⚠️"
    if resp.verification_status == "TAMPERED":
        status_emoji = "🚨"

    lines = [
        f"### {status_emoji} VerifiBrand Content Passport Certificate Verification",
        f"- **Passport Identifier:** `{resp.passport_id}`",
        f"- **Verification Outcome:** **`{resp.verification_status}`**",
        f"- **Official Assessment:** {resp.message}",
    ]

    if resp.hash_verified is not None:
        lines.append(
            f"- **Cryptographic Integrity:** "
            f"{'VALID (SHA-256 fingerprint matches canonical snapshot)' if resp.hash_verified else 'COMPROMISED (Cryptographic hash divergence detected)'}"
        )

    if resp.passport_hash:
        lines.append(f"- **SHA-256 Digest:** `{resp.passport_hash}`")

    if resp.status:
        lines.append(f"- **Governance Status:** `{resp.status}`")

    if resp.created_at:
        lines.append(f"- **Issuance Timestamp:** {resp.created_at}")

    if resp.metadata_summary:
        lines.append(f"- **Reviewer Sign-off:** {resp.metadata_summary.get('reviewer_id', 'N/A')}")
        lines.append(f"- **Referenced Policies:** {', '.join(resp.metadata_summary.get('policy_versions', [])) or 'None'}")

    if resp.error:
        lines.append(f"\n> **Lookup Error:** {resp.error}")

    return "\n".join(lines)


def _format_help_menu(preface: str = "") -> str:
    """Return an interactive capabilities guide for ASI:One users."""
    prefix = f"{preface}\n\n" if preface else ""
    return (
        f"{prefix}### 🤖 VerifiBrand Governance Agent (ASI:One Interface)\n\n"
        "I provide authoritative brand safety, publication gate enforcement, and "
        "Content Passport verification connected directly to the BrandLedger backend.\n\n"
        "**Available Actions:**\n\n"
        "1. **Check Creative Compliance**\n"
        "   - *Prompt:* `Check compliance: title=\"Summer Launch\" text=\"Get our eco-friendly guarantee today!\"`\n"
        "   - *JSON:* `{\"action\": \"check_compliance\", \"title\": \"...\", \"content_text\": \"...\"}`\n\n"
        "2. **Explain Publication Blocks**\n"
        "   - *Prompt:* `Why was event evt_blocked_12345 blocked?`\n"
        "   - *JSON:* `{\"action\": \"explain_block\", \"event_id\": \"evt_blocked_12345\"}`\n\n"
        "3. **Verify Brand Passport**\n"
        "   - *Prompt:* `Verify passport 3fa85f64-5717-4562-b3fc-2c963f66afa6`\n"
        "   - *JSON:* `{\"action\": \"verify_passport\", \"passport_id\": \"<UUID>\"}`\n"
    )


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON dictionary if present."""
    trimmed = text.strip()
    if trimmed.startswith("{") and trimmed.endswith("}"):
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None
