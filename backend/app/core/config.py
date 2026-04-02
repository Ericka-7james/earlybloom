"""
Central application settings for EarlyBloom.

This config keeps environment-driven settings in one place and provides a
cached settings object for the rest of the application.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # -----------------------------
    # Supabase
    # -----------------------------
    SUPABASE_URL: str | None = None
    SUPABASE_SECRET_KEY: str | None = None
    SUPABASE_PUBLISHABLE_KEY: str | None = None

    # -----------------------------
    # App behavior
    # -----------------------------
    JOB_DATA_MODE: str = "mock"
    JOB_CACHE_TTL_SECONDS: int = 300

    # -----------------------------
    # Provider toggles
    # -----------------------------
    JOB_PROVIDER_TIMEOUT_SECONDS: float = 6.0
    JOB_PROVIDER_MAX_JOBS_PER_SOURCE: int = 100

    JOB_PROVIDER_USAJOBS_ENABLED: bool = True
    JOB_PROVIDER_REMOTIVE_ENABLED: bool = True
    JOB_PROVIDER_ARBEITNOW_ENABLED: bool = True
    JOB_PROVIDER_JSEARCH_ENABLED: bool = False
    JOB_PROVIDER_JOBICY_ENABLED: bool = False

    # -----------------------------
    # USAJOBS
    # -----------------------------
    USAJOBS_API_KEY: str | None = None
    USAJOBS_USER_AGENT: str | None = None
    USAJOBS_RESULTS_PER_PAGE: int = 50
    USAJOBS_JOB_CATEGORY_CODE: str | None = None
    USAJOBS_POSITION_OFFER_TYPE_CODE: str | None = None

    # -----------------------------
    # ArbeitNow
    # -----------------------------
    JOB_PROVIDER_ARBEITNOW_PAGES: int = 2
    JOB_PROVIDER_ARBEITNOW_REMOTE_ONLY: bool = False

    # -----------------------------
    # Remotive
    # -----------------------------
    JOB_PROVIDER_REMOTIVE_CATEGORY: str | None = None
    JOB_PROVIDER_REMOTIVE_SEARCH: str | None = None

    # -----------------------------
    # JSearch
    # -----------------------------
    JSEARCH_API_KEY: str | None = None
    JOB_PROVIDER_JSEARCH_QUERY: str = (
        "software engineer OR software developer OR IT support"
    )
    JOB_PROVIDER_JSEARCH_PAGE: int = 1
    JOB_PROVIDER_JSEARCH_NUM_PAGES: int = 1
    JOB_PROVIDER_JSEARCH_COUNTRY: str = "us"
    JOB_PROVIDER_JSEARCH_DATE_POSTED: str | None = None

    # -----------------------------
    # Jobicy
    # -----------------------------
    JOB_PROVIDER_JOBICY_PAGES: int = 1

    @field_validator("JOB_DATA_MODE")
    @classmethod
    def validate_job_data_mode(cls, value: str) -> str:
        """Normalize and validate the job data mode."""
        normalized = value.strip().lower()
        if normalized not in {"mock", "live"}:
            raise ValueError("JOB_DATA_MODE must be 'mock' or 'live'.")
        return normalized


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()