"""Configuration for the VerifiBrand Fetch.ai Agent.

Reads environment settings with safe defaults and provides helper utilities
to mask sensitive secrets in logs and diagnostics. Enforces production security
policies preventing insecure development seeds or plaintext HTTP public endpoints.
"""
import os
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_SEED_DEFAULT = "verifibrand-agent-development-seed-do-not-use-in-prod"


class AgentConfig(BaseSettings):
    """VerifiBrand Fetch.ai Agent configuration model."""

    # Operational Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Operating environment: 'development', 'testing', or 'production'",
    )

    # Backend connection
    BACKEND_URL: str = Field(
        default="http://127.0.0.1:8000",
        description="Base URL for the BrandLedger FastAPI backend",
    )
    BACKEND_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="Timeout in seconds for backend HTTP calls",
    )

    # Fetch.ai agent identity and networking
    AGENT_NAME: str = Field(
        default="verifibrand_agent",
        description="Fetch.ai agent display name",
    )
    AGENT_PORT: int = Field(
        default=8001,
        description="Local HTTP communication port for the agent",
    )
    AGENT_SEED: str = Field(
        default=DEVELOPMENT_SEED_DEFAULT,
        description="Seed phrase for deterministic Fetch.ai agent address and wallet generation",
    )
    AGENT_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Public HTTPS endpoint URL where the agent can receive incoming webhooks",
    )

    # Agentverse & Discovery Configuration
    AGENTVERSE_API_KEY: Optional[str] = Field(
        default=None,
        description="Agentverse API token for cloud mailbox, directory, and registry services",
    )
    AGENTVERSE_MAILBOX: bool = Field(
        default=False,
        description="Enable Agentverse Cloud Mailbox for firewall-traversing communication",
    )
    AGENT_HANDLE: str = Field(
        default="verifibrand",
        description="Agentverse unique handle for human-readable discovery",
    )
    AGENT_DESCRIPTION: str = Field(
        default=(
            "VerifiBrand authoritative compliance, publication gate explanation, "
            "and cryptographic Content Passport verification agent for brand marketing assets."
        ),
        description="Public metadata description indexed by Agentverse and ASI:One",
    )
    AGENT_TAGS: List[str] = Field(
        default_factory=lambda: [
            "brand-safety",
            "compliance",
            "verification",
            "content-passport",
            "asi-one",
            "governance",
        ],
        description="Search keywords and discovery tags for Almanac and ASI:One routing",
    )

    # Logging and diagnostics
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "agent/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "AgentConfig":
        """Enforce strict security standards when running in production."""
        env_clean = self.ENVIRONMENT.strip().lower()
        if env_clean in ("production", "prod"):
            # 1. Insecure development seed detection
            seed_clean = self.AGENT_SEED.strip().lower()
            if (
                not seed_clean
                or seed_clean == DEVELOPMENT_SEED_DEFAULT
                or "dev" in seed_clean
                or "test" in seed_clean
            ):
                raise ValueError(
                    "Production security violation: Insecure development AGENT_SEED detected. "
                    "A unique, private 12/24-word mnemonic seed phrase is required in production."
                )

            # 2. Enforce HTTPS for public endpoint in production
            if self.AGENT_ENDPOINT:
                endpoint_clean = self.AGENT_ENDPOINT.strip().lower()
                if not endpoint_clean.startswith("https://"):
                    raise ValueError(
                        f"Production security violation: AGENT_ENDPOINT ('{self.AGENT_ENDPOINT}') "
                        "must use HTTPS for secure public communication."
                    )
        return self

    def masked_seed(self) -> str:
        """Return a safely redacted representation of the agent seed."""
        if not self.AGENT_SEED or len(self.AGENT_SEED) < 8:
            return "***"
        return f"{self.AGENT_SEED[:4]}***{self.AGENT_SEED[-4:]}"

    def masked_api_key(self) -> Optional[str]:
        """Return a safely redacted representation of the Agentverse API key."""
        if not self.AGENTVERSE_API_KEY:
            return None
        if len(self.AGENTVERSE_API_KEY) < 8:
            return "***"
        return f"{self.AGENTVERSE_API_KEY[:4]}***{self.AGENTVERSE_API_KEY[-4:]}"

    def get_safe_summary(self) -> Dict[str, Any]:
        """Return configuration dictionary with all secrets and seeds redacted."""
        return {
            "ENVIRONMENT": self.ENVIRONMENT,
            "BACKEND_URL": self.BACKEND_URL,
            "BACKEND_TIMEOUT_SECONDS": self.BACKEND_TIMEOUT_SECONDS,
            "AGENT_NAME": self.AGENT_NAME,
            "AGENT_PORT": self.AGENT_PORT,
            "AGENT_SEED": self.masked_seed(),
            "AGENT_ENDPOINT": self.AGENT_ENDPOINT,
            "AGENTVERSE_API_KEY": self.masked_api_key(),
            "AGENTVERSE_MAILBOX": self.AGENTVERSE_MAILBOX,
            "AGENT_HANDLE": self.AGENT_HANDLE,
            "AGENT_TAGS": self.AGENT_TAGS,
            "LOG_LEVEL": self.LOG_LEVEL,
        }


def get_agent_config() -> AgentConfig:
    """Factory function to instantiate agent settings."""
    return AgentConfig()
