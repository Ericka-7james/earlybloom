# backend/app/services/jobs/job_ingestion.py
"""Job ingestion service for EarlyBloom.

This module orchestrates provider ingestion for the jobs API.

Latency-oriented strategy:
- Prefer fast in-process memory cache first
- Prefer cached query/shared jobs before live refresh
- Do not run shared-cache cleanup on every request
- Return decent shared results immediately when available
- Refresh live providers in parallel with bounded concurrency
- Cap final response size to avoid overfilling payloads
- Treat Supabase as an accelerator, not the sole dependency
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.db.database import JobCacheRepository
from app.schemas.jobs import NormalizedJob
from app.services.jobs.job_cache import (
    build_jobs_cache_key,
    get_cached_value,
    set_cached_value,
)
from app.services.jobs.job_dedupe import dedupe_jobs
from app.services.jobs.job_filters import (
    build_filter_options,
    should_include_job,
    should_match_location_query,
)
from app.services.jobs.normalizer import normalize_provider_job
from app.services.jobs.providers import get_configured_providers
from app.services.jobs.us_filters import should_keep_us_focused_job
from app.services.jobs.common.skill_extractor import attach_normalized_skills

logger = logging.getLogger(__name__)

_LAST_SHARED_CACHE_CLEANUP_AT = 0.0


class JobIngestionService:
    """Service wrapper around the async ingestion flow."""

    def __init__(self, providers: dict[str, Any] | None = None) -> None:
        self.providers = providers or {}

    async def ingest_jobs(
        self,
        remote_only: bool = False,
        levels: list[str] | None = None,
        role_types: list[str] | None = None,
        location_query: str | None = None,
    ) -> list[dict[str, Any]]:
        return await get_jobs(
            remote_only=remote_only,
            levels=levels,
            role_types=role_types,
            location_query=location_query,
            providers=self.providers or None,
        )


async def get_jobs(
    remote_only: bool = False,
    levels: list[str] | None = None,
    role_types: list[str] | None = None,
    location_query: str | None = None,
    providers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Public entry point for jobs ingestion."""
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        logger.warning("JOB_DATA_MODE=mock. Returning mock jobs.")
        return _get_mock_jobs()

    provider_registry = providers or get_configured_providers()
    repository = JobCacheRepository()

    logger.warning(
        "get_jobs called remote_only=%s levels=%s role_types=%s location_query=%s providers=%s",
        remote_only,
        levels,
        role_types,
        location_query,
        list(provider_registry.keys()),
    )

    use_memory_cache = providers is None
    memory_cache_key: str | None = None

    if use_memory_cache:
        memory_cache_key = build_jobs_cache_key(
            remote_only=remote_only,
            provider_names=list(provider_registry.keys()),
        )
        if location_query:
            memory_cache_key = f"{memory_cache_key}:location:{_normalize_text(location_query)}"

        cached_memory_jobs = get_cached_value(memory_cache_key)
        if cached_memory_jobs is not None:
            logger.warning(
                "Returning jobs from memory cache. count=%s",
                len(cached_memory_jobs),
            )
            return _cap_jobs_for_response(cached_memory_jobs)

    query_key = repository.build_query_cache_key(
        remote_only=remote_only,
        levels=levels,
        role_types=role_types,
        location_query=location_query,
    )

    cached_query_jobs = _get_cached_jobs_from_query_cache(
        repository=repository,
        query_key=query_key,
    )
    if cached_query_jobs:
        logger.warning(
            "Returning jobs from query cache. count=%s query_key=%s",
            len(cached_query_jobs),
            query_key,
        )
        capped_query_jobs = _cap_jobs_for_response(cached_query_jobs)
        if use_memory_cache and memory_cache_key is not None:
            set_cached_value(memory_cache_key, capped_query_jobs)
        return capped_query_jobs

    shared_jobs = _get_cached_jobs_from_db(
        repository=repository,
        remote_only=remote_only,
        levels=levels,
        role_types=role_types,
        location_query=location_query,
        limit=settings.JOBS_MAX_DB_SCAN_ROWS,
    )

    logger.warning(
        "Shared cache returned count=%s query_key=%s",
        len(shared_jobs),
        query_key,
    )

    if shared_jobs:
        capped_shared_jobs = _cap_jobs_for_response(shared_jobs)

        _write_query_cache(
            repository=repository,
            query_key=query_key,
            jobs=capped_shared_jobs,
            remote_only=remote_only,
            levels=levels,
            role_types=role_types,
            location_query=location_query,
        )

        if _should_return_shared_jobs_immediately(shared_jobs):
            logger.warning(
                "Returning jobs from shared DB cache immediately. count=%s threshold=%s immediate_min=%s",
                len(shared_jobs),
                settings.JOBS_SHARED_CACHE_MIN_RESULTS,
                settings.JOBS_MIN_IMMEDIATE_RESULTS,
            )
            if use_memory_cache and memory_cache_key is not None:
                set_cached_value(memory_cache_key, capped_shared_jobs)
            return capped_shared_jobs

    if settings.JOBS_DB_ONLY_READS:
        logger.warning(
            "JOBS_DB_ONLY_READS enabled. Returning shared jobs without live refresh. count=%s",
            len(shared_jobs),
        )
        capped_shared_jobs = _cap_jobs_for_response(shared_jobs)
        if use_memory_cache and memory_cache_key is not None:
            set_cached_value(memory_cache_key, capped_shared_jobs)
        return capped_shared_jobs

    logger.warning(
        "Shared cache below threshold or empty. Triggering live refresh. cached_count=%s threshold=%s",
        len(shared_jobs),
        settings.JOBS_SHARED_CACHE_MIN_RESULTS,
    )

    live_normalized_jobs = await _refresh_jobs_from_providers_if_allowed(
        repository=repository,
        query_key=query_key,
        remote_only=remote_only,
        levels=levels,
        role_types=role_types,
        location_query=location_query,
        providers=provider_registry,
    )

    live_jobs = [map_normalized_job_to_response(job) for job in live_normalized_jobs]
    live_jobs = _cap_jobs_for_response(live_jobs)

    logger.warning(
        "Live provider refresh returned count=%s query_key=%s",
        len(live_jobs),
        query_key,
    )

    final_jobs = live_jobs or _cap_jobs_for_response(shared_jobs)

    if live_jobs:
        _write_query_cache(
            repository=repository,
            query_key=query_key,
            jobs=live_jobs,
            remote_only=remote_only,
            levels=levels,
            role_types=role_types,
            location_query=location_query,
        )

    if use_memory_cache and memory_cache_key is not None:
        set_cached_value(memory_cache_key, final_jobs)

    logger.warning("Returning final jobs count=%s", len(final_jobs))
    return final_jobs


