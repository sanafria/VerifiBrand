"""Executable Entrypoint for the VerifiBrand Fetch.ai Agent.

Starts the agent event loop and listens for communication protocol messages on the
configured port (default: 8001).

Usage:
    python -m agent.main
    # or
    python agent/main.py
"""
import logging
import sys

from agent.agent import create_verifibrand_agent
from agent.config import get_agent_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agent.main")


def main() -> None:
    """Initialize configuration and launch the VerifiBrand Fetch.ai Agent."""
    config = get_agent_config()

    # Redact sensitive seeds and keys before logging
    safe_config = config.get_safe_summary()
    logger.info("Initializing VerifiBrand Fetch.ai Agent...")
    logger.info("Agent Configuration: %s", safe_config)

    agent = create_verifibrand_agent(config=config)

    logger.info("=" * 60)
    logger.info("VerifiBrand Fetch.ai Agent Core initialized.")
    logger.info("Agent Name:       %s", agent.name)
    logger.info("Agent Address:    %s", agent.address)
    logger.info("Agent Identifier: %s", agent.identifier)
    logger.info("Listening Port:   %d", config.AGENT_PORT)
    logger.info("Backend Target:   %s", config.BACKEND_URL)
    logger.info("Protocols:        %s", [p.name for p in agent.protocols.values()])
    logger.info("ASI:One Enabled:  AgentChatProtocol (ACP 0.3.0) Active")
    logger.info("Mailbox Mode:     %s", "ENABLED" if agent._use_mailbox else "DISABLED (Direct/Local)")
    logger.info("=" * 60)
    logger.info("Starting agent event loop...")

    # Run the uAgents agent loop
    agent.run()


if __name__ == "__main__":
    main()
