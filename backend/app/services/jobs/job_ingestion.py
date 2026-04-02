"""Job ingestion service for EarlyBloom.

This module orchestrates provider ingestion for the jobs API.

Current strategy:
- Load enabled providers from the Layer 1 registry
- Fetch provider-normalized raw jobs asynchronously
- Normalize all provider data through the shared normalization pipeline
- Apply shared filtering, dedupe, and response mapping
- Keep provider trust separate from normalization policy
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
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
)
from app.services.jobs.normalizer import normalize_provider_job
from app.services.jobs.providers import get_configured_providers

logger = logging.getLogger(__name__)


class JobIngestionService:
    """Service wrapper around the async ingestion flow."""

    def __init__(self, providers: dict[str, Any] | None = None) -> None:
        """Initialize the ingestion service.

        Args:
            providers: Optional provider registry override for testing.
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
        return await get_jobs(remote_only=remote_only, providers=self.providers or None)


async def get_jobs(
    remote_only: bool = False,
    providers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Public entry point for jobs ingestion.

    Args:
        remote_only: Whether to keep only remote jobs after normalization.
        providers: Optional provider registry override for testing.

    Returns:
        A list of job dictionaries matching the API response contract.
    """
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        return _get_mock_jobs()

    provider_registry = providers or get_configured_providers()
    cache_key = build_jobs_cache_key(
        remote_only=remote_only,
        provider_names=list(provider_registry.keys()),
    )

    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached

    live_jobs = await _get_live_jobs(
        remote_only=remote_only,
        providers=provider_registry,
    )
    set_cached_value(cache_key, live_jobs)
    return live_jobs


async def _get_live_jobs(
    remote_only: bool = False,
    providers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate live jobs from configured providers and normalize them.

    Args:
        remote_only: Whether to keep only remote jobs after normalization.
        providers: Optional provider registry override.

    Returns:
        A list of normalized job dictionaries matching the jobs API shape.
    """
    options = build_filter_options(
        levels=None,
        role_types=None,
    )
    provider_registry = providers or get_configured_providers()

    if not provider_registry:
        logger.warning("No job providers are configured.")
        return []

    provider_results = await asyncio.gather(
        *[
            _fetch_provider_jobs(provider_name, provider)
            for provider_name, provider in provider_registry.items()
        ],
        return_exceptions=True,
    )

    normalized_jobs: list[NormalizedJob] = []

    for provider_name, provider_result in zip(provider_registry.keys(), provider_results):
        if isinstance(provider_result, Exception):
            logger.exception(
                "Job provider failed. provider=%s error=%s",
                provider_name,
                provider_result,
            )
            continue

        raw_jobs = provider_result
        if not raw_jobs:
            logger.warning("Provider returned no jobs. provider=%s", provider_name)
            continue

        normalized_count = 0
        filtered_out_count = 0
        kept_count = 0

        for raw_job in raw_jobs:
            normalized = normalize_provider_job(
                raw_job=raw_job,
                source=provider_name,
            )
            if normalized is None:
                continue

            normalized_count += 1

            if not should_include_job(
                title=normalized.title,
                normalized_level=normalized.experience_level,
                normalized_role_type=getattr(normalized, "role_type", None),
                options=options,
            ):
                filtered_out_count += 1
                continue

            normalized_jobs.append(normalized)
            kept_count += 1

        logger.warning(
            "Provider normalization complete. provider=%s raw=%s normalized=%s filtered_out=%s kept=%s",
            provider_name,
            len(raw_jobs),
            normalized_count,
            filtered_out_count,
            kept_count,
        )

    if remote_only:
        before_remote_filter = len(normalized_jobs)
        normalized_jobs = [job for job in normalized_jobs if _is_remote_job(job)]
        logger.warning(
            "Remote-only filter applied. before=%s after=%s",
            before_remote_filter,
            len(normalized_jobs),
        )

    deduped_jobs = dedupe_jobs(normalized_jobs)
    logger.warning(
        "Live ingestion complete. aggregated=%s deduped=%s",
        len(normalized_jobs),
        len(deduped_jobs),
    )

    return [_map_internal_job_to_response(job) for job in deduped_jobs]


async def _fetch_provider_jobs(
    provider_name: str,
    provider: Any,
) -> list[dict[str, Any]]:
    """Fetch raw jobs from a single provider instance.

    Args:
        provider_name: Provider source name.
        provider: Provider instance implementing fetch_jobs().

    Returns:
        Provider-normalized raw jobs.

    Raises:
        Propagates provider exceptions to be handled by the caller.
    """
    raw_jobs = await provider.fetch_jobs()
    if not isinstance(raw_jobs, list):
        logger.warning(
            "Provider returned non-list payload. provider=%s type=%s",
            provider_name,
            type(raw_jobs).__name__,
        )
        return []

    return [job for job in raw_jobs if isinstance(job, dict)]


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
            "salary_currency": None,
            "responsibilities": [],
            "qualifications": [],
            "required_skills": [],
            "preferred_skills": [],
        }
    ]


def _is_remote_job(job: NormalizedJob) -> bool:
    """Determine whether a normalized job should be treated as remote.

    Args:
        job: Normalized job instance.

    Returns:
        True if the job appears remote, otherwise False.
    """
    if bool(job.remote):
        return True

    remote_type = str(job.remote_type or "").lower()
    if remote_type == "remote":
        return True

    location = _normalize_text(job.location)
    description = _normalize_text(job.description)

    return "remote" in location or "remote" in description or "telework" in description


def _map_internal_job_to_response(job: NormalizedJob) -> dict[str, Any]:
    """Map normalized data into the public jobs API response shape.

    Args:
        job: Normalized job instance.

    Returns:
        A dictionary matching the public jobs API response schema.
    """
    return {
        "id": job.id or _build_public_job_id(job),
        "title": job.title or "Unknown title",
        "company": job.company or "Unknown company",
        "location": job.location or "",
        "remote": bool(job.remote),
        "remote_type": job.remote_type or "unknown",
        "url": str(job.url or ""),
        "source": job.source or "unknown",
        "summary": job.summary or "",
        "description": job.description or "",
        "responsibilities": job.responsibilities or [],
        "qualifications": job.qualifications or [],
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "employment_type": job.employment_type,
        "experience_level": job.experience_level or "unknown",
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
    }


def _build_public_job_id(job: NormalizedJob) -> str:
    """Build a stable public job ID from source and URL.

    Args:
        job: Normalized job instance.

    Returns:
        A stable public job identifier.
    """
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