def map_normalized_job_to_response(job: NormalizedJob) -> dict[str, Any]:
    """Map normalized data into the public jobs API response shape."""
    return {
        "id": job.id or _build_public_job_id(job),
        "title": job.title or "Unknown title",
        "company": job.company or "Unknown company",
        "location": job.location or "",
        "location_display": job.location_display or job.location or "",
        "remote": bool(job.remote),
        "remote_type": job.remote_type or "unknown",
        "url": str(job.url or ""),
        "source": job.source or "unknown",
        "source_job_id": job.source_job_id,
        "summary": job.summary or "",
        "description": job.description or "",
        "responsibilities": job.responsibilities or [],
        "qualifications": job.qualifications or [],
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "employment_type": job.employment_type,
        "experience_level": job.experience_level or "unknown",
        "role_type": job.role_type or "unknown",
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "stable_key": job.stable_key,
        "provider_payload_hash": job.provider_payload_hash,
        "skills": job.skills or [],
        "viewer_state": {
            "is_saved": False,
            "is_hidden": False,
            "saved_at": None,
            "hidden_at": None,
        },
    }


def _get_cached_jobs_from_query_cache(
    *,
    repository: JobCacheRepository,
    query_key: str,
) -> list[dict[str, Any]]:
    """Return cached query result if still valid."""
    try:
        row = repository.get_query_cache(cache_key=query_key)
    except Exception as exc:
        logger.exception(
            "Failed to read query cache. query_key=%s",
            query_key,
            exc_info=exc,
        )
        return []

    if not row:
        logger.warning("No valid query cache row found. query_key=%s", query_key)
        return []

    job_ids = row.get("job_ids") or []
    if not isinstance(job_ids, list) or not job_ids:
        logger.warning("Query cache row had no job_ids. query_key=%s", query_key)
        return []

    try:
        rows = repository.list_active_jobs_by_ids([str(job_id) for job_id in job_ids])
    except Exception as exc:
        logger.exception(
            "Failed to load active jobs by ids from query cache. query_key=%s",
            query_key,
            exc_info=exc,
        )
        return []

    jobs: list[NormalizedJob] = []
    for cache_row in rows:
        normalized = repository.row_to_normalized_job(cache_row)
        if normalized is not None:
            jobs.append(normalized)

    deduped_jobs = dedupe_jobs(jobs)

    logger.warning(
        "Loaded jobs from query cache. query_key=%s requested_ids=%s hydrated=%s deduped=%s",
        query_key,
        len(job_ids),
        len(jobs),
        len(deduped_jobs),
    )

    return [map_normalized_job_to_response(job) for job in deduped_jobs]


