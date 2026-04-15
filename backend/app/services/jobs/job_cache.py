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


# OrderedDict lets us cheaply evict the oldest entry when the cache grows too large.
_CACHE: OrderedDict[str, CacheEntry[T]] = OrderedDict()


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
    ordered_providers = ",".join(
        sorted(str(name).strip().lower() for name in provider_names)
    )
    scope = "remote" if remote_only else "all"
    return f"jobs:v4:{scope}:providers:{ordered_providers}"


def get_cached_value(cache_key: str) -> T | None:
    """Return a cached value if the entry is still fresh.

    Accessing a live key also refreshes its recency so the cache behaves
    roughly like a lightweight LRU.

    Args:
        cache_key: Cache key to lookup.

    Returns:
        Cached value when present and unexpired, otherwise None.
    """
    settings = get_settings()
    entry = _CACHE.get(cache_key)

    if entry is None:
        return None

    now = time.time()
    if (now - entry.stored_at) > settings.JOB_CACHE_TTL_SECONDS:
        _CACHE.pop(cache_key, None)
        return None

    # Refresh recency for hot keys.
    _CACHE.move_to_end(cache_key)
    return entry.value


def set_cached_value(cache_key: str, value: T) -> None:
    """Store a value in the in-memory cache.

    Existing keys are replaced in place and become the most recently used.
    When capacity is exceeded, the oldest entry is evicted.

    Args:
        cache_key: Cache key to store.
        value: Value to cache.
    """
    settings = get_settings()
    now = time.time()

    _CACHE[cache_key] = CacheEntry(stored_at=now, value=value)
    _CACHE.move_to_end(cache_key)

    _prune_expired_entries(now=now)
    _enforce_capacity(max_entries=settings.JOB_CACHE_MAX_ENTRIES)


def clear_cache_key(cache_key: str) -> None:
    """Remove a single cache key if present.

    Args:
        cache_key: Cache key to remove.
    """
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
    """Remove expired entries opportunistically.

    This keeps the cache from accumulating dead entries indefinitely without
    requiring a background worker.
    """
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