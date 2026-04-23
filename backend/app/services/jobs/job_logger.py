"""Structured logging helpers for jobs ingestion flows.

This module keeps repetitive logging code out of job_ingestion.py so the
ingestion service can focus on orchestration instead of message formatting.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_ingestion_start(
    *,
    remote_only: bool,
    levels: list[str] | None,
    role_types: list[str] | None,
    location_query: str | None,
    providers: list[str],
) -> None:
    """Log the start of an ingestion request."""
    logger.info(
        "jobs.ingestion.start remote_only=%s levels=%s role_types=%s location_query=%s providers=%s",
        remote_only,
        levels or [],
        role_types or [],
        (location_query or "").strip(),
        providers,
    )


def log_memory_cache_hit(*, count: int, cache_key: str) -> None:
    """Log a memory-cache hit."""
    logger.info(
        "jobs.cache.memory.hit count=%s cache_key=%s",
        count,
        cache_key,
    )


def log_query_cache_hit(*, count: int, query_key: str) -> None:
    """Log a query-cache hit."""
    logger.info(
        "jobs.cache.query.hit count=%s query_key=%s",
        count,
        query_key,
    )


def log_shared_cache_result(*, count: int, query_key: str) -> None:
    """Log the shared-db cache result."""
    logger.info(
        "jobs.cache.shared.result count=%s query_key=%s",
        count,
        query_key,
    )


def log_shared_cache_return(
    *,
    count: int,
    shared_cache_min_results: int,
    immediate_min_results: int,
) -> None:
    """Log that shared-cache jobs were returned immediately."""
    logger.info(
        "jobs.cache.shared.return count=%s shared_cache_min_results=%s immediate_min_results=%s",
        count,
        shared_cache_min_results,
        immediate_min_results,
    )


def log_live_refresh_start(*, cached_count: int, threshold: int) -> None:
    """Log that live refresh is starting."""
    logger.info(
        "jobs.refresh.live.start cached_count=%s threshold=%s",
        cached_count,
        threshold,
    )


def log_live_refresh_complete(
    *,
    aggregated_count: int,
    deduped_count: int,
    capped_count: int,
) -> None:
    """Log aggregate live-refresh completion."""
    logger.info(
        "jobs.refresh.live.complete aggregated=%s deduped=%s capped=%s",
        aggregated_count,
        deduped_count,
        capped_count,
    )


def log_final_return(*, count: int) -> None:
    """Log final response size."""
    logger.info("jobs.ingestion.return count=%s", count)


def log_provider_skipped_running(*, provider_name: str, query_key: str) -> None:
    """Log that a provider was skipped because a run is already active."""
    logger.info(
        "jobs.provider.skip.running provider=%s query_key=%s",
        provider_name,
        query_key,
    )


def log_provider_skipped_cooldown(*, provider_name: str, query_key: str) -> None:
    """Log that a provider was skipped because cooldown is active."""
    logger.info(
        "jobs.provider.skip.cooldown provider=%s query_key=%s",
        provider_name,
        query_key,
    )


def log_provider_complete(
    *,
    provider_name: str,
    raw_count: int,
    normalized_count: int,
    filtered_count: int,
    kept_count: int,
) -> None:
    """Log successful provider refresh results."""
    logger.info(
        "jobs.provider.complete provider=%s raw=%s normalized=%s filtered=%s kept=%s",
        provider_name,
        raw_count,
        normalized_count,
        filtered_count,
        kept_count,
    )


def log_provider_failure(*, provider_name: str, error: Exception) -> None:
    """Log provider failure with stack trace."""
    logger.exception(
        "jobs.provider.failed provider=%s error=%s",
        provider_name,
        error,
        exc_info=error,
    )


def log_non_list_provider_payload(*, provider_name: str, payload_type: str) -> None:
    """Log unexpected provider payload types."""
    logger.warning(
        "jobs.provider.invalid_payload provider=%s payload_type=%s",
        provider_name,
        payload_type,
    )


def log_query_cache_write(*, query_key: str, job_count: int) -> None:
    """Log successful query-cache write."""
    logger.info(
        "jobs.cache.query.write query_key=%s job_count=%s",
        query_key,
        job_count,
    )


def log_cleanup_complete(*, marked_inactive: Any, deleted: Any) -> None:
    """Log shared-cache cleanup completion."""
    logger.info(
        "jobs.cache.cleanup marked_inactive=%s deleted=%s",
        marked_inactive,
        deleted,
    )


def log_db_only_reads_return(*, count: int) -> None:
    """Log DB-only return behavior."""
    logger.info(
        "jobs.db_only_reads.return count=%s",
        count,
    )