def _get_cached_jobs_from_db(
    *,
    repository: JobCacheRepository,
    remote_only: bool = False,
    levels: list[str] | None = None,
    role_types: list[str] | None = None,
    location_query: str | None = None,
    limit: int = 300,
) -> list[dict[str, Any]]:
    """Read jobs from Supabase cache and apply the same filtering pipeline."""
    try:
        _cleanup_shared_cache_if_due(repository)
        rows = repository.list_active_jobs(limit=limit)
    except Exception as exc:
        logger.exception("Failed to read jobs from Supabase cache.", exc_info=exc)
        return []

    if not rows:
        logger.warning("No active jobs found in Supabase cache after cleanup.")
        return []

    normalized_jobs: list[NormalizedJob] = []
    for row in rows:
        normalized = repository.row_to_normalized_job(row)
        if normalized is not None:
            normalized_jobs.append(normalized)

    filtered_jobs = _apply_job_filters(
        jobs=normalized_jobs,
        remote_only=remote_only,
        levels=levels,
        role_types=role_types,
        location_query=location_query,
    )

    deduped_jobs = dedupe_jobs(filtered_jobs)

    logger.warning(
        "Loaded jobs from Supabase cache. rows=%s normalized=%s filtered=%s deduped=%s",
        len(rows),
        len(normalized_jobs),
        len(filtered_jobs),
        len(deduped_jobs),
    )

    return [map_normalized_job_to_response(job) for job in deduped_jobs]


def _write_query_cache(
    *,
    repository: JobCacheRepository,
    query_key: str,
    jobs: list[dict[str, Any]],
    remote_only: bool,
    levels: list[str] | None,
    role_types: list[str] | None,
    location_query: str | None,
) -> None:
    """Persist filtered response ids for fast query replay."""
    try:
        job_ids = [
            str(job.get("id") or "").strip()
            for job in jobs
            if str(job.get("id") or "").strip()
        ]

        repository.upsert_query_cache(
            cache_key=query_key,
            query_params={
                "remote_only": remote_only,
                "levels": levels or [],
                "role_types": role_types or [],
                "location_query": (location_query or "").strip(),
            },
            job_ids=job_ids,
            viewer_scope="public",
            ttl_seconds=get_settings().JOBS_QUERY_CACHE_TTL_SECONDS,
        )

        logger.warning(
            "Upserted query cache. query_key=%s job_count=%s",
            query_key,
            len(job_ids),
        )
    except Exception as exc:
        logger.exception(
            "Failed to write query cache. query_key=%s",
            query_key,
            exc_info=exc,
        )


