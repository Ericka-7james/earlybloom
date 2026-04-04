"""Job ingestion service for EarlyBloom.

This module orchestrates provider ingestion for the jobs API.

Layer 1 strategy:
- Load enabled providers from the registry
- Fetch provider-normalized jobs asynchronously
- Keep only U.S.-based / U.S.-eligible jobs
- Keep entry-level, junior, mid-level, and plausible unknown jobs
- Deduplicate and map into the public response shape
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
        self.providers = providers or {}

    async def ingest_jobs(
        self,
        remote_only: bool = False,
        levels: list[str] | None = None,
        role_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return await get_jobs(
            remote_only=remote_only,
            levels=levels,
            role_types=role_types,
            providers=self.providers or None,
        )


async def get_jobs(
    remote_only: bool = False,
    levels: list[str] | None = None,
    role_types: list[str] | None = None,
    providers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Public entry point for jobs ingestion."""
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        return _get_mock_jobs()

    provider_registry = providers or get_configured_providers()
    cache_key = build_jobs_cache_key(
        remote_only=remote_only,
        provider_names=list(provider_registry.keys()),
    )

    cached = get_cached_value(cache_key)
    if cached is not None and levels is None and role_types is None:
        return cached

    live_jobs = await _get_live_jobs(
        remote_only=remote_only,
        levels=levels,
        role_types=role_types,
        providers=provider_registry,
    )

    if levels is None and role_types is None:
        set_cached_value(cache_key, live_jobs)

    return live_jobs


async def _get_live_jobs(
    remote_only: bool = False,
    levels: list[str] | None = None,
    role_types: list[str] | None = None,
    providers: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate live jobs from configured providers."""
    options = build_filter_options(
        levels=levels,
        role_types=role_types,
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

        provider_jobs = provider_result
        if not provider_jobs:
            logger.warning("Provider returned no jobs. provider=%s", provider_name)
            continue

        received_count = len(provider_jobs)
        normalized_count = 0
        non_us_filtered_count = 0
        filtered_out_count = 0
        kept_count = 0

        for provider_job in provider_jobs:
            normalized = _coerce_to_normalized_job(
                provider_job=provider_job,
                source=provider_name,
            )
            if normalized is None:
                continue

            normalized_count += 1

            if not _is_us_eligible_job(normalized):
                non_us_filtered_count += 1
                continue

            if not should_include_job(
                title=normalized.title,
                normalized_level=normalized.experience_level,
                normalized_role_type=None,
                options=options,
            ):
                filtered_out_count += 1
                continue

            normalized_jobs.append(normalized)
            kept_count += 1

        logger.warning(
            (
                "Provider ingestion complete. provider=%s received=%s normalized=%s "
                "filtered_non_us=%s filtered_by_options=%s kept=%s"
            ),
            provider_name,
            received_count,
            normalized_count,
            non_us_filtered_count,
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
) -> list[Any]:
    """Fetch jobs from a single provider instance."""
    jobs = await provider.fetch_jobs()

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
        return provider_job

    if isinstance(provider_job, dict):
        normalized = normalize_provider_job(
            raw_job=provider_job,
            source=source,
        )
        if normalized is not None:
            return normalized

        try:
            return NormalizedJob.model_validate(provider_job)
        except Exception:
            return None

    return None


def _get_mock_jobs() -> list[dict[str, Any]]:
    """Return minimal mock fallback jobs."""
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


def _is_us_eligible_job(job: NormalizedJob) -> bool:
    """Keep only U.S.-based / U.S.-eligible roles for EarlyBloom Layer 1."""
    text = " ".join(
        [
            _normalize_text(job.title),
            _normalize_text(job.location),
            _normalize_text(job.description),
            _normalize_text(job.summary),
        ]
    )

    positive_markers = [
        "united states",
        "united states only",
        "us only",
        "u.s. only",
        "usa",
        "u.s.a.",
        "us-based",
        "u.s.-based",
        "based in the united states",
        "must be authorized to work in the us",
        "must be authorized to work in the u.s.",
        "eligible to work in the us",
        "eligible to work in the united states",
        "work authorization in the us",
        "citizenship required",
        "u.s. citizenship",
        "federal government",
        "telework eligible",
    ]

    negative_markers = [
        "anywhere in the world",
        "worldwide",
        "europe only",
        "europe",
        "uk only",
        "united kingdom",
        "canada only",
        "canada",
        "germany",
        "france",
        "spain",
        "poland",
        "netherlands",
        "portugal",
        "latam",
        "latin america",
        "apac",
        "emea",
        "asia pacific",
        "berlin",
        "london",
        "amsterdam",
        "barcelona",
        "lisbon",
        "warsaw",
    ]

    if any(marker in text for marker in positive_markers):
        return True

    if any(marker in text for marker in negative_markers):
        return False

    location = _normalize_text(job.location)
    if location in {"remote", "unknown", ""}:
        return False

    us_state_tokens = {
        "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "ia",
        "id", "il", "in", "ks", "ky", "la", "ma", "md", "me", "mi", "mn", "mo",
        "ms", "mt", "nc", "nd", "ne", "nh", "nj", "nm", "nv", "ny", "oh", "ok",
        "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "va", "vt", "wa", "wi",
        "wv", "wy", "dc",
    }
    us_state_names = {
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new hampshire", "new jersey", "new mexico", "new york",
        "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode island", "south carolina", "south dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west virginia", "wisconsin", "wyoming", "district of columbia",
    }

    location_parts = {
        part.strip(" ,")
        for part in location.replace("/", ",").split(",")
        if part.strip(" ,")
    }

    if any(part in us_state_tokens or part in us_state_names for part in location_parts):
        return True

    return False


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


def _map_internal_job_to_response(job: NormalizedJob) -> dict[str, Any]:
    """Map normalized data into the public jobs API response shape."""
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