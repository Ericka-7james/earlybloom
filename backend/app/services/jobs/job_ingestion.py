"""Job ingestion service for EarlyBloom.

This module orchestrates provider ingestion for the jobs API.

Current V2 strategy:
- Use USAJOBS as the primary and only live source for now
- Normalize all provider data through the shared normalization pipeline
- Keep the ingestion layer focused on trust, structure, and U.S. relevance
- Preserve the response schema expected by the jobs API

This intentionally narrows scope so the team can validate one provider end to end
before reintroducing noisier providers.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.jobs.job_filters import (
    build_filter_options,
    should_include_job,
)
from app.services.jobs.normalizer import normalize_provider_job
from app.services.jobs.providers.usajobs import get_usajobs_jobs

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


class JobIngestionService:
    """Thin service wrapper around the function-based ingestion flow."""

    def __init__(self, providers: dict[str, Any] | None = None) -> None:
        """Initialize the ingestion service.

        Args:
            providers: Optional provider registry for future dependency injection.
        """
        self.providers = providers or {}

    async def ingest_jobs(
        self,
        remote_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Return jobs in the API response shape.

        Args:
            remote_only: Whether to keep only remote jobs after normalization.

        Returns:
            A list of normalized job dictionaries suitable for the API response.
        """
        return get_jobs(remote_only=remote_only)


def get_jobs(
    remote_only: bool = False,
) -> list[dict[str, Any]]:
    """Public entry point for jobs ingestion.

    Args:
        remote_only: Whether to keep only remote jobs after normalization.

    Returns:
        A list of job dictionaries matching the API response contract.
    """
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        return _get_mock_jobs()

    cache_key = f"jobs:v2-usajobs-only:{'remote' if remote_only else 'all'}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    live_jobs = _get_live_jobs(remote_only=remote_only)

    # In live mode, do not silently fall back to mock jobs.
    # Returning an empty list makes it obvious when filters are too strict.
    _set_cache(cache_key, live_jobs)
    return live_jobs


def _get_live_jobs(
    remote_only: bool = False,
) -> list[dict[str, Any]]:
    """Aggregate live jobs from USAJOBS and normalize them.

    For this phase of the project, USAJOBS is intentionally the only enabled
    live source. This makes it easier to validate product usefulness, ranking,
    and data presentation without noisy third-party sources overwhelming the
    results.

    Args:
        remote_only: Whether to keep only remote jobs after normalization.

    Returns:
        A list of normalized job dictionaries matching the jobs API shape.
    """
    aggregated: list[dict[str, Any]] = []
    options = build_filter_options(
        levels=None,
        role_types=None,
    )

    provider_calls: list[tuple[str, Any]] = [
        ("usajobs", get_usajobs_jobs),
    ]

    for provider_name, provider_fn in provider_calls:
        try:
            raw_jobs = provider_fn()
            if not raw_jobs:
                logger.warning(
                    "Provider returned no jobs. provider=%s",
                    provider_name,
                )
                continue

            normalized_count = 0
            filtered_out_count = 0
            kept_count = 0

            for raw_job in raw_jobs:
                normalized = normalize_provider_job(raw_job=raw_job, source=provider_name)
                if normalized is None:
                    continue

                normalized_count += 1
                normalized_dict = normalized.model_dump(mode="json")

                if not should_include_job(
                    title=normalized_dict.get("title"),
                    normalized_level=normalized_dict.get("experience_level"),
                    normalized_role_type=normalized_dict.get("role_type"),
                    options=options,
                ):
                    filtered_out_count += 1
                    continue

                aggregated.append(normalized_dict)
                kept_count += 1

            logger.warning(
                "Provider normalization complete. provider=%s raw=%s normalized=%s filtered_out=%s kept=%s",
                provider_name,
                len(raw_jobs),
                normalized_count,
                filtered_out_count,
                kept_count,
            )
        except Exception as exc:
            logger.exception(
                "Job provider failed. provider=%s error=%s",
                provider_name,
                exc,
            )

    if remote_only:
        before_remote_filter = len(aggregated)
        aggregated = [job for job in aggregated if _is_remote_job(job)]
        logger.warning(
            "Remote-only filter applied. before=%s after=%s",
            before_remote_filter,
            len(aggregated),
        )

    deduped = _dedupe_jobs(aggregated)
    logger.warning(
        "Live ingestion complete. aggregated=%s deduped=%s",
        len(aggregated),
        len(deduped),
    )
    return [_map_internal_job_to_response(job) for job in deduped]


