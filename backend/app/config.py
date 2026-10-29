"""Application Configuration Module for BrandLedger.

Loads settings from environment variables or .env file with safe defaults.
"""
from typing import List, Union
from pydantic import field_validator
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

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
