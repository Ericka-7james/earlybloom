"""
Central application settings for EarlyBloom.

This config keeps environment-driven settings in one place and provides a
cached settings object for the rest of the application.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.ENV: str = os.getenv("ENV", "development").strip().lower()

        # ========================
        # Supabase settings
        # ========================
        self.SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
        self.SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "").strip()
        self.SUPABASE_PUBLISHABLE_KEY: str = os.getenv(
            "SUPABASE_PUBLISHABLE_KEY", ""
        ).strip()

        # ========================
        # Job data mode
        # ========================
        self.JOB_DATA_MODE: str = os.getenv("JOB_DATA_MODE", "live").strip().lower()
        if self.JOB_DATA_MODE not in {"live", "mock"}:
            raise ValueError("JOB_DATA_MODE must be 'live' or 'mock'")

        # ========================
        # Provider toggles
        # ========================
        self.JOB_PROVIDER_ARBEITNOW_ENABLED: bool = _get_bool(
            "JOB_PROVIDER_ARBEITNOW_ENABLED", True
        )
        self.JOB_PROVIDER_REMOTEOK_ENABLED: bool = _get_bool(
            "JOB_PROVIDER_REMOTEOK_ENABLED", True
        )
        self.JOB_PROVIDER_JOBICY_ENABLED: bool = _get_bool(
            "JOB_PROVIDER_JOBICY_ENABLED", True
        )
        self.JOB_PROVIDER_USAJOBS_ENABLED: bool = _get_bool(
            "JOB_PROVIDER_USAJOBS_ENABLED", False
        )
        self.JOB_PROVIDER_GREENHOUSE_ENABLED: bool = _get_bool(
            "JOB_PROVIDER_GREENHOUSE_ENABLED", False
        )
        self.JOB_PROVIDER_JSEARCH_ENABLED: bool = _get_bool(
            "JOB_PROVIDER_JSEARCH_ENABLED", False
        )
        self.JOB_PROVIDER_SERPAPI_ENABLED: bool = _get_bool(
            "JOB_PROVIDER_SERPAPI_ENABLED", False
        )

        # ========================
        # Shared provider settings
        # ========================
        self.JOB_PROVIDER_TIMEOUT_SECONDS: float = max(
            0.5, _get_float("JOB_PROVIDER_TIMEOUT_SECONDS", 3.0)
        )
        self.JOB_PROVIDER_MAX_JOBS_PER_SOURCE: int = max(
            1, _get_int("JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)
        )
        self.JOB_CACHE_TTL_SECONDS: int = max(
            1, _get_int("JOB_CACHE_TTL_SECONDS", 180)
        )
        self.JOB_CACHE_MAX_ENTRIES: int = max(
            10, _get_int("JOB_CACHE_MAX_ENTRIES", 64)
        )

        # ========================
        # Lightweight provider pagination controls
        # ========================
        self.JOB_PROVIDER_ARBEITNOW_PAGES: int = min(
            max(1, _get_int("JOB_PROVIDER_ARBEITNOW_PAGES", 2)),
            5,
        )
        self.JOB_PROVIDER_JOBICY_PAGES: int = min(
            max(1, _get_int("JOB_PROVIDER_JOBICY_PAGES", 2)),
            5,
        )
        self.JOB_PROVIDER_SERPAPI_MAX_JOBS: int = max(
            1, _get_int("JOB_PROVIDER_SERPAPI_MAX_JOBS", 50)
        )

        # ========================
        # Shared cache / ingestion control
        # ========================
        self.JOBS_DB_ONLY_READS: bool = _get_bool("JOBS_DB_ONLY_READS", False)
        self.JOBS_SHARED_CACHE_MIN_RESULTS: int = max(
            1, _get_int("JOBS_SHARED_CACHE_MIN_RESULTS", 20)
        )
        self.JOBS_MIN_IMMEDIATE_RESULTS: int = max(
            1, _get_int("JOBS_MIN_IMMEDIATE_RESULTS", 20)
        )
        self.JOBS_SHARED_CACHE_TTL_DAYS: int = max(
            1, _get_int("JOBS_SHARED_CACHE_TTL_DAYS", 14)
        )
        self.JOBS_QUERY_CACHE_TTL_SECONDS: int = max(
            1, _get_int("JOBS_QUERY_CACHE_TTL_SECONDS", 300)
        )
        self.JOBS_PROVIDER_REFRESH_COOLDOWN_SECONDS: int = max(
            1, _get_int("JOBS_PROVIDER_REFRESH_COOLDOWN_SECONDS", 900)
        )
        self.JOBS_INGESTION_RUNNING_TTL_SECONDS: int = max(
            1, _get_int("JOBS_INGESTION_RUNNING_TTL_SECONDS", 300)
        )
        self.JOBS_MAX_DB_SCAN_ROWS: int = max(
            1, _get_int("JOBS_MAX_DB_SCAN_ROWS", 400)
        )
        self.JOBS_PROVIDER_MAX_CONCURRENCY: int = max(
            1, _get_int("JOBS_PROVIDER_MAX_CONCURRENCY", 3)
        )
        self.JOBS_MAX_RESPONSE_JOBS: int = max(
            1, _get_int("JOBS_MAX_RESPONSE_JOBS", 160)
        )
        self.JOBS_MAX_LIVE_AGGREGATE_JOBS: int = max(
            1, _get_int("JOBS_MAX_LIVE_AGGREGATE_JOBS", 300)
        )
        self.JOBS_CACHE_CLEANUP_INTERVAL_SECONDS: int = max(
            30, _get_int("JOBS_CACHE_CLEANUP_INTERVAL_SECONDS", 900)
        )

        # ========================
        # Greenhouse settings
        # ========================
        self.JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS: str = os.getenv(
            "JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", ""
        ).strip()
        self.JOB_PROVIDER_GREENHOUSE_INCLUDE_DEPARTMENTS: str = os.getenv(
            "JOB_PROVIDER_GREENHOUSE_INCLUDE_DEPARTMENTS", ""
        ).strip()
        self.JOB_PROVIDER_GREENHOUSE_EXCLUDE_DEPARTMENTS: str = os.getenv(
            "JOB_PROVIDER_GREENHOUSE_EXCLUDE_DEPARTMENTS", ""
        ).strip()
        self.JOB_PROVIDER_GREENHOUSE_INCLUDE_OFFICES: str = os.getenv(
            "JOB_PROVIDER_GREENHOUSE_INCLUDE_OFFICES", ""
        ).strip()
        self.JOB_PROVIDER_GREENHOUSE_EXCLUDE_OFFICES: str = os.getenv(
            "JOB_PROVIDER_GREENHOUSE_EXCLUDE_OFFICES", ""
        ).strip()

        # ========================
        # API pagination defaults
        # ========================
        self.JOBS_DEFAULT_PAGE_SIZE: int = min(
            max(1, _get_int("JOBS_DEFAULT_PAGE_SIZE", 30)),
            100,
        )
        self.JOBS_MAX_PAGE_SIZE: int = min(
            max(1, _get_int("JOBS_MAX_PAGE_SIZE", 100)),
            200,
        )

        # ========================
        # USAJOBS settings
        # ========================
        self.USAJOBS_API_KEY: str = os.getenv("USAJOBS_API_KEY", "").strip()
        self.USAJOBS_USER_AGENT: str = os.getenv("USAJOBS_USER_AGENT", "").strip()
        self.USAJOBS_RESULTS_PER_PAGE: int = min(
            max(1, _get_int("USAJOBS_RESULTS_PER_PAGE", 50)),
            500,
        )
        self.USAJOBS_POSITION_OFFER_TYPE_CODE: str = os.getenv(
            "USAJOBS_POSITION_OFFER_TYPE_CODE", ""
        ).strip()
        self.USAJOBS_JOB_CATEGORY_CODE: str = os.getenv(
            "USAJOBS_JOB_CATEGORY_CODE", "2210"
        ).strip()

        # ========================
        # Other provider keys
        # ========================
        self.JSEARCH_API_KEY: str = os.getenv("JSEARCH_API_KEY", "").strip()
        self.RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "").strip()
        self.SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "").strip()


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()