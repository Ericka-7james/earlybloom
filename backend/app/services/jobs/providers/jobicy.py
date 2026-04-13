from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.jobs import NormalizedJob
from app.services.jobs.providers.base import BaseJobProvider
from app.services.jobs.common.experience_rules import (
    infer_experience_level_from_text,
)
from app.services.jobs.common.role_taxonomy import (
    infer_role_type_from_text,
)
from app.services.jobs.common.skill_hints import (
    extract_skill_hints,
)
from app.services.jobs.common.text_cleaning import (
    normalize_paragraph_text,
    strip_html,
)
from app.services.jobs.common.title_rules import (
    is_obviously_senior_title,
    should_keep_title_for_earlybloom,
)

logger = logging.getLogger(__name__)


class JobicyProvider(BaseJobProvider):
    """Fetch jobs from the Jobicy API."""

    source_name = "jobicy"
    base_url = os.getenv("JOBICY_BASE_URL", "https://jobicy.com/api/v2/remote-jobs")

    def __init__(
        self,
        *,
        timeout_seconds: float = 6.0,
        max_jobs: int = 100,
        pages: int = 2,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_jobs = max_jobs
        self.pages = max(1, pages)

    @classmethod
    def from_env(cls) -> "JobicyProvider | None":
        """Build a Jobicy provider from application settings."""
        settings = get_settings()

        enabled = str(
            getattr(settings, "JOB_PROVIDER_JOBICY_ENABLED", True)
        ).strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        return cls(
            timeout_seconds=float(
                getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)
            ),
            max_jobs=int(
                getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)
            ),
            pages=int(
                getattr(settings, "JOB_PROVIDER_JOBICY_PAGES", 2)
            ),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from Jobicy."""
        normalized_jobs: list[NormalizedJob] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for page in range(1, self.pages + 1):
                try:
                    response = await client.get(
                        self.base_url,
                        params={"page": page},
                    )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as exc:
                    logger.exception("Jobicy fetch failed on page=%s", page, exc_info=exc)
                    break

                items = payload.get("jobs") or payload.get("data") or []
                if not isinstance(items, list) or not items:
                    break

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    normalized = self._normalize_job(item)
                    if normalized is None:
                        continue

                    normalized_jobs.append(normalized)

                    if len(normalized_jobs) >= self.max_jobs:
                        return normalized_jobs[: self.max_jobs]

        return normalized_jobs[: self.max_jobs]

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        """Normalize a single Jobicy record."""
        title = self._safe_str(item.get("jobTitle") or item.get("title"))
        url = self._safe_str(item.get("url"))
        external_id = self._safe_str(item.get("id"))
        company = self._safe_str(item.get("companyName") or item.get("company")) or "Unknown Company"
        location = self._safe_str(item.get("jobGeo") or item.get("location")) or "Remote"
        raw_description = self._safe_str(item.get("jobDescription") or item.get("description"))

        if not title or not url:
            return None

        if is_obviously_senior_title(title):
            return None

        if not should_keep_title_for_earlybloom(title):
            return None

        plain_description = strip_html(raw_description)
        summary = self.summarize(plain_description or title)

        remote, remote_type = self.infer_remote_type(
            title,
            location,
            plain_description,
        )

        role_type = infer_role_type_from_text(
            title=title,
            description=plain_description,
            tags=[],
        )

        experience_level = self._normalize_experience_level(
            infer_experience_level_from_text(
                title=title,
                description=plain_description,
                tags=[],
            )
        )

        combined_skill_text = "\n".join(
            part
            for part in [title, plain_description]
            if part
        )

        job_id = self.build_stable_job_id(
            external_id=external_id,
            url=url,
            title=title,
            company=company,
            location=location,
        )

        return NormalizedJob(
            id=job_id,
            title=title,
            company=company,
            location=location,
            remote=remote,
            remote_type=remote_type,
            url=url,
            source=self.source_name,
            summary=summary,
            description=normalize_paragraph_text(plain_description),
            responsibilities=[],
            qualifications=[],
            required_skills=extract_skill_hints(
                combined_skill_text,
                role_type=role_type,
                limit=12,
            ),
            preferred_skills=[],
            employment_type=None,
            experience_level=experience_level,
            salary_min=None,
            salary_max=None,
            salary_currency="USD",
        )

    def _normalize_experience_level(self, level: str | None) -> str:
        normalized = str(level or "").strip().lower()

        if normalized in {"entry", "entry-level"}:
            return "entry-level"
        if normalized == "junior":
            return "junior"
        if normalized in {"mid", "mid-level", "midlevel"}:
            return "mid-level"
        if normalized == "senior":
            return "senior"
        return "unknown"

    def _safe_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()