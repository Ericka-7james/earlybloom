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

        if remote_flag is None:
            remote_flag = False

        if not title or not company or not url:
            logger.debug(
                "Skipping job with missing required fields. source=%s title=%s company=%s url=%s",
                source,
                title,
                company,
                url,
            )
            return None

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
            remote_flag=bool(remote_flag),
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
        salary_min, salary_max, salary_currency = extract_salary(cleaned_description)

        remote_type = detect_remote_type(
            title=title,
            location=location,
            description=cleaned_description,
        )
        remote = bool(remote_flag) or remote_type == "remote"

        experience_level = detect_experience_level(
            title=title,
            description=cleaned_description,
        )

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
            experience_level = "senior"
        elif any(
            keyword in normalized_title
            for keyword in [
                " junior ",
                " entry ",
                " associate ",
                " new grad ",
                " graduate ",
            ]
        ):
            experience_level = "junior"

        employment_type = detect_employment_type(cleaned_description)
        summary = extract_summary(cleaned_description)

        return NormalizedJob(
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

    except Exception:
        logger.exception("Failed to normalize provider job. source=%s raw_job=%s", source, raw_job)
        return None