"""Job ingestion service for EarlyBloom.

V2 behavior:
- Strictly U.S.-focused job results
- Keep remote U.S. roles
- Exclude clearly non-U.S. jobs
- Preserve current response schema expected by the jobs API
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
# TODO(earlybloom-v3): Re-enable Arbeitnow when international / overseas feeds
# are handled separately. For V2 we are strictly U.S.-focused.
# from app.services.jobs.providers.arbeitnow import get_arbeitnow_jobs
from app.services.jobs.providers.jobicy import get_jobicy_jobs
from app.services.jobs.providers.remoteok import get_remoteok_jobs
from app.services.jobs.providers.usajobs import get_usajobs_jobs

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

US_STATE_NAMES = {
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

NON_US_LOCATION_KEYWORDS = {
    "germany",
    "berlin",
    "munich",
    "jena",
    "viersen",
    "deutschland",
    "canada",
    "toronto",
    "vancouver",
    "united kingdom",
    "uk",
    "london",
    "france",
    "paris",
    "spain",
    "madrid",
    "barcelona",
    "netherlands",
    "amsterdam",
    "poland",
    "warsaw",
    "india",
    "bangalore",
    "bengaluru",
    "mumbai",
    "delhi",
    "singapore",
    "australia",
    "sydney",
    "melbourne",
    "ireland",
    "dublin",
    "brazil",
    "mexico",
    "philippines",
    "europe",
    "emea",
    "apac",
    "latam",
}

US_REMOTE_MARKERS = {
    "united states",
    "u.s.",
    "usa",
    "us only",
    "remote us",
    "remote - us",
    "remote, us",
    "must be based in the us",
    "must be authorized to work in the united states",
    "authorized to work in the u.s.",
}


class JobIngestionService:
    """Thin service wrapper around the existing function-based ingestion flow."""

    def __init__(self, providers: dict[str, Any] | None = None) -> None:
        self.providers = providers or {}

    async def ingest_jobs(
        self,
        remote_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Return jobs in the API response shape."""
        return get_jobs(remote_only=remote_only)


def get_jobs(
    remote_only: bool = False,
) -> list[dict[str, Any]]:
    """Public entry point for jobs ingestion."""
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        return _get_mock_jobs()

    cache_key = f"jobs:v2-us:{'remote' if remote_only else 'all'}"
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
) -> list[dict[str, Any]]:
    """Aggregate live jobs from enabled providers and enforce U.S.-only filtering."""
    settings = get_settings()
    aggregated: list[dict[str, Any]] = []

    provider_calls: list[tuple[str, Any]] = []

    # TODO(earlybloom-v3): Add overseas/international ingestion path.
    # For V2, keep Arbeitnow disabled because it is overwhelmingly non-U.S.
    # if settings.JOB_PROVIDER_ARBEITNOW_ENABLED:
    #     provider_calls.append(
    #         (
    #             "arbeitnow",
    #             lambda: get_arbeitnow_jobs(
    #                 pages=settings.JOB_PROVIDER_ARBEITNOW_PAGES,
    #                 remote_only=remote_only,
    #             ),
    #         )
    #     )

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
            if not jobs:
                continue

            us_jobs = [
                job for job in jobs
                if _is_us_focused_job(job=job, provider_name=provider_name)
            ]

            if us_jobs:
                aggregated.extend(us_jobs)

            logger.info(
                "Provider filtering complete. provider=%s raw=%s us_kept=%s",
                provider_name,
                len(jobs),
                len(us_jobs),
            )
        except Exception as exc:
            logger.exception(
                "Job provider failed. provider=%s error=%s",
                provider_name,
                exc,
            )

    if remote_only:
        aggregated = [job for job in aggregated if _is_remote_job(job)]

    deduped = _dedupe_jobs(aggregated)
    preferred = _prefer_early_career_jobs(deduped)

    final_internal_jobs = preferred or deduped
    return [_map_internal_job_to_response(job) for job in final_internal_jobs]


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
            "salary_currency": "USD",
            "responsibilities": [],
            "qualifications": [],
            "required_skills": [],
            "preferred_skills": [],
        }
    ]


def _get_cached(cache_key: str) -> list[dict[str, Any]] | None:
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


def _set_cache(cache_key: str, jobs: list[dict[str, Any]]) -> None:
    """Store jobs in the in-memory cache."""
    _CACHE[cache_key] = (time.time(), jobs)


def _is_us_focused_job(job: dict[str, Any], provider_name: str) -> bool:
    """Return True only for jobs that are clearly U.S.-based or U.S.-remote.

    Rules for V2:
    - Always allow USAJobs
    - Reject clearly non-U.S. locations
    - Keep explicit U.S. locations
    - Keep remote roles only when they explicitly mention U.S. / USA / United States
    """
    if provider_name == "usajobs":
        return True

    title = _normalize_text(job.get("title"))
    location = _normalize_text(job.get("location"))
    description = _normalize_text(job.get("description"))
    company = _normalize_text(job.get("company") or job.get("company_name"))
    combined = f"{title} {location} {description} {company}"

    if _looks_non_us(combined):
        return False

    if _looks_us_location(location):
        return True

    if _looks_us_remote(combined):
        return True

    return False