def _get_mock_jobs() -> list[dict[str, Any]]:
    """Return minimal mock fallback jobs.

    Returns:
        A fallback list used only when live ingestion is unavailable.
    """
    return [
        {
            "id": "mock-junior-software-engineer",
            "title": "Junior Software Engineer",
            "company": "EarlyBloom Demo",
            "location": "Remote, United States",
            "remote": True,
            "remote_type": "remote",
            "description": "Fallback mock job used only when live ingestion is unavailable.",
            "summary": "Fallback mock job used only when live ingestion is unavailable.",
            "source": "mock",
            "url": "https://example.com/jobs/junior-software-engineer",
            "employment_type": "full-time",
            "experience_level": "junior",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "responsibilities": [],
            "qualifications": [],
            "required_skills": [],
            "preferred_skills": [],
        }
    ]


def _get_cached(cache_key: str) -> list[dict[str, Any]] | None:
    """Return cached jobs if the cache entry is still fresh.

    Args:
        cache_key: Cache key for the requested job set.

    Returns:
        Cached jobs if fresh, otherwise None.
    """
    settings = get_settings()
    entry = _CACHE.get(cache_key)

    if not entry:
        return None

    stored_at, jobs = entry
    if (time.time() - stored_at) > settings.JOB_CACHE_TTL_SECONDS:
        _CACHE.pop(cache_key, None)
        return None

    return jobs


def _set_cache(cache_key: str, jobs: list[dict[str, Any]]) -> None:
    """Store jobs in the in-memory cache.

    Args:
        cache_key: Cache key for this job set.
        jobs: Jobs to cache.
    """
    _CACHE[cache_key] = (time.time(), jobs)


def _dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate jobs by normalized ID, canonical URL, then title/company.

    Args:
        jobs: Normalized job dictionaries.

    Returns:
        A deduplicated list of jobs preserving original order.
    """
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    seen_title_company: set[str] = set()
    deduped: list[dict[str, Any]] = []

    for job in jobs:
        job_id = str(job.get("id") or "").strip()
        url = _canonical_url(job.get("url"))
        title = _normalize_text(job.get("title"))
        company = _normalize_text(job.get("company"))
        title_company_key = f"{title}::{company}"

        if job_id and job_id in seen_ids:
            continue

        if url and url in seen_urls:
            continue

        if title_company_key in seen_title_company:
            continue

        if job_id:
            seen_ids.add(job_id)

        if url:
            seen_urls.add(url)

        seen_title_company.add(title_company_key)
        deduped.append(job)

    return deduped


def _is_remote_job(job: dict[str, Any]) -> bool:
    """Determine whether a normalized job should be treated as remote.

    Args:
        job: Normalized internal job dictionary.

    Returns:
        True if the job appears remote, otherwise False.
    """
    remote_value = job.get("remote")
    if isinstance(remote_value, bool) and remote_value:
        return True

    remote_type = str(job.get("remote_type") or "").lower()
    if remote_type == "remote":
        return True

    location = _normalize_text(job.get("location"))
    description = _normalize_text(job.get("description"))

    return "remote" in location or "remote" in description or "telework" in description


def _map_internal_job_to_response(job: dict[str, Any]) -> dict[str, Any]:
    """Map normalized internal data into the jobs API response shape.

    Args:
        job: Normalized internal job dictionary.

    Returns:
        A dictionary matching the public jobs API response schema.
    """
    return {
        "id": job.get("id") or _build_public_job_id(job),
        "title": job.get("title") or "Unknown title",
        "company": job.get("company") or "Unknown company",
        "location": job.get("location") or "",
        "remote": bool(job.get("remote", False)),
        "remote_type": job.get("remote_type") or "unknown",
        "url": job.get("url"),
        "source": job.get("source") or "unknown",
        "summary": job.get("summary") or "",
        "description": job.get("description") or "",
        "responsibilities": job.get("responsibilities") or [],
        "qualifications": job.get("qualifications") or [],
        "required_skills": job.get("required_skills") or [],
        "preferred_skills": job.get("preferred_skills") or [],
        "employment_type": job.get("employment_type"),
        "experience_level": job.get("experience_level") or "unknown",
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_currency": job.get("salary_currency") or "USD",
    }


def _build_public_job_id(job: dict[str, Any]) -> str:
    """Build a stable public job ID from source and provider ID or URL.

    Args:
        job: Normalized internal job dictionary.

    Returns:
        A stable public job identifier.
    """
    source = job.get("source") or "unknown"
    external_id = job.get("external_id") or _canonical_url(job.get("url")) or "no-id"
    return f"{source}:{external_id}"


def _canonical_url(url: Any) -> str:
    """Normalize a URL for deduplication.

    Args:
        url: Raw URL-like value.

    Returns:
        A canonical URL string or an empty string if invalid.
    """
    raw = str(url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()


def _normalize_text(value: Any) -> str:
    """Normalize arbitrary text for matching.

    Args:
        value: Arbitrary value to normalize.

    Returns:
        A lowercase whitespace-normalized string.
    """
    return " ".join(str(value or "").strip().lower().split())