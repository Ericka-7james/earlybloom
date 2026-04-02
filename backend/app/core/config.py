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
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ENV: str = "development"

    # Supabase settings
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""

    # Job data mode:
    # - live: fetch real providers first, fallback to mock only if needed
    # - mock: force mock data
    JOB_DATA_MODE: str = "live"

    # Provider toggles
    JOB_PROVIDER_ARBEITNOW_ENABLED: bool = True
    JOB_PROVIDER_REMOTEOK_ENABLED: bool = True
    JOB_PROVIDER_JOBICY_ENABLED: bool = True
    JOB_PROVIDER_USAJOBS_ENABLED: bool = False

    # Shared provider settings
    JOB_PROVIDER_TIMEOUT_SECONDS: float = 3.5
    JOB_PROVIDER_MAX_JOBS_PER_SOURCE: int = 100
    JOB_CACHE_TTL_SECONDS: int = 300

    # Lightweight provider pagination controls for serverless execution
    JOB_PROVIDER_ARBEITNOW_PAGES: int = 2
    JOB_PROVIDER_JOBICY_PAGES: int = 2

    # API pagination defaults
    JOBS_DEFAULT_PAGE_SIZE: int = 30
    JOBS_MAX_PAGE_SIZE: int = 100

    # USAJOBS settings
    USAJOBS_API_KEY: str = ""
    USAJOBS_USER_AGENT: str = ""
    USAJOBS_RESULTS_PER_PAGE: int = 50
    USAJOBS_POSITION_OFFER_TYPE_CODE: str = ""
    USAJOBS_JOB_CATEGORY_CODE: str = "2210"

    @field_validator("JOB_DATA_MODE")
    @classmethod
    def validate_job_data_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"live", "mock"}:
            raise ValueError("JOB_DATA_MODE must be 'live' or 'mock'")
        return normalized

    @field_validator("USAJOBS_RESULTS_PER_PAGE")
    @classmethod
    def validate_usajobs_results_per_page(cls, value: int) -> int:
        if value < 1:
            return 1
        if value > 500:
            return 500
        return value

    @field_validator("JOB_PROVIDER_ARBEITNOW_PAGES", "JOB_PROVIDER_JOBICY_PAGES")
    @classmethod
    def validate_small_page_counts(cls, value: int) -> int:
        if value < 1:
            return 1
        if value > 5:
            return 5
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()