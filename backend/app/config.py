"""Application Configuration Module for BrandLedger.

Loads settings from environment variables or .env file with safe defaults.
"""
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """BrandLedger Backend Settings."""

    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS origins
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Supabase / DB Configuration (Placeholders for Phase 1)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = "postgresql://brandledger_user:brandledger_secret@localhost:5433/brandledger"

    # Optional AI Key (Zynab's engine integration)
    OPENAI_API_KEY: str = ""

    # Agent Authentication Key (Member 2 agent tools security)
    AGENT_API_KEY: str = ""

    # Publication Gate & CMS Webhook HMAC-SHA256 Secret (Member 6)
    CMS_WEBHOOK_SECRET: str = "brandledger_cms_default_secret_dev"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Enforce strict security standards when running in production."""
        env_clean = self.ENVIRONMENT.strip().lower()
        if env_clean in ("production", "prod"):
            # 1. Enforce strong, non-development CMS Webhook Secret
            secret_clean = self.CMS_WEBHOOK_SECRET.strip()
            if (
                not secret_clean
                or secret_clean == "brandledger_cms_default_secret_dev"
                or "dev" in secret_clean.lower()
                or "default" in secret_clean.lower()
                or len(secret_clean) < 16
            ):
                raise ValueError(
                    "Production security violation: Insecure development CMS_WEBHOOK_SECRET detected. "
                    "A strong secret of at least 16 characters is required in production."
                )

            # 2. Refuse default development database password in production
            if "brandledger_secret" in self.DATABASE_URL:
                raise ValueError(
                    "Production security violation: Default development database credentials detected in DATABASE_URL. "
                    "Production requires secure, private database credentials."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
