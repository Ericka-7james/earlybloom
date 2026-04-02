"""Lightweight in-memory cache helpers for job ingestion."""

from __future__ import annotations

import time
from typing import TypeVar

from app.core.config import get_settings

T = TypeVar("T")

_CACHE: dict[str, tuple[float, T]] = {}


def build_jobs_cache_key(
    *,
    remote_only: bool,
    provider_names: list[str] | tuple[str, ...] | set[str],
) -> str:
    """Build a deterministic cache key for a job-ingestion request.

    Args:
        remote_only: Whether only remote jobs are requested.
        provider_names: Enabled provider names for this request.

    Returns:
        A deterministic cache key string.
    """
    ordered_providers = ",".join(sorted(str(name).strip().lower() for name in provider_names))
    scope = "remote" if remote_only else "all"
    return f"jobs:v3:{scope}:providers:{ordered_providers}"


def get_cached_value(cache_key: str) -> T | None:
    """Return a cached value if the entry is still fresh.

    Args:
        cache_key: Cache key to lookup.

    Returns:
        Cached value when present and unexpired, otherwise None.
    """
    settings = get_settings()
    entry = _CACHE.get(cache_key)

    if entry is None:
        return None

    stored_at, value = entry
    if (time.time() - stored_at) > settings.JOB_CACHE_TTL_SECONDS:
        _CACHE.pop(cache_key, None)
        return None

    return value


def set_cached_value(cache_key: str, value: T) -> None:
    """Store a value in the in-memory cache.

    Args:
        cache_key: Cache key to store.
        value: Value to cache.
    """
    _CACHE[cache_key] = (time.time(), value)


def clear_cache_key(cache_key: str) -> None:
    """Remove a single cache key if present.

    Args:
        cache_key: Cache key to remove.
    """
    _CACHE.pop(cache_key, None)


def clear_all_cache() -> None:
    """Clear all cached entries."""
    _CACHE.clear()