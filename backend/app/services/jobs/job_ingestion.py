from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.jobs.providers.arbeitnow import get_arbeitnow_jobs
from app.services.jobs.providers.jobicy import get_jobicy_jobs
from app.services.jobs.providers.remoteok import get_remoteok_jobs
from app.services.jobs.providers.usajobs import get_usajobs_jobs


_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def get_jobs(
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Public entry point for jobs ingestion.

    Args:
        remote_only: Whether to keep only remote jobs.

    Returns:
        List of jobs already mapped to the API response shape.
    """
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        return _get_mock_jobs()

    cache_key = f"jobs:{'remote' if remote_only else 'all'}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    live_jobs = _get_live_jobs(remote_only=remote_only)

    if not live_jobs:
        fallback_jobs = _get_mock_jobs()
        _set_cache(cache_key, fallback_jobs)
        return fallback_jobs

    _set_cache(cache_key, live_jobs)
    return live_jobs


def _get_live_jobs(
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Aggregate live jobs from all enabled providers.
    """
    settings = get_settings()
    aggregated: List[Dict[str, Any]] = []

    provider_calls = []

    if settings.JOB_PROVIDER_ARBEITNOW_ENABLED:
        provider_calls.append(
            (
                "arbeitnow",
                lambda: get_arbeitnow_jobs(
                    pages=settings.JOB_PROVIDER_ARBEITNOW_PAGES,
                    remote_only=remote_only,
                ),
            )
        )

    if settings.JOB_PROVIDER_REMOTEOK_ENABLED:
        provider_calls.append(("remoteok", get_remoteok_jobs))

    if settings.JOB_PROVIDER_JOBICY_ENABLED:
        provider_calls.append(
            (
                "jobicy",
                lambda: get_jobicy_jobs(
                    pages=settings.JOB_PROVIDER_JOBICY_PAGES,
                    remote_only=remote_only,
                ),
            )
        )

    if settings.JOB_PROVIDER_USAJOBS_ENABLED:
        provider_calls.append(("usajobs", get_usajobs_jobs))

    for provider_name, provider_fn in provider_calls:
        try:
            jobs = provider_fn()
            if jobs:
                aggregated.extend(jobs)
        except Exception as exc:
            print(f"[job_ingestion] provider {provider_name} failed: {exc}")

    if remote_only:
        aggregated = [job for job in aggregated if _is_remote_job(job)]

    deduped = _dedupe_jobs(aggregated)
    preferred = _prefer_early_career_jobs(deduped)

    final_internal_jobs = preferred or deduped

    return [_map_internal_job_to_response(job) for job in final_internal_jobs]


def _get_mock_jobs() -> List[Dict[str, Any]]:
    """
    Minimal mock fallback.

    Replace this with your existing mock loader if you already have one elsewhere.
    """
    return [
        {
            "id": "mock-junior-software-engineer",
            "title": "Junior Software Engineer",
            "company_name": "EarlyBloom Demo",
            "location": "Remote",
            "description": "Fallback mock job used only when live ingestion is unavailable.",
            "source": "mock",
            "url": "https://example.com/jobs/junior-software-engineer",
            "employment_type": "Full-time",
            "experience_level": "junior",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "requirements": [],
        }
    ]


def _get_cached(cache_key: str) -> List[Dict[str, Any]] | None:
    """
    Return cached jobs if cache is still fresh.
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


def _set_cache(cache_key: str, jobs: List[Dict[str, Any]]) -> None:
    """
    Store jobs in simple in-memory cache.
    """
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
    Prefer early-career jobs and exclude obvious senior roles where possible.
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
    """
    Determine whether a normalized internal job should be treated as remote.
    """
    remote_type = (job.get("remote_type") or "").lower()
    location = _normalize_text(job.get("location"))
    description = _normalize_text(job.get("description"))

    if remote_type == "remote":
        return True

    if "remote" in location or "remote" in description or "telework" in description:
        return True

    return False


def _map_internal_job_to_response(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map the internal normalized provider shape into the existing API response schema.
    """
    return {
        "id": _build_public_job_id(job),
        "title": job.get("title") or "Unknown title",
        "company_name": job.get("company") or "Unknown company",
        "location": job.get("location") or "",
        "description": _strip_html(job.get("description") or ""),
        "source": job.get("source") or "unknown",
        "url": job.get("url"),
        "employment_type": job.get("employment_type"),
        "experience_level": _infer_experience_level(job),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_currency": job.get("currency") or "USD",
        "requirements": _extract_requirements(job),
    }


def _build_public_job_id(job: Dict[str, Any]) -> str:
    """
    Build a stable public job id from source and provider id/url.
    """
    source = job.get("source") or "unknown"
    external_id = job.get("external_id") or _canonical_url(job.get("url")) or "no-id"
    return f"{source}:{external_id}"


def _infer_experience_level(job: Dict[str, Any]) -> str | None:
    """
    Infer a coarse experience level from title and description.
    """
    combined = _normalize_text(
        f"{job.get('title', '')} {job.get('description', '')} {job.get('seniority_hint', '')}"
    )

    if _looks_senior(combined):
        return "senior"

    if _looks_early_career(combined):
        return "junior"

    return None


def _extract_requirements(job: Dict[str, Any]) -> List[str]:
    """
    Produce a lightweight requirements list from tags.
    """
    tags = job.get("tags") or []
    if not isinstance(tags, list):
        return []

    return [str(tag).strip() for tag in tags if str(tag).strip()][:10]


def _canonical_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _strip_html(text: str) -> str:
    """
    Remove basic HTML tags from descriptions.
    """
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()