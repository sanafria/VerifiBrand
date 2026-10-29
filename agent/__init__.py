"""VerifiBrand Fetch.ai Agent Package."""

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
from agent.agent import create_verifibrand_agent, create_verifibrand_protocol
from agent.chat import create_agent_chat_protocol, process_chat_query
from agent.register import register_agent_with_agentverse

__all__ = [
    "AgentConfig",
    "get_agent_config",
    "ComplianceCheckRequest",
    "ComplianceCheckResponse",
    "ExplainBlockRequest",
    "ExplainBlockResponse",
    "VerifyPassportRequest",
    "VerifyPassportResponse",
    "VerifiBrandAgentService",
    "create_verifibrand_agent",
    "create_verifibrand_protocol",
    "create_agent_chat_protocol",
    "process_chat_query",
    "register_agent_with_agentverse",
]
