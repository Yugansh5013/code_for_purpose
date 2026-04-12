"""
OmniData — Application Settings

Pydantic Settings model that loads all configuration from .env file.
Validates required values at startup — fail fast if anything is missing.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Groq API Keys (rotated per-request) ───────────────
    groq_api_key_1: str = ""
    groq_api_key_2: str = ""
    groq_api_key_3: str = ""

    # ── Pinecone ──────────────────────────────────────────
    pinecone_api_key: str
    pinecone_hybrid_index: str = "omnidata-hybrid"
    pinecone_dense_index: str = "omnidata-dense"

    # ── Snowflake ─────────────────────────────────────────
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_database: str = "OMNIDATA_DB"

    # ── E2B ───────────────────────────────────────────────
    e2b_api_key: str = ""

    # ── Tavily (Phase 3) ─────────────────────────────────
    tavily_api_key: str = ""

    # ── Salesforce (Phase 2) ──────────────────────────────
    salesforce_username: str = ""
    salesforce_password: str = ""
    salesforce_security_token: str = ""
    salesforce_instance_url: str = ""
    salesforce_consumer_key: str = ""
    salesforce_consumer_secret: str = ""

    # ── Confluence (Phase 2) ──────────────────────────────
    confluence_base_url: str = ""
    confluence_api_token: str = ""
    confluence_user_email: str = ""
    confluence_default_space: str = "AURA"

    # ── App ───────────────────────────────────────────────
    backend_url: str = "http://localhost:8000"
    next_public_api_url: str = "http://localhost:8000"

    @property
    def groq_keys(self) -> list[str]:
        """Return list of non-empty Groq API keys for rotation."""
        keys = [self.groq_api_key_1, self.groq_api_key_2, self.groq_api_key_3]
        return [k for k in keys if k]

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — loaded once at startup."""
    return Settings()
