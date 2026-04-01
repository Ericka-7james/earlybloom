"""Shared normalization pipeline for provider job payloads."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.schemas.jobs import NormalizedJob
from app.services.jobs.cleaning import normalize_whitespace, remove_noise_lines, strip_html
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
from app.services.jobs.us_filters import should_keep_us_focused_job

logger = logging.getLogger(__name__)


def _build_job_id(source: str, url: str | None, title: str | None, company: str | None) -> str:
    """Build a stable job id for deduplication across repeated ingestions."""
    raw = f"{source}|{url or ''}|{title or ''}|{company or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def normalize_provider_job(raw_job: dict[str, Any], source: str) -> NormalizedJob | None:
    """Normalize a raw provider payload into the shared shape.

    This function is intentionally forgiving because providers often vary in
    field names and completeness.
    """
    try:
        title = (raw_job.get("title") or raw_job.get("job_title") or "").strip()
        company = (raw_job.get("company") or raw_job.get("company_name") or "").strip()
        location = (raw_job.get("location") or raw_job.get("candidate_required_location") or "").strip()
        url = (raw_job.get("url") or raw_job.get("job_url") or raw_job.get("apply_url") or "").strip()

        raw_description = (
            raw_job.get("description")
            or raw_job.get("job_description")
            or raw_job.get("content")
            or raw_job.get("body")
            or ""
        )

        remote_flag = raw_job.get("remote")
        if isinstance(remote_flag, str):
            remote_flag = remote_flag.lower() in {"true", "1", "yes"}

        cleaned_description = strip_html(raw_description)
        cleaned_description = remove_noise_lines(cleaned_description)
        cleaned_description = normalize_whitespace(cleaned_description)

        if not title or not company or not url:
            logger.debug(
                "Skipping job with missing required fields. source=%s title=%s company=%s url=%s",
                source,
                title,
                company,
                url,
            )
            return None

        if not should_keep_us_focused_job(
            location=location,
            description=cleaned_description,
            remote_flag=bool(remote_flag),
        ):
            return None

        responsibilities = extract_responsibilities(cleaned_description)
        qualifications = extract_qualifications(cleaned_description)
        required_skills, preferred_skills = split_required_and_preferred_skills(
            qualifications=qualifications,
            description=cleaned_description,
        )
        salary_min, salary_max, salary_currency = extract_salary(cleaned_description)

        remote_type = detect_remote_type(
            title=title,
            location=location,
            description=cleaned_description,
        )
        remote = remote_type == "remote" or bool(remote_flag)
        experience_level = detect_experience_level(
            title=title,
            description=cleaned_description,
        )
        employment_type = detect_employment_type(cleaned_description)
        summary = extract_summary(cleaned_description)

        normalized = NormalizedJob(
            id=_build_job_id(source=source, url=url, title=title, company=company),
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
            salary_currency=salary_currency or "USD",
        )

        return normalized

    except Exception:
        logger.exception("Failed to normalize provider job. source=%s raw_job=%s", source, raw_job)
        return None