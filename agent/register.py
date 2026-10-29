"""Agentverse Registration and Mailbox Setup Script for VerifiBrand Agent.

Provides the official workflow for registering the VerifiBrand agent on Agentverse
and Almanac using challenge-response cryptographic proofs.

Pre-requisites for live Agentverse registration:
1. An active account at https://agentverse.ai
2. An API Key generated under Agentverse Profile -> API Keys (AGENTVERSE_API_KEY)
3. A unique production seed phrase (AGENT_SEED)
4. (Optional) A public HTTPS webhook endpoint (AGENT_ENDPOINT) or Cloud Mailbox (AGENTVERSE_MAILBOX=true)

Usage:
    python -m agent.register
"""
import asyncio
import logging
import sys
from typing import Any, Dict, Optional

from uagents.agent import parse_agentverse_config, register_in_agentverse
from uagents.crypto import Identity
from uagents.mailbox import AgentverseConnectRequest
from uagents_core.registration import AgentProfile, RegistrationRequest

from agent.agent import create_verifibrand_agent
from agent.config import AgentConfig, get_agent_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agent.register")


async def register_agent_with_agentverse(
    config: Optional[AgentConfig] = None,
) -> Dict[str, Any]:
    """Execute official Agentverse registration workflow using cryptographic challenge response.

    Safe to run repeatedly (idempotent). Fails safely if credentials are unset.
    """
    cfg = config or get_agent_config()
    safe_summary = cfg.get_safe_summary()

    logger.info("VerifiBrand Agentverse Registration Readiness Check:")
    logger.info("Configuration (Safe): %s", safe_summary)

    # 1. Derive agent identity
    agent = create_verifibrand_agent(cfg)
    identity = agent._identity

    logger.info("Agent Name:       %s", cfg.AGENT_NAME)
    logger.info("Agent Handle:     %s", cfg.AGENT_HANDLE)
    logger.info("Agent Address:    %s", agent.address)
    logger.info("Agent Identifier: %s", agent.identifier)
    logger.info("Protocols:        %s", [p.name for p in agent.protocols.values()])

    # 2. Verify Agentverse API Key is present
    if not cfg.AGENTVERSE_API_KEY or not cfg.AGENTVERSE_API_KEY.strip():
        message = (
            "Agentverse API Key is not configured (AGENTVERSE_API_KEY is empty). "
            "To complete live registration on Agentverse:\n"
            "  1. Sign in to https://agentverse.ai\n"
            "  2. Go to Profile -> API Keys -> Create API Key\n"
            "  3. Configure AGENTVERSE_API_KEY=<your_key> in agent/.env or environment\n"
            "  4. Set AGENTVERSE_MAILBOX=true (or provide public AGENT_ENDPOINT)\n"
            "  5. Re-run: python -m agent.register"
        )
        logger.warning(message)
        return {
            "registered": False,
            "agent_address": agent.address,
            "agent_name": cfg.AGENT_NAME,
            "detail": "PREREQUISITES_MISSING",
            "message": message,
        }

    # 3. Build Agentverse Connection Request
    agentverse_config = parse_agentverse_config(cfg.AGENTVERSE_API_KEY + "@agentverse.ai")

    endpoint_val = cfg.AGENT_ENDPOINT or f"http://127.0.0.1:{cfg.AGENT_PORT}/submit"
    agent_type = "mailbox" if cfg.AGENTVERSE_MAILBOX else "custom"

    connect_req = AgentverseConnectRequest(
        user_token=cfg.AGENTVERSE_API_KEY,
        agent_type=agent_type,
        endpoint=endpoint_val,
        team=None,
    )

    profile = AgentProfile(
        description=cfg.AGENT_DESCRIPTION,
        readme="",
        avatar_url="",
        banner_url="",
        starter_prompts=[
            "Check compliance: title='Promo' text='Our new eco-friendly collection.'",
            "Why was event evt_blocked_12345 blocked?",
            "Verify passport 3fa85f64-5717-4562-b3fc-2c963f66afa6",
        ],
    )

    registration_data = RegistrationRequest(
        address=agent.address,
        name=agent.name,
        handle=cfg.AGENT_HANDLE,
        url=endpoint_val,
        profile=profile,
        endpoints=agent._endpoints,
        protocols=list(agent.protocols.keys()),
        metadata={
            "description": cfg.AGENT_DESCRIPTION,
            "tags": cfg.AGENT_TAGS,
            "handle": cfg.AGENT_HANDLE,
        },
    )

    # 4. Perform Challenge-Response Registration
    logger.info("Connecting to Agentverse identity challenge endpoint...")
    try:
        response = await register_in_agentverse(
            request=connect_req,
            identity=identity,
            prefix=agent._prefix,
            agentverse=agentverse_config,
            agent_details=registration_data,
        )
    except Exception as exc:
        logger.error("Agentverse registration network exception: %s", exc)
        return {
            "registered": False,
            "agent_address": agent.address,
            "detail": f"NETWORK_ERROR: {str(exc)}",
            "message": "Registration attempt encountered a network exception.",
        }

    if response.success:
        logger.info("Successfully registered VerifiBrand Agent on Agentverse!")
        return {
            "registered": True,
            "agent_address": agent.address,
            "agent_name": cfg.AGENT_NAME,
            "agent_type": agent_type,
            "detail": "SUCCESS",
            "message": f"Agent registered as {agent_type} on Agentverse.",
        }
    else:
        logger.warning("Agentverse registration failed: %s", response.detail)
        return {
            "registered": False,
            "agent_address": agent.address,
            "agent_name": cfg.AGENT_NAME,
            "detail": response.detail,
            "message": f"Agentverse returned error: {response.detail}",
        }


def main() -> None:
    """CLI entrypoint for Agentverse registration."""
    result = asyncio.run(register_agent_with_agentverse())
    print("=" * 60)
    print("Agentverse Registration Result:")
    for k, v in result.items():
        if k != "message":
            print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
