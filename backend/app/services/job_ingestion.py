from __future__ import annotations

import re
import time
from typing import Any, Dict, List
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.providers.arbeitnow import get_arbeitnow_jobs
from app.services.providers.jobicy import get_jobicy_jobs
from app.services.providers.remoteok import get_remoteok_jobs
from app.services.providers.usajobs import get_usajobs_jobs


_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def get_mock_jobs() -> List[Dict[str, Any]]:
    """Return mock jobs for local development or fallback."""
    return [
        {
            "source": "mock",
            "external_id": "mock-1",
            "title": "Frontend Engineer",
            "company": "EarlyBloom",
            "location": "Atlanta, GA",
            "remote_type": "hybrid",
            "url": "https://example.com/jobs/mock-1",
            "salary_min": 85000,
            "salary_max": 105000,
            "currency": "USD",
            "description": "Mock frontend job for local development.",
            "posted_at": None,
            "employment_type": "full-time",
            "seniority_hint": "entry-level",
            "tags": ["React", "JavaScript"],
        }
    ]


def get_live_jobs(remote_only: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch live jobs from all enabled providers.

    Args:
        remote_only: Whether to keep only remote jobs.

    Returns:
        List of internal normalized jobs from providers.
    """
    settings = get_settings()
    jobs: List[Dict[str, Any]] = []

    provider_calls: list[tuple[str, Any]] = []

    if settings.JOB_PROVIDER_ARBEITNOW_ENABLED:
        provider_calls.append(
            ("arbeitnow", lambda: get_arbeitnow_jobs(
                pages=settings.JOB_PROVIDER_ARBEITNOW_PAGES,
                remote_only=remote_only,
            ))
        )

    if settings.JOB_PROVIDER_REMOTEOK_ENABLED:
        provider_calls.append(("remoteok", get_remoteok_jobs))

    if settings.JOB_PROVIDER_JOBICY_ENABLED:
        provider_calls.append(
            ("jobicy", lambda: get_jobicy_jobs(
                pages=settings.JOB_PROVIDER_JOBICY_PAGES,
                remote_only=remote_only,
            ))
        )

    if settings.JOB_PROVIDER_USAJOBS_ENABLED:
        provider_calls.append(("usajobs", get_usajobs_jobs))

    for provider_name, provider_fn in provider_calls:
        try:
            provider_jobs = provider_fn()
            if provider_jobs:
                jobs.extend(provider_jobs)
        except Exception as exc:
            print(f"[job_ingestion] provider {provider_name} failed: {exc}")

    if remote_only:
        jobs = [job for job in jobs if _is_remote_job(job)]

    jobs = _dedupe_jobs(jobs)

    preferred_jobs = _prefer_early_career_jobs(jobs)
    return preferred_jobs or jobs


def get_jobs(remote_only: bool = False) -> List[Dict[str, Any]]:
    """
    Return jobs according to JOB_DATA_MODE with graceful fallback.

    Args:
        remote_only: Whether to keep only remote jobs.

    Returns:
        List of internal normalized jobs.
    """
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        return get_mock_jobs()

    cache_key = f"jobs:{'remote' if remote_only else 'all'}"
    cached_jobs = _get_cached(cache_key)
    if cached_jobs is not None:
        return cached_jobs

    live_jobs = get_live_jobs(remote_only=remote_only)
    if live_jobs:
        _set_cache(cache_key, live_jobs)
        return live_jobs

    fallback_jobs = get_mock_jobs()
    _set_cache(cache_key, fallback_jobs)
    return fallback_jobs


def _get_cached(cache_key: str) -> List[Dict[str, Any]] | None:
    """Return cached jobs if cache is still fresh."""
    settings = get_settings()
    entry = _CACHE.get(cache_key)

    if not entry:
        return None

    stored_at, jobs = entry
    if (time.time() - stored_at) > settings.JOB_CACHE_TTL_SECONDS:
        _CACHE.pop(cache_key, None)
        return None

    return jobs


def _set_cache(cache_key: str, jobs: List[Dict[str, Any]]) -> None:
    """Store jobs in a small in-memory cache."""
    _CACHE[cache_key] = (time.time(), jobs)


def _dedupe_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate jobs across providers by canonical URL first, then title+company.
    """
    seen_urls: set[str] = set()
    seen_title_company: set[str] = set()
    deduped: List[Dict[str, Any]] = []

    for job in jobs:
        url = _canonical_url(job.get("url"))
        title = _normalize_text(job.get("title"))
        company = _normalize_text(job.get("company"))
        title_company_key = f"{title}::{company}"

        if url and url in seen_urls:
            continue

        if title_company_key in seen_title_company:
            continue

        if url:
            seen_urls.add(url)

        seen_title_company.add(title_company_key)
        deduped.append(job)

    return deduped


def _prefer_early_career_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prefer entry-level, junior, and new grad roles while excluding obvious senior roles.
    """
    filtered: List[Dict[str, Any]] = []

    for job in jobs:
        title = _normalize_text(job.get("title"))
        description = _normalize_text(job.get("description"))
        combined = f"{title} {description}"

        if _looks_senior(combined):
            continue

        if _looks_early_career(combined) or _looks_tech_relevant(combined):
            filtered.append(job)

    return filtered


def _looks_senior(text: str) -> bool:
    """Return True if the text looks like a senior role."""
    signals = {
        "senior",
        "sr ",
        "sr.",
        "staff",
        "principal",
        "lead ",
        "manager",
        "director",
        "head of",
        "architect",
        "vp",
        "vice president",
    }
    return any(signal in text for signal in signals)


def _looks_early_career(text: str) -> bool:
    """Return True if the text looks like an early-career role."""
    signals = {
        "entry level",
        "entry-level",
        "junior",
        "new grad",
        "new graduate",
        "graduate",
        "associate",
        "trainee",
        "apprentice",
        "engineer i",
        "developer i",
        "0-2 years",
        "1-2 years",
        "recent graduate",
        "early career",
    }
    return any(signal in text for signal in signals)


def _looks_tech_relevant(text: str) -> bool:
    """Return True if the text looks tech-related."""
    signals = {
        "software",
        "developer",
        "engineer",
        "frontend",
        "front-end",
        "backend",
        "back-end",
        "full stack",
        "full-stack",
        "web",
        "mobile",
        "data",
        "qa",
        "test",
        "automation",
        "cloud",
        "security",
        "it specialist",
        "applications",
        "product engineer",
        "ui",
        "ux",
    }
    return any(signal in text for signal in signals)


def _is_remote_job(job: Dict[str, Any]) -> bool:
    """Determine whether a normalized internal job should be treated as remote."""
    remote_type = (job.get("remote_type") or "").lower()
    location = _normalize_text(job.get("location"))
    description = _normalize_text(job.get("description"))

    if remote_type == "remote":
        return True

    return (
        "remote" in location
        or "remote" in description
        or "telework" in description
    )


def _canonical_url(url: Any) -> str:
    """Normalize URL for deduplication."""
    raw = str(url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()


def _normalize_text(value: Any) -> str:
    """Normalize free text for matching."""
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text