def _looks_non_us(text: str) -> bool:
    """Return True if the text clearly points to a non-U.S. role."""
    return any(keyword in text for keyword in NON_US_LOCATION_KEYWORDS)


def _looks_us_remote(text: str) -> bool:
    """Return True if a role explicitly says U.S. / USA / United States."""
    return any(marker in text for marker in US_REMOTE_MARKERS)


def _looks_us_location(text: str) -> bool:
    """Return True if the text clearly looks U.S.-based."""
    if not text:
        return False

    if "united states" in text or "u.s." in text or "usa" in text:
        return True

    for state_name in US_STATE_NAMES:
        if state_name in text:
            return True

    tokens = re.split(r"[\s,()/|-]+", text.upper())
    return any(token in US_STATE_CODES for token in tokens if token)


def _dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate jobs across providers by canonical URL, then title plus company."""
    seen_urls: set[str] = set()
    seen_title_company: set[str] = set()
    deduped: list[dict[str, Any]] = []

    for job in jobs:
        url = _canonical_url(job.get("url"))
        title = _normalize_text(job.get("title"))
        company = _normalize_text(job.get("company") or job.get("company_name"))
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


def _prefer_early_career_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer early-career jobs and exclude obvious senior roles where possible."""
    filtered: list[dict[str, Any]] = []

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
        "ai",
        "ml",
    }
    return any(signal in text for signal in signals)


def _is_remote_job(job: dict[str, Any]) -> bool:
    """Determine whether a normalized internal job should be treated as remote."""
    remote_type = str(job.get("remote_type") or "").lower()
    location = _normalize_text(job.get("location"))
    description = _normalize_text(job.get("description"))

    if remote_type == "remote":
        return True

    if "remote" in location or "remote" in description or "telework" in description:
        return True

    return False


def _map_internal_job_to_response(job: dict[str, Any]) -> dict[str, Any]:
    """Map the internal normalized provider shape into the API response schema."""
    description = _strip_html(job.get("description") or "")
    qualifications = _extract_requirements(job)
    required_skills = qualifications[:]
    remote_type = _infer_remote_type(job)
    remote = remote_type == "remote"

    return {
        "id": _build_public_job_id(job),
        "title": job.get("title") or "Unknown title",
        "company": job.get("company") or job.get("company_name") or "Unknown company",
        "location": job.get("location") or "",
        "remote": remote,
        "remote_type": remote_type,
        "url": job.get("url"),
        "source": job.get("source") or "unknown",
        "summary": _build_summary(description),
        "description": description,
        "responsibilities": [],
        "qualifications": qualifications,
        "required_skills": required_skills,
        "preferred_skills": [],
        "employment_type": job.get("employment_type"),
        "experience_level": _infer_experience_level(job),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_currency": job.get("salary_currency") or job.get("currency") or "USD",
    }


def _build_public_job_id(job: dict[str, Any]) -> str:
    """Build a stable public job id from source and provider id or URL."""
    source = job.get("source") or "unknown"
    external_id = job.get("external_id") or _canonical_url(job.get("url")) or "no-id"
    return f"{source}:{external_id}"


def _infer_experience_level(job: dict[str, Any]) -> str:
    """Infer a coarse experience level from title and description."""
    combined = _normalize_text(
        f"{job.get('title', '')} {job.get('description', '')} {job.get('seniority_hint', '')}"
    )

    if _looks_senior(combined):
        return "senior"

    if any(term in combined for term in {"mid", "mid-level", "intermediate", "level ii", "level 2"}):
        return "mid"

    if any(term in combined for term in {"entry level", "entry-level", "new grad", "graduate", "associate"}):
        return "entry-level"

    if _looks_early_career(combined):
        return "junior"

    return "unknown"


def _infer_remote_type(job: dict[str, Any]) -> str:
    """Infer remote type from provider fields and text."""
    remote_type = str(job.get("remote_type") or "").strip().lower()
    if remote_type in {"remote", "hybrid", "onsite", "unknown"}:
        return remote_type

    combined = _normalize_text(
        f"{job.get('location', '')} {job.get('description', '')} {job.get('title', '')}"
    )

    if "hybrid" in combined:
        return "hybrid"
    if "onsite" in combined or "on-site" in combined or "in office" in combined:
        return "onsite"
    if "remote" in combined or "telework" in combined:
        return "remote"
    return "unknown"


def _extract_requirements(job: dict[str, Any]) -> list[str]:
    """Produce a lightweight requirements list from tags."""
    tags = job.get("tags") or []
    if not isinstance(tags, list):
        return []

    return [str(tag).strip() for tag in tags if str(tag).strip()][:10]


def _build_summary(description: str, max_length: int = 280) -> str:
    """Build a short summary from the description."""
    if not description:
        return ""

    text = description.strip()
    if len(text) <= max_length:
        return text

    return text[: max_length - 3].rstrip() + "..."


def _canonical_url(url: Any) -> str:
    """Normalize a URL for deduplication."""
    raw = str(url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()


def _normalize_text(value: Any) -> str:
    """Normalize arbitrary text for matching."""
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _strip_html(text: str) -> str:
    """Remove basic HTML tags from descriptions."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()