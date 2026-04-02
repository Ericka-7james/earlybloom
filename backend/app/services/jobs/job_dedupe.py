from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.schemas.jobs import NormalizedJob

_WHITESPACE_RE = re.compile(r"\s+")


def dedupe_jobs(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    """
    Dedupe across providers using layered fingerprints.

    Priority:
    1. canonical URL
    2. normalized source + title/company/location
    3. normalized title/company/location

    When duplicates are found, we merge them and keep the richer record.
    """
    seen: dict[str, NormalizedJob] = {}
    ordered: list[NormalizedJob] = []

    for job in jobs:
        key = _best_key(job)

        if key not in seen:
            seen[key] = job
            ordered.append(job)
            continue

        merged = _merge_jobs(seen[key], job)
        seen[key] = merged

        for idx, existing in enumerate(ordered):
            if existing.id == merged.id or _best_key(existing) == key:
                ordered[idx] = merged
                break

    return ordered


def _best_key(job: NormalizedJob) -> str:
    url_key = _canonicalize_url(str(job.url or ""))
    if url_key:
        return f"url::{url_key}"

    source_title_company_location = "::".join(
        [
            _norm(job.source),
            _norm(job.title),
            _norm(job.company),
            _norm(job.location),
        ]
    )
    if source_title_company_location.replace("::", ""):
        return f"stcl::{source_title_company_location}"

    title_company_location = "::".join(
        [
            _norm(job.title),
            _norm(job.company),
            _norm(job.location),
        ]
    )
    return f"tcl::{title_company_location}"


def _merge_jobs(left: NormalizedJob, right: NormalizedJob) -> NormalizedJob:
    """
    Prefer the richer record while preserving compatibility with the existing schema.
    """
    description = _prefer_longer(left.description, right.description)
    summary = _prefer_longer(left.summary, right.summary)
    responsibilities = _merge_list(left.responsibilities, right.responsibilities)
    qualifications = _merge_list(left.qualifications, right.qualifications)
    required_skills = _merge_list(left.required_skills, right.required_skills)
    preferred_skills = _merge_list(left.preferred_skills, right.preferred_skills)

    remote_type = left.remote_type
    if remote_type == "unknown" and right.remote_type != "unknown":
        remote_type = right.remote_type

    experience_level = left.experience_level
    if experience_level == "unknown" and right.experience_level != "unknown":
        experience_level = right.experience_level

    employment_type = left.employment_type or right.employment_type

    return left.model_copy(
        update={
            "summary": summary,
            "description": description,
            "responsibilities": responsibilities,
            "qualifications": qualifications,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "remote": left.remote or right.remote,
            "remote_type": remote_type,
            "experience_level": experience_level,
            "employment_type": employment_type,
            "url": str(left.url or right.url),
        }
    )


def _merge_list(left: list[str], right: list[str], max_items: int = 12) -> list[str]:
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
    return right if len((right or "").strip()) > len((left or "").strip()) else left


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value).strip().casefold()


def _canonicalize_url(url: str) -> str:
    if not url:
        return ""

    parts = urlsplit(url)
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    cleaned_query = urlencode(query_items)

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            cleaned_query,
            "",
        )
    )