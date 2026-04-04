"""Shared normalization pipeline for provider job payloads."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.schemas.jobs import NormalizedJob
from app.services.jobs.cleaning import clean_description
from app.services.jobs.parsing import (
    detect_employment_type,
    detect_experience_level,
    detect_remote_type,
    extract_qualifications,
    extract_responsibilities,
    extract_salary,
    extract_summary,
    split_required_and_preferred_skills,
)
from app.services.jobs.providers.common.title_rules import (
    is_early_career_title,
    is_obviously_senior_title,
)
from app.services.jobs.us_filters import (
    detect_spam_or_scam,
    should_keep_us_focused_job,
)

logger = logging.getLogger(__name__)

_EXPERIENCE_LEVEL_ALIASES = {
    "entry": "entry-level",
    "entry-level": "entry-level",
    "entry level": "entry-level",
    "junior": "junior",
    "jr": "junior",
    "mid": "mid-level",
    "mid-level": "mid-level",
    "mid level": "mid-level",
    "intermediate": "mid-level",
    "senior": "senior",
    "sr": "senior",
    "staff": "senior",
    "principal": "senior",
}


def normalize_provider_job(raw_job: dict[str, Any] | NormalizedJob, source: str) -> NormalizedJob | None:
    """Normalize a provider payload into the shared schema.

    Accepts either:
    - a legacy provider-normalized dict
    - an already-built NormalizedJob

    Returns:
        A fully normalized job or None when the record should be dropped.
    """
    try:
        if isinstance(raw_job, NormalizedJob):
            return _normalize_existing_job(raw_job)

        if not isinstance(raw_job, dict):
            logger.debug(
                "Skipping unsupported job payload type. source=%s type=%s",
                source,
                type(raw_job).__name__,
            )
            return None

        title = _safe_str(raw_job.get("title") or raw_job.get("job_title"))
        company = _safe_str(raw_job.get("company") or raw_job.get("company_name"))
        location = _safe_str(
            raw_job.get("location") or raw_job.get("candidate_required_location")
        )
        url = _safe_str(raw_job.get("url") or raw_job.get("job_url") or raw_job.get("apply_url"))
        external_id = _safe_str(raw_job.get("external_id") or raw_job.get("job_id"))
        raw_description = (
            raw_job.get("description")
            or raw_job.get("job_description")
            or raw_job.get("content")
            or raw_job.get("body")
            or ""
        )

        if not title or not company or not url:
            logger.debug(
                "Skipping job with missing required fields. source=%s title=%s company=%s url=%s",
                source,
                title,
                company,
                url,
            )
            return None

        provider_remote_flag = _coerce_bool(raw_job.get("remote"))
        provider_remote_type = _normalize_remote_type(raw_job.get("remote_type"))
        provider_employment_type = _safe_str(raw_job.get("employment_type")) or None
        provider_experience_hint = _normalize_experience_hint(raw_job.get("seniority_hint"))
        provider_summary = _safe_str(raw_job.get("summary"))
        provider_salary_min = _coerce_int(raw_job.get("salary_min"))
        provider_salary_max = _coerce_int(raw_job.get("salary_max"))
        provider_salary_currency = (
            _safe_str(raw_job.get("currency") or raw_job.get("salary_currency")) or None
        )

        provider_responsibilities = _coerce_string_list(raw_job.get("responsibilities"))
        provider_qualifications = _coerce_string_list(raw_job.get("qualifications"))
        provider_required_skills = _coerce_string_list(raw_job.get("required_skills"))
        provider_preferred_skills = _coerce_string_list(raw_job.get("preferred_skills"))

        cleaned_description = clean_description(raw_description)

        if detect_spam_or_scam(
            title=title,
            company=company,
            location=location,
            description=cleaned_description,
            url=url,
        ):
            logger.debug(
                "Dropping spam/scam job. source=%s title=%s company=%s",
                source,
                title,
                company,
            )
            return None

        if not should_keep_us_focused_job(
            title=title,
            location=location,
            description=cleaned_description,
            remote_flag=provider_remote_flag,
        ):
            logger.debug(
                "Dropping non-U.S. or unclear-scope job. source=%s title=%s company=%s location=%s",
                source,
                title,
                company,
                location,
            )
            return None

        responsibilities = provider_responsibilities or extract_responsibilities(cleaned_description)
        qualifications = provider_qualifications or extract_qualifications(cleaned_description)

        parsed_required_skills, parsed_preferred_skills = split_required_and_preferred_skills(
            qualifications=qualifications,
            description=cleaned_description,
        )

        required_skills = provider_required_skills or parsed_required_skills
        preferred_skills = provider_preferred_skills or parsed_preferred_skills

        parsed_salary_min, parsed_salary_max, parsed_salary_currency = extract_salary(
            cleaned_description
        )
        salary_min = provider_salary_min if provider_salary_min is not None else parsed_salary_min
        salary_max = provider_salary_max if provider_salary_max is not None else parsed_salary_max
        salary_currency = provider_salary_currency or parsed_salary_currency

        parsed_remote_type = detect_remote_type(
            title=title,
            location=location,
            description=cleaned_description,
        )
        remote_type = (
            provider_remote_type if provider_remote_type != "unknown" else parsed_remote_type
        )
        remote = bool(provider_remote_flag) or remote_type == "remote"

        parsed_experience_level = detect_experience_level(
            title=title,
            description=cleaned_description,
        )
        experience_level = provider_experience_hint or parsed_experience_level
        experience_level = _apply_title_override(title=title, experience_level=experience_level)

        employment_type = provider_employment_type or detect_employment_type(cleaned_description)
        summary = provider_summary or extract_summary(cleaned_description)

        return NormalizedJob(
            id=_build_job_id(
                source=source,
                external_id=external_id,
                url=url,
                title=title,
                company=company,
                location=location,
            ),
            title=title,
            company=company,
            location=location or "Unknown",
            remote=remote,
            remote_type=remote_type,
            url=url,
            source=source,
            summary=summary,
            description=cleaned_description,
            responsibilities=responsibilities,
            qualifications=qualifications,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            employment_type=employment_type,
            experience_level=experience_level,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
        )

    except Exception:
        logger.exception("Failed to normalize provider job. source=%s raw_job=%s", source, raw_job)
        return None


def _normalize_existing_job(job: NormalizedJob) -> NormalizedJob | None:
    """Validate and lightly enrich an already-normalized job."""
    title = _safe_str(job.title)
    company = _safe_str(job.company)
    location = _safe_str(job.location)
    url = _safe_str(job.url)
    description = clean_description(job.description or "")

    if not title or not company or not url:
        return None

    if detect_spam_or_scam(
        title=title,
        company=company,
        location=location,
        description=description,
        url=url,
    ):
        return None

    if not should_keep_us_focused_job(
        title=title,
        location=location,
        description=description,
        remote_flag=bool(job.remote),
    ):
        return None

    experience_level = _normalize_experience_hint(job.experience_level) or detect_experience_level(
        title=title,
        description=description,
    )
    experience_level = _apply_title_override(title=title, experience_level=experience_level)

    responsibilities = job.responsibilities or extract_responsibilities(description)
    qualifications = job.qualifications or extract_qualifications(description)

    parsed_required_skills, parsed_preferred_skills = split_required_and_preferred_skills(
        qualifications=qualifications,
        description=description,
    )

    required_skills = job.required_skills or parsed_required_skills
    preferred_skills = job.preferred_skills or parsed_preferred_skills

    salary_min = job.salary_min
    salary_max = job.salary_max
    salary_currency = job.salary_currency

    if salary_min is None and salary_max is None:
        parsed_salary_min, parsed_salary_max, parsed_salary_currency = extract_salary(description)
        salary_min = parsed_salary_min
        salary_max = parsed_salary_max
        salary_currency = salary_currency or parsed_salary_currency

    remote_type = job.remote_type
    if remote_type == "unknown":
        remote_type = detect_remote_type(
            title=title,
            location=location,
            description=description,
        )

    return NormalizedJob(
        id=job.id or _build_job_id(
            source=job.source,
            external_id="",
            url=url,
            title=title,
            company=company,
            location=location,
        ),
        title=title,
        company=company,
        location=location or "Unknown",
        remote=bool(job.remote) or remote_type == "remote",
        remote_type=remote_type,
        url=url,
        source=job.source,
        summary=job.summary or extract_summary(description),
        description=description,
        responsibilities=responsibilities,
        qualifications=qualifications,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        employment_type=job.employment_type or detect_employment_type(description),
        experience_level=experience_level,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
    )


def _build_job_id(
    *,
    source: str,
    external_id: str | None,
    url: str | None,
    title: str | None,
    company: str | None,
    location: str | None,
) -> str:
    """Build a stable job ID for repeated ingestions."""
    raw = "::".join(
        [
            source.strip().lower(),
            (external_id or "").strip(),
            _canonicalize_url(url or ""),
            (title or "").strip().lower(),
            (company or "").strip().lower(),
            (location or "").strip().lower(),
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{source}_{digest}"


def _canonicalize_url(url: str) -> str:
    """Normalize a URL into a stable comparison string."""
    return str(url or "").strip().rstrip("/").lower()


def _safe_str(value: Any) -> str:
    """Return a stripped string representation."""
    if value is None:
        return ""
    return str(value).strip()


def _coerce_bool(value: Any) -> bool:
    """Coerce flexible booleans from provider payloads."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    if isinstance(value, int):
        return value != 0
    return False


def _coerce_int(value: Any) -> int | None:
    """Coerce numeric-looking values into integers."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_string_list(value: Any) -> list[str]:
    """Coerce string-ish lists while preserving order."""
    if not isinstance(value, list):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in value:
        text = _safe_str(item)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)

    return cleaned


def _normalize_remote_type(value: Any) -> str:
    """Normalize remote type values from provider payloads."""
    normalized = _safe_str(value).lower()
    if normalized in {"remote", "hybrid", "onsite"}:
        return normalized
    return "unknown"


def _normalize_experience_hint(value: Any) -> str | None:
    """Normalize a provider experience hint into the shared level vocabulary."""
    normalized = _safe_str(value).lower()
    if not normalized:
        return None
    return _EXPERIENCE_LEVEL_ALIASES.get(normalized)


def _apply_title_override(title: str, experience_level: str) -> str:
    """Apply strong title-based overrides for obvious level wording."""
    normalized_title = _safe_str(title).lower()

    if is_obviously_senior_title(normalized_title):
        return "senior"

    if is_early_career_title(normalized_title):
        # Do not crush entry-level into junior.
        if experience_level in {"senior", "mid-level"}:
            return "junior"
        return "entry-level"

    return experience_level or "unknown"