def _write_jobs_to_db_cache(
    *,
    repository: JobCacheRepository,
    jobs: list[NormalizedJob],
    ingestion_run_id: str | None = None,
) -> None:
    """Persist normalized jobs to Supabase shared cache."""
    if not jobs:
        return

    try:
        settings = get_settings()
        repository.upsert_jobs(
            jobs,
            ttl_days=settings.JOBS_SHARED_CACHE_TTL_DAYS,
            ingestion_run_id=ingestion_run_id,
        )
        logger.warning(
            "Upserted jobs into Supabase cache. count=%s ingestion_run_id=%s",
            len(jobs),
            ingestion_run_id,
        )
    except Exception as exc:
        logger.exception("Failed to upsert jobs into Supabase cache.", exc_info=exc)


async def _refresh_jobs_from_providers_if_allowed(
    *,
    repository: JobCacheRepository,
    query_key: str,
    remote_only: bool,
    levels: list[str] | None,
    role_types: list[str] | None,
    location_query: str | None,
    providers: dict[str, Any],
) -> list[NormalizedJob]:
    """Refresh from providers only when cooldown and running guards allow it."""
    settings = get_settings()

    if not providers:
        logger.warning("No job providers are configured.")
        return []

    eligible_runs: list[tuple[str, Any, str | None]] = []

    for provider_name, provider in providers.items():
        if repository.has_running_ingestion(
            provider=provider_name,
            query_key=query_key,
            within_seconds=settings.JOBS_INGESTION_RUNNING_TTL_SECONDS,
        ):
            logger.warning(
                "Skipping provider refresh because a run is already active. provider=%s query_key=%s",
                provider_name,
                query_key,
            )
            continue

        if repository.has_recent_successful_run(
            provider=provider_name,
            query_key=query_key,
            within_seconds=settings.JOBS_PROVIDER_REFRESH_COOLDOWN_SECONDS,
        ):
            logger.warning(
                "Skipping provider refresh because cooldown is active. provider=%s query_key=%s",
                provider_name,
                query_key,
            )
            continue

        run = repository.create_ingestion_run(
            provider=provider_name,
            query_key=query_key,
            status_value="running",
            metadata={
                "remote_only": remote_only,
                "levels": levels or [],
                "role_types": role_types or [],
                "location_query": (location_query or "").strip(),
            },
        )
        run_id = str(run.get("id") or "").strip() or None
        eligible_runs.append((provider_name, provider, run_id))

    if not eligible_runs:
        logger.warning("No eligible providers available for live refresh.")
        return []

    semaphore = asyncio.Semaphore(max(1, settings.JOBS_PROVIDER_MAX_CONCURRENCY))
    tasks = [
        _refresh_single_provider(
            semaphore=semaphore,
            repository=repository,
            provider_name=provider_name,
            provider=provider,
            run_id=run_id,
            remote_only=remote_only,
            levels=levels,
            role_types=role_types,
            location_query=location_query,
        )
        for provider_name, provider, run_id in eligible_runs
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs: list[NormalizedJob] = []

    for result in results:
        if isinstance(result, Exception):
            logger.exception("Parallel provider refresh task failed.", exc_info=result)
            continue

        all_jobs.extend(result)

    deduped_all_jobs = dedupe_jobs(all_jobs)
    capped_jobs = deduped_all_jobs[: settings.JOBS_MAX_LIVE_AGGREGATE_JOBS]

    logger.warning(
        "Live refresh complete. aggregated=%s deduped=%s capped=%s",
        len(all_jobs),
        len(deduped_all_jobs),
        len(capped_jobs),
    )

    return capped_jobs


async def _refresh_single_provider(
    *,
    semaphore: asyncio.Semaphore,
    repository: JobCacheRepository,
    provider_name: str,
    provider: Any,
    run_id: str | None,
    remote_only: bool,
    levels: list[str] | None,
    role_types: list[str] | None,
    location_query: str | None,
) -> list[NormalizedJob]:
    """Fetch, filter, dedupe, and persist a single provider result."""
    raw_count = 0
    normalized_count = 0
    deduped_count = 0

    async with semaphore:
        try:
            provider_jobs = await _fetch_provider_jobs(provider_name, provider)
            raw_count = len(provider_jobs)

            provider_normalized: list[NormalizedJob] = []
            for provider_job in provider_jobs:
                normalized = _coerce_to_normalized_job(
                    provider_job=provider_job,
                    source=provider_name,
                )
                if normalized is not None:
                    provider_normalized.append(normalized)

            normalized_count = len(provider_normalized)

            filtered_provider_jobs = _apply_job_filters(
                jobs=provider_normalized,
                remote_only=remote_only,
                levels=levels,
                role_types=role_types,
                location_query=location_query,
            )

            deduped_provider_jobs = dedupe_jobs(filtered_provider_jobs)
            deduped_count = len(deduped_provider_jobs)

            if deduped_provider_jobs:
                _write_jobs_to_db_cache(
                    repository=repository,
                    jobs=deduped_provider_jobs,
                    ingestion_run_id=run_id,
                )

            if run_id:
                repository.complete_ingestion_run(
                    run_id=run_id,
                    status_value="success",
                    raw_count=raw_count,
                    normalized_count=normalized_count,
                    deduped_count=deduped_count,
                    metadata={"provider": provider_name},
                )

            logger.warning(
                "Provider refresh complete. provider=%s raw=%s normalized=%s filtered=%s kept=%s",
                provider_name,
                raw_count,
                normalized_count,
                len(filtered_provider_jobs),
                deduped_count,
            )

            return deduped_provider_jobs

        except Exception as exc:
            logger.exception(
                "Provider refresh failed. provider=%s error=%s",
                provider_name,
                exc,
            )
            if run_id:
                repository.complete_ingestion_run(
                    run_id=run_id,
                    status_value="failed",
                    raw_count=raw_count,
                    normalized_count=normalized_count,
                    deduped_count=deduped_count,
                    error_message=str(exc),
                    metadata={"provider": provider_name},
                )
            return []


def _apply_job_filters(
    *,
    jobs: list[NormalizedJob],
    remote_only: bool = False,
    levels: list[str] | None = None,
    role_types: list[str] | None = None,
    location_query: str | None = None,
) -> list[NormalizedJob]:
    """Apply shared U.S./experience/remote/location filters to normalized jobs."""
    options = build_filter_options(
        levels=levels,
        role_types=role_types,
        location_query=location_query,
    )

    filtered: list[NormalizedJob] = []

    for job in jobs:
        if not should_keep_us_focused_job(
            title=job.title,
            location=job.location,
            description=job.description,
            remote_flag=job.remote,
            source=job.source,
        ):
            continue

        if not should_include_job(
            title=job.title,
            normalized_level=job.experience_level,
            normalized_role_type=job.role_type,
            options=options,
        ):
            continue

        if remote_only and not _is_remote_job(job):
            continue

        if not should_match_location_query(
            location_query=options.selected_location_query,
            title=job.title,
            location=job.location,
            location_display=job.location_display,
            description=job.description,
            remote_flag=job.remote,
            remote_type=job.remote_type,
        ):
            continue

        filtered.append(job)

    return filtered


async def _fetch_provider_jobs(
    provider_name: str,
    provider: Any,
) -> list[Any]:
    """Fetch jobs from a single provider instance."""
    fetcher = provider.fetch_jobs
    jobs = fetcher()
    if inspect.isawaitable(jobs):
        jobs = await jobs

    if not isinstance(jobs, list):
        logger.warning(
            "Provider returned non-list payload. provider=%s type=%s",
            provider_name,
            type(jobs).__name__,
        )
        return []

    return jobs


def _coerce_to_normalized_job(
    provider_job: Any,
    source: str,
) -> NormalizedJob | None:
    """Accept both already-normalized jobs and legacy dict payloads."""
    if isinstance(provider_job, NormalizedJob):
        return attach_normalized_skills(provider_job)

    if isinstance(provider_job, dict):
        normalized = normalize_provider_job(
            raw_job=provider_job,
            source=source,
        )
        if normalized is not None:
            return attach_normalized_skills(normalized)

        try:
            return NormalizedJob.model_validate(provider_job)
        except Exception:
            logger.exception(
                "Failed to validate provider job as NormalizedJob. source=%s",
                source,
            )
            return None

    return None


def _should_return_shared_jobs_immediately(shared_jobs: list[dict[str, Any]]) -> bool:
    """Return shared jobs immediately when they are good enough for fast UX."""
    settings = get_settings()
    count = len(shared_jobs)

    return (
        count >= settings.JOBS_SHARED_CACHE_MIN_RESULTS
        or count >= settings.JOBS_MIN_IMMEDIATE_RESULTS
    )


def _cap_jobs_for_response(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cap jobs list size for faster serialization and frontend work."""
    settings = get_settings()
    return jobs[: settings.JOBS_MAX_RESPONSE_JOBS]


def _cleanup_shared_cache_if_due(repository: JobCacheRepository) -> None:
    """Throttle shared-cache cleanup so it does not run on every request."""
    global _LAST_SHARED_CACHE_CLEANUP_AT

    settings = get_settings()
    now = time.time()

    if (now - _LAST_SHARED_CACHE_CLEANUP_AT) < settings.JOBS_CACHE_CLEANUP_INTERVAL_SECONDS:
        return

    try:
        cleanup_result = repository.cleanup_expired_jobs(grace_hours=48)
        _LAST_SHARED_CACHE_CLEANUP_AT = now
        logger.warning(
            "Jobs cache cleanup complete. marked_inactive=%s deleted=%s",
            cleanup_result["marked_inactive"],
            cleanup_result["deleted"],
        )
    except Exception as exc:
        logger.exception("Failed during jobs cache cleanup.", exc_info=exc)


def _get_mock_jobs() -> list[dict[str, Any]]:
    """Return minimal mock fallback jobs."""
    return [
        {
            "id": "mock-junior-software-engineer",
            "title": "Junior Software Engineer",
            "company": "EarlyBloom Demo",
            "location": "Remote, United States",
            "location_display": "Remote, United States",
            "remote": True,
            "remote_type": "remote",
            "description": "Fallback mock job used only when live ingestion is unavailable.",
            "summary": "Fallback mock job used only when live ingestion is unavailable.",
            "source": "mock",
            "source_job_id": None,
            "url": "https://example.com/jobs/junior-software-engineer",
            "employment_type": "full-time",
            "experience_level": "junior",
            "role_type": "software-engineering",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": None,
            "responsibilities": [],
            "qualifications": [],
            "required_skills": [],
            "preferred_skills": [],
            "stable_key": None,
            "provider_payload_hash": None,
            "viewer_state": {
                "is_saved": False,
                "is_hidden": False,
                "saved_at": None,
                "hidden_at": None,
            },
        }
    ]


def _is_remote_job(job: NormalizedJob) -> bool:
    """Determine whether a normalized job should be treated as remote."""
    if bool(job.remote):
        return True

    remote_type = str(job.remote_type or "").lower()
    if remote_type == "remote":
        return True

    location = _normalize_text(job.location)
    description = _normalize_text(job.description)

    return "remote" in location or "remote" in description or "telework" in description


def _build_public_job_id(job: NormalizedJob) -> str:
    """Build a stable public job ID from source and URL."""
    source = job.source or "unknown"
    canonical_url = _canonical_url(str(job.url or ""))
    if canonical_url:
        return f"{source}:{canonical_url}"
    return f"{source}:{job.id or 'no-id'}"


def _canonical_url(url: str) -> str:
    """Normalize a URL for public ID generation."""
    raw = str(url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()


def _normalize_text(value: Any) -> str:
    """Normalize arbitrary text for matching."""
    return " ".join(str(value or "").strip().lower().split())