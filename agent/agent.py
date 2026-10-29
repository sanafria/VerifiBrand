"""Fetch.ai Agent Definition and Dual Protocol Mounting for VerifiBrand.

Configures the official uagents.Agent instance with:
1. VerifiBrandAgentProtocol (1.0.0): Structured model protocol for direct agent-to-agent RPC
2. AgentChatProtocol (0.3.0): Official Fetch.ai ACP for ASI:One conversational interaction
3. Agentverse metadata (name, handle, description, discovery tags)
4. Configurable Mailbox / Public Endpoint networking
"""
import asyncio
import logging
from typing import Optional
from uagents import Agent, Context, Protocol

from agent.chat import create_agent_chat_protocol
from agent.config import AgentConfig, get_agent_config
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

# Official Protocol Identifier
VERIFIBRAND_PROTOCOL_NAME = "VerifiBrandAgentProtocol"
VERIFIBRAND_PROTOCOL_VERSION = "1.0.0"


def create_verifibrand_protocol(
    service: Optional[VerifiBrandAgentService] = None,
) -> Protocol:
    """Create and configure the VerifiBrand direct RPC Protocol."""
    svc = service or VerifiBrandAgentService()
    protocol = Protocol(
        name=VERIFIBRAND_PROTOCOL_NAME,
        version=VERIFIBRAND_PROTOCOL_VERSION,
    )

    # Action A: Check Creative Compliance Handler
    @protocol.on_message(
        model=ComplianceCheckRequest,
        replies=ComplianceCheckResponse,
    )
    async def handle_compliance_check(
        ctx: Context,
        sender: str,
        msg: ComplianceCheckRequest,
    ) -> None:
        ctx.logger.info(f"Received creative compliance check request from {sender}: title='{msg.title}'")
        response = await svc.check_creative_compliance(msg)
        ctx.logger.info(
            f"Compliance decision for {sender}: outcome='{response.decision}', "
            f"total_findings={response.total_findings}, has_blockers={response.has_blockers}"
        )
        await ctx.send(sender, response)

    # Action B: Explain Publication Blocks Handler
    @protocol.on_message(
        model=ExplainBlockRequest,
        replies=ExplainBlockResponse,
    )
    async def handle_explain_block(
        ctx: Context,
        sender: str,
        msg: ExplainBlockRequest,
    ) -> None:
        target_id = msg.event_id or msg.scan_id or "unknown"
        ctx.logger.info(f"Received block explanation request from {sender} for identifier='{target_id}'")
        response = await svc.explain_publication_blocks(msg)
        ctx.logger.info(
            f"Explanation generated for {sender}: decision='{response.decision}', "
            f"reason='{response.reason}', findings_count={len(response.findings)}"
        )
        await ctx.send(sender, response)

    # Action C: Verify Brand Passport Handler
    @protocol.on_message(
        model=VerifyPassportRequest,
        replies=VerifyPassportResponse,
    )
    async def handle_verify_passport(
        ctx: Context,
        sender: str,
        msg: VerifyPassportRequest,
    ) -> None:
        ctx.logger.info(f"Received passport verification request from {sender} for id='{msg.passport_id}'")
        response = await svc.verify_brand_passport(msg)
        ctx.logger.info(
            f"Passport verification outcome for {sender}: status='{response.verification_status}', "
            f"hash_verified={response.hash_verified}"
        )
        await ctx.send(sender, response)

    return protocol


def create_verifibrand_agent(
    config: Optional[AgentConfig] = None,
    service: Optional[VerifiBrandAgentService] = None,
) -> Agent:
    """Instantiate and configure the official Fetch.ai Agent for VerifiBrand.

    Mounts both:
    1. VerifiBrandAgentProtocol (direct RPC)
    2. AgentChatProtocol (ASI:One ACP compatibility)

    Applies discovery metadata for Agentverse and Almanac indexers.
    """
    cfg = config or get_agent_config()
    svc = service or VerifiBrandAgentService(config=cfg)

    # Networking and Mailbox determination
    mailbox = bool(cfg.AGENTVERSE_MAILBOX and cfg.AGENTVERSE_API_KEY)
    endpoint = None
    if not mailbox:
        endpoint = [cfg.AGENT_ENDPOINT] if cfg.AGENT_ENDPOINT else [f"http://127.0.0.1:{cfg.AGENT_PORT}/submit"]

    agentverse_config = None
    if cfg.AGENTVERSE_API_KEY:
        agentverse_config = f"{cfg.AGENTVERSE_API_KEY}@agentverse.ai"

    metadata = {
        "description": cfg.AGENT_DESCRIPTION,
        "tags": cfg.AGENT_TAGS,
        "handle": cfg.AGENT_HANDLE,
    }

    # Ensure an active event loop exists for uagents on Python 3.10+
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

    # Initialize official uAgents Agent
    agent = Agent(
        name=cfg.AGENT_NAME,
        loop=loop,
        port=cfg.AGENT_PORT,
        seed=cfg.AGENT_SEED,
        endpoint=endpoint,
        mailbox=mailbox,
        agentverse=agentverse_config,
        metadata=metadata,
        publish_agent_details=True,
    )

    # 1. Attach direct typed protocol (Phase 3 RPC)
    direct_protocol = create_verifibrand_protocol(svc)
    agent.include(direct_protocol, publish_manifest=True)

    # 2. Attach Agent Chat Protocol (Phase 4 ASI:One ACP)
    chat_protocol = create_agent_chat_protocol(svc)
    agent.include(chat_protocol, publish_manifest=True)

    # Attach service and config to agent for programmatic access
    agent.service = svc  # type: ignore[attr-defined]
    agent.config = cfg   # type: ignore[attr-defined]

    return agent
