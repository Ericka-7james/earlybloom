"""Lightweight in-memory cache helpers for job ingestion.

Latency goals:
- keep hot jobs requests in-process when possible
- enforce TTL expiration without requiring every caller to manage cleanup
- bound memory growth with simple LRU-style eviction
- keep cache operations cheap and predictable
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.config import get_settings

T = TypeVar("T")


@dataclass(slots=True)
class CacheEntry(Generic[T]):
    """Represents a single in-memory cache entry."""

    stored_at: float
    value: T


_CACHE: OrderedDict[str, CacheEntry[T]] = OrderedDict()


def _normalize_text(value: object) -> str:
    """Normalize arbitrary values for deterministic cache-key use."""
    return " ".join(str(value or "").strip().lower().split())


def _normalize_list(values: list[str] | tuple[str, ...] | set[str] | None) -> str:
    """Normalize a collection into a stable comma-separated string."""
    if not values:
        return ""
    normalized = sorted(
        {
            _normalize_text(value)
            for value in values
            if _normalize_text(value)
        }
    )
    return ",".join(normalized)


def build_jobs_cache_key(
    *,
    remote_only: bool,
    provider_names: list[str] | tuple[str, ...] | set[str],
    levels: list[str] | tuple[str, ...] | set[str] | None = None,
    role_types: list[str] | tuple[str, ...] | set[str] | None = None,
    location_query: str | None = None,
) -> str:
    """Build a deterministic cache key for a job-ingestion request."""
    ordered_providers = _normalize_list(provider_names)
    ordered_levels = _normalize_list(levels)
    ordered_role_types = _normalize_list(role_types)
    normalized_location = _normalize_text(location_query)
    scope = "remote" if remote_only else "all"

    return (
        "jobs:v5:"
        f"scope:{scope}:"
        f"providers:{ordered_providers}:"
        f"levels:{ordered_levels or 'none'}:"
        f"roles:{ordered_role_types or 'none'}:"
        f"location:{normalized_location or 'none'}"
    )


def get_cached_value(cache_key: str) -> T | None:
    """Return a cached value if the entry is still fresh."""
    settings = get_settings()
    entry = _CACHE.get(cache_key)

    if entry is None:
        return None

    now = time.time()
    if (now - entry.stored_at) > settings.JOB_CACHE_TTL_SECONDS:
        _CACHE.pop(cache_key, None)
        return None

    _CACHE.move_to_end(cache_key)
    return entry.value


def set_cached_value(cache_key: str, value: T) -> None:
    """Store a value in the in-memory cache."""
    settings = get_settings()
    now = time.time()

    _CACHE[cache_key] = CacheEntry(stored_at=now, value=value)
    _CACHE.move_to_end(cache_key)

    _prune_expired_entries(now=now)
    _enforce_capacity(max_entries=settings.JOB_CACHE_MAX_ENTRIES)


def clear_cache_key(cache_key: str) -> None:
    """Remove a single cache key if present."""
    _CACHE.pop(cache_key, None)


def clear_all_cache() -> None:
    """Clear all cached entries."""
    _CACHE.clear()


def get_cache_stats() -> dict[str, int]:
    """Return lightweight cache stats for debugging and observability."""
    now = time.time()
    ttl_seconds = get_settings().JOB_CACHE_TTL_SECONDS

    live_entries = 0
    expired_entries = 0

    for entry in _CACHE.values():
        if (now - entry.stored_at) > ttl_seconds:
            expired_entries += 1
        else:
            live_entries += 1

    return {
        "total_entries": len(_CACHE),
        "live_entries": live_entries,
        "expired_entries": expired_entries,
    }


def _prune_expired_entries(*, now: float | None = None) -> None:
    """Remove expired entries opportunistically."""
    current_time = now if now is not None else time.time()
    ttl_seconds = get_settings().JOB_CACHE_TTL_SECONDS

    expired_keys = [
        cache_key
        for cache_key, entry in _CACHE.items()
        if (current_time - entry.stored_at) > ttl_seconds
    ]

    for cache_key in expired_keys:
        _CACHE.pop(cache_key, None)


def _enforce_capacity(*, max_entries: int) -> None:
    """Evict the oldest entries until the cache is within capacity."""
    safe_max_entries = max(1, int(max_entries))

    while len(_CACHE) > safe_max_entries:
        _CACHE.popitem(last=False)