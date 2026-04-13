"""Cross-source deduplication helpers for normalized jobs."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas.jobs import NormalizedJob
from app.services.jobs.constants import (
    PROVIDER_SOURCE_PRIORITY,
    URL_IGNORED_QUERY_PARAMS,
)

_WHITESPACE_RE = re.compile(r"\s+")
_LOCATION_SPLIT_RE = re.compile(r"\s*;\s*|\s*\|\s*")
_MULTI_LOCATION_SOURCES = {
    "greenhouse",
    "lever",
}

_EXPERIENCE_LEVEL_RANK = {
    "unknown": 0,
    "entry-level": 1,
    "junior": 2,
    "mid-level": 3,
    "senior": 4,
}

_REMOTE_TYPE_RANK = {
    "unknown": 0,
    "onsite": 1,
    "hybrid": 2,
    "remote": 3,
}


def dedupe_jobs(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    """Dedupe normalized jobs across providers using layered aliases.

    The dedupe strategy uses multiple aliases for each job:
    1. Canonical URL
    2. Source + title + company + location
    3. Title + company + location
    4. For selected multi-location commercial providers, source + title + company

    When duplicates are detected, the richer record is kept and merged.

    Args:
        jobs: Normalized jobs to deduplicate.

    Returns:
        Deduplicated jobs in stable input order.
    """
    merged_jobs: list[NormalizedJob] = []
    alias_to_index: dict[str, int] = {}

    for job in jobs:
        candidate_aliases = _candidate_aliases(job)
        existing_index = _find_existing_index(candidate_aliases, alias_to_index)

        if existing_index is None:
            merged_jobs.append(job)
            new_index = len(merged_jobs) - 1
            for alias in candidate_aliases:
                alias_to_index[alias] = new_index
            continue

        merged = _merge_jobs(merged_jobs[existing_index], job)
        merged_jobs[existing_index] = merged

        for alias in _candidate_aliases(merged):
            alias_to_index[alias] = existing_index

    return merged_jobs


def _find_existing_index(
    aliases: set[str],
    alias_to_index: dict[str, int],
) -> int | None:
    """Return the first matching dedupe index for any candidate alias."""
    for alias in aliases:
        if alias in alias_to_index:
            return alias_to_index[alias]
    return None


def _candidate_aliases(job: NormalizedJob) -> set[str]:
    """Build layered dedupe aliases for a normalized job."""
    aliases: set[str] = set()

    canonical_url = _canonicalize_url(str(job.url or ""))
    if canonical_url:
        aliases.add(f"url::{canonical_url}")

    source_title_company_location = "::".join(
        [
            _norm(job.source),
            _norm(job.title),
            _norm(job.company),
            _norm(job.location),
        ]
    )
    if source_title_company_location.replace("::", ""):
        aliases.add(f"stcl::{source_title_company_location}")

    title_company_location = "::".join(
        [
            _norm(job.title),
            _norm(job.company),
            _norm(job.location),
        ]
    )
    if title_company_location.replace("::", ""):
        aliases.add(f"tcl::{title_company_location}")

    # For selected ATS-style providers, also merge same title/company/source
    # across multiple office postings.
    if _supports_multilocation_family_merge(job):
        source_title_company = "::".join(
            [
                _norm(job.source),
                _norm(job.title),
                _norm(job.company),
            ]
        )
        if source_title_company.replace("::", ""):
            aliases.add(f"stc::{source_title_company}")

    return aliases


def _supports_multilocation_family_merge(job: NormalizedJob) -> bool:
    """Return True when same-role multi-location cards should be merged."""
    source = _norm(job.source)
    if source not in _MULTI_LOCATION_SOURCES:
        return False

    title = _norm(job.title)
    company = _norm(job.company)
    if not title or not company:
        return False

    # Be conservative and avoid over-merging govt-ish or generic cases.
    if source == "usajobs":
        return False

    return True


def _merge_jobs(left: NormalizedJob, right: NormalizedJob) -> NormalizedJob:
    """Merge two duplicate jobs into a single richer record."""
    primary, secondary = _choose_primary(left, right)

    merged_summary = _prefer_longer(primary.summary, secondary.summary)
    merged_description = _prefer_longer(primary.description, secondary.description)
    merged_responsibilities = _merge_list(primary.responsibilities, secondary.responsibilities)
    merged_qualifications = _merge_list(primary.qualifications, secondary.qualifications)
    merged_required_skills = _merge_list(primary.required_skills, secondary.required_skills)
    merged_preferred_skills = _merge_list(primary.preferred_skills, secondary.preferred_skills)

    merged_remote_type = _prefer_ranked_value(
        primary.remote_type,
        secondary.remote_type,
        _REMOTE_TYPE_RANK,
    )
    merged_experience_level = _prefer_ranked_value(
        primary.experience_level,
        secondary.experience_level,
        _EXPERIENCE_LEVEL_RANK,
    )

    merged_role_type = primary.role_type
    if str(merged_role_type or "").strip().lower() == "unknown":
        merged_role_type = secondary.role_type

    salary_min = primary.salary_min if primary.salary_min is not None else secondary.salary_min
    salary_max = primary.salary_max if primary.salary_max is not None else secondary.salary_max
    salary_currency = primary.salary_currency or secondary.salary_currency
    employment_type = primary.employment_type or secondary.employment_type

    merged_location = _merge_locations(primary.location, secondary.location)
    merged_location_display = _merge_locations(
        primary.location_display or primary.location,
        secondary.location_display or secondary.location,
    )
    merged_url = str(primary.url or secondary.url or "")
    merged_source_job_id = primary.source_job_id or secondary.source_job_id
    merged_stable_key = primary.stable_key or secondary.stable_key
    merged_provider_payload_hash = primary.provider_payload_hash or secondary.provider_payload_hash

    return primary.model_copy(
        update={
            "summary": merged_summary,
            "description": merged_description,
            "responsibilities": merged_responsibilities,
            "qualifications": merged_qualifications,
            "required_skills": merged_required_skills,
            "preferred_skills": merged_preferred_skills,
            "remote": bool(primary.remote or secondary.remote),
            "remote_type": merged_remote_type,
            "experience_level": merged_experience_level,
            "role_type": merged_role_type,
            "employment_type": employment_type,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "location": merged_location,
            "location_display": merged_location_display,
            "url": merged_url,
            "source_job_id": merged_source_job_id,
            "stable_key": merged_stable_key,
            "provider_payload_hash": merged_provider_payload_hash,
        }
    )


def _choose_primary(left: NormalizedJob, right: NormalizedJob) -> tuple[NormalizedJob, NormalizedJob]:
    """Choose the stronger base record before merging."""
    left_score = _richness_score(left)
    right_score = _richness_score(right)

    if right_score > left_score:
        return right, left
    return left, right


def _richness_score(job: NormalizedJob) -> int:
    """Score a job by source trust and field richness."""
    score = PROVIDER_SOURCE_PRIORITY.get(str(job.source or "").lower(), 0)

    if job.summary:
        score += 5
    if job.description:
        score += min(len(job.description) // 200, 20)
    if job.responsibilities:
        score += min(len(job.responsibilities), 8)
    if job.qualifications:
        score += min(len(job.qualifications), 8)
    if job.required_skills:
        score += min(len(job.required_skills), 8)
    if job.preferred_skills:
        score += min(len(job.preferred_skills), 6)
    if job.salary_min is not None or job.salary_max is not None:
        score += 5
    if job.remote_type != "unknown":
        score += 2
    if job.experience_level != "unknown":
        score += 2
    if job.role_type != "unknown":
        score += 2
    if str(job.url or "").strip():
        score += 4
    if str(job.location_display or job.location or "").strip():
        score += 2

    return score


def _merge_list(left: list[str], right: list[str], max_items: int = 12) -> list[str]:
    """Merge two string lists while preserving order and uniqueness."""
    seen: set[str] = set()
    merged: list[str] = []

    for item in [*left, *right]:
        normalized = _norm(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(item.strip())
        if len(merged) >= max_items:
            break

    return merged


def _prefer_longer(left: str, right: str) -> str:
    """Prefer the longer non-empty text value."""
    return right if len((right or "").strip()) > len((left or "").strip()) else left


def _prefer_ranked_value(
    left: str | None,
    right: str | None,
    ranking: dict[str, int],
) -> str:
    """Prefer the higher-ranked normalized categorical value."""
    left_value = (left or "unknown").strip().lower()
    right_value = (right or "unknown").strip().lower()

    if ranking.get(right_value, 0) > ranking.get(left_value, 0):
        return right_value
    return left_value


def _merge_locations(left: str | None, right: str | None) -> str:
    """Merge location strings while preserving readable order."""
    left_parts = _split_locations(left)
    right_parts = _split_locations(right)

    merged: list[str] = []
    seen: set[str] = set()

    for part in [*left_parts, *right_parts]:
        key = _norm(part)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(part)

    if not merged:
        return ""

    if len(merged) == 1:
        return merged[0]

    return "; ".join(merged)


def _split_locations(value: str | None) -> list[str]:
    """Split a location string into de-duplicable pieces."""
    raw = str(value or "").strip()
    if not raw:
        return []

    parts = _LOCATION_SPLIT_RE.split(raw)
    cleaned = [" ".join(part.split()) for part in parts if " ".join(part.split())]
    return cleaned


def _norm(value: str | None) -> str:
    """Normalize a string for matching."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value).strip().casefold()


def _canonicalize_url(url: str) -> str:
    """Canonicalize a URL for cross-source dedupe."""
    if not url:
        return ""

    parts = urlsplit(url)

    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.strip().lower() in URL_IGNORED_QUERY_PARAMS:
            continue
        query_items.append((key, value))

    cleaned_query = urlencode(query_items, doseq=True)

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            cleaned_query,
            "",
        )
    )