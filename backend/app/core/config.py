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

    # ========================
    # Supabase settings
    # ========================
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""

    # ========================
    # Job data mode
    # - live: allow guarded provider refreshes when shared cache is stale/empty
    # - mock: force mock data
    # ========================
    JOB_DATA_MODE: str = "live"

    # ========================
    # Provider toggles
    # ========================
    JOB_PROVIDER_ARBEITNOW_ENABLED: bool = True
    JOB_PROVIDER_REMOTEOK_ENABLED: bool = True
    JOB_PROVIDER_JOBICY_ENABLED: bool = True
    JOB_PROVIDER_USAJOBS_ENABLED: bool = False
    JOB_PROVIDER_GREENHOUSE_ENABLED: bool = False

    # ========================
    # Shared provider settings
    # ========================
    JOB_PROVIDER_TIMEOUT_SECONDS: float = 3.5
    JOB_PROVIDER_MAX_JOBS_PER_SOURCE: int = 100
    JOB_CACHE_TTL_SECONDS: int = 300

    # Lightweight provider pagination controls for serverless execution
    JOB_PROVIDER_ARBEITNOW_PAGES: int = 2
    JOB_PROVIDER_JOBICY_PAGES: int = 2

    # ========================
    # Shared cache / ingestion control
    # ========================
    JOBS_DB_ONLY_READS: bool = False
    JOBS_SHARED_CACHE_MIN_RESULTS: int = 20
    JOBS_SHARED_CACHE_TTL_DAYS: int = 14
    JOBS_QUERY_CACHE_TTL_SECONDS: int = 300
    JOBS_PROVIDER_REFRESH_COOLDOWN_SECONDS: int = 900
    JOBS_INGESTION_RUNNING_TTL_SECONDS: int = 300
    JOBS_MAX_DB_SCAN_ROWS: int = 500

    # ========================
    # Greenhouse settings
    # ========================
    JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS: str = ""
    JOB_PROVIDER_GREENHOUSE_INCLUDE_DEPARTMENTS: str = ""
    JOB_PROVIDER_GREENHOUSE_EXCLUDE_DEPARTMENTS: str = ""
    JOB_PROVIDER_GREENHOUSE_INCLUDE_OFFICES: str = ""
    JOB_PROVIDER_GREENHOUSE_EXCLUDE_OFFICES: str = ""

    # ========================
    # API pagination defaults
    # ========================
    JOBS_DEFAULT_PAGE_SIZE: int = 30
    JOBS_MAX_PAGE_SIZE: int = 100

    # ========================
    # USAJOBS settings
    # ========================
    USAJOBS_API_KEY: str = ""
    USAJOBS_USER_AGENT: str = ""
    USAJOBS_RESULTS_PER_PAGE: int = 50
    USAJOBS_POSITION_OFFER_TYPE_CODE: str = ""
    USAJOBS_JOB_CATEGORY_CODE: str = "2210"

    # ========================
    # Validators
    # ========================
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

    @field_validator(
        "JOB_PROVIDER_ARBEITNOW_PAGES",
        "JOB_PROVIDER_JOBICY_PAGES",
    )
    @classmethod
    def validate_small_page_counts(cls, value: int) -> int:
        if value < 1:
            return 1
        if value > 5:
            return 5
        return value

    @field_validator(
        "JOBS_SHARED_CACHE_MIN_RESULTS",
        "JOBS_SHARED_CACHE_TTL_DAYS",
        "JOBS_QUERY_CACHE_TTL_SECONDS",
        "JOBS_PROVIDER_REFRESH_COOLDOWN_SECONDS",
        "JOBS_INGESTION_RUNNING_TTL_SECONDS",
        "JOBS_MAX_DB_SCAN_ROWS",
        "JOBS_DEFAULT_PAGE_SIZE",
        "JOBS_MAX_PAGE_SIZE",
    )
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        return max(1, value)

    @field_validator("JOB_PROVIDER_TIMEOUT_SECONDS")
    @classmethod
    def validate_timeout_seconds(cls, value: float) -> float:
        return max(0.5, float(value))

    @field_validator("JOBS_MAX_PAGE_SIZE")
    @classmethod
    def validate_jobs_max_page_size(cls, value: int) -> int:
        return min(max(1, value), 200)

    @field_validator("JOBS_DEFAULT_PAGE_SIZE")
    @classmethod
    def validate_jobs_default_page_size(cls, value: int) -> int:
        return min(max(1, value), 100)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()