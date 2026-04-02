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


def normalize_provider_job(raw_job: dict[str, Any], source: str) -> NormalizedJob | None:
    """Normalize a provider-normalized raw job payload into the shared schema.

    Args:
        raw_job: Provider-normalized raw job payload.
        source: Provider source name.

    Returns:
        A fully normalized job or None when the record should be dropped.
    """
    try:
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
        provider_salary_currency = _safe_str(raw_job.get("currency") or raw_job.get("salary_currency")) or None

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

        responsibilities = extract_responsibilities(cleaned_description)
        qualifications = extract_qualifications(cleaned_description)
        required_skills, preferred_skills = split_required_and_preferred_skills(
            qualifications=qualifications,
            description=cleaned_description,
        )

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
        remote_type = provider_remote_type if provider_remote_type != "unknown" else parsed_remote_type
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
    normalized_title = f" {title.lower()} "

    if any(
        keyword in normalized_title
        for keyword in [
            " chief ",
            " ciso ",
            " cto ",
            " cio ",
            " director ",
            " head ",
            " principal ",
            " staff ",
            " senior ",
            " sr ",
            " lead ",
            " manager ",
            " architect ",
        ]
    ):
        return "senior"

    if any(
        keyword in normalized_title
        for keyword in [
            " junior ",
            " entry ",
            " associate ",
            " new grad ",
            " graduate ",
        ]
    ):
        return "junior"

    return experience_level