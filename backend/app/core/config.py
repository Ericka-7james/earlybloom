"""
Central application settings for EarlyBloom job ingestion.

This config is designed for lightweight, serverless-friendly ingestion on Vercel.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings:
    # -----------------------------
    # Supabase
    # -----------------------------
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_SECRET_KEY: str | None = os.getenv("SUPABASE_SECRET_KEY")
    SUPABASE_PUBLISHABLE_KEY: str | None = os.getenv("SUPABASE_PUBLISHABLE_KEY")

    # -----------------------------
    # App behavior
    # -----------------------------
    JOB_DATA_MODE: str = os.getenv("JOB_DATA_MODE", "mock").strip().lower()


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()