from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.jobs import NormalizedJob
from app.services.jobs.providers.base import BaseJobProvider
from app.services.jobs.providers.common.experience_rules import (
    infer_experience_level_from_text,
)
from app.services.jobs.providers.common.role_taxonomy import (
    infer_role_type_from_text,
)
from app.services.jobs.providers.common.skill_hints import (
    extract_skill_hints,
)
from app.services.jobs.providers.common.text_cleaning import (
    strip_html,
)
from app.services.jobs.providers.common.title_rules import (
    is_obviously_senior_title,
    should_keep_title_for_earlybloom,
)

logger = logging.getLogger(__name__)


class JobicyProvider(BaseJobProvider):
    """Fetch jobs from the Jobicy remote jobs API."""

    source_name = "jobicy"
    base_url = os.getenv("JOBICY_BASE_URL", "https://jobicy.com/api/v2/remote-jobs")

    def __init__(
        self,
        *,
        timeout_seconds: float = 6.0,
        max_jobs: int = 100,
        pages: int = 1,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_jobs = max_jobs
        self.pages = max(1, pages)

    @classmethod
    def from_env(cls) -> "JobicyProvider | None":
        settings = get_settings()
        enabled = str(
            getattr(settings, "JOB_PROVIDER_JOBICY_ENABLED", False)
        ).strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        return cls(
            timeout_seconds=float(getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)),
            max_jobs=int(getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)),
            pages=int(getattr(settings, "JOB_PROVIDER_JOBICY_PAGES", 1)),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from Jobicy."""
        jobs: list[NormalizedJob] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for page in range(1, self.pages + 1):
                try:
                    response = await client.get(self.base_url, params={"page": page})
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as exc:
                    logger.exception("Jobicy fetch failed on page=%s", page, exc_info=exc)
                    break

                items = self._extract_items(payload)
                if not items:
                    break

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    normalized = self._normalize_job(item)
                    if normalized is not None:
                        jobs.append(normalized)

                    if len(jobs) >= self.max_jobs:
                        return jobs[: self.max_jobs]

        return jobs[: self.max_jobs]

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            jobs = payload.get("jobs") or payload.get("posts") or payload.get("data") or []
            if isinstance(jobs, list):
                return [item for item in jobs if isinstance(item, dict)]

        return []

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        title = self._safe_str(item.get("jobTitle") or item.get("title") or item.get("name"))
        company = self._extract_company(item) or "Unknown Company"
        location = self._safe_str(
            item.get("jobGeo")
            or item.get("location")
            or item.get("candidate_required_location")
            or "Remote"
        )
        url = self._safe_str(item.get("url") or item.get("jobUrl") or item.get("link"))
        external_id = self._safe_str(item.get("id") or item.get("slug"))
        description_html = self._safe_str(
            item.get("jobDescription")
            or item.get("description")
            or item.get("content")
        )
        tags = self._coerce_string_list(item.get("jobTags") or item.get("tags"))
        employment_type = self._safe_str(item.get("jobType")) or None

        if not title or not company or not url:
            return None

        if is_obviously_senior_title(title):
            return None

        if not should_keep_title_for_earlybloom(title):
            return None

        description = strip_html(description_html)
        summary = self.summarize(description or title)

        remote, remote_type = self.infer_remote_type(
            title,
            location,
            description,
            "remote",
            employment_type or "",
            " ".join(tags),
        )

        role_type = infer_role_type_from_text(
            title=title,
            description=description,
            tags=tags,
        )

        experience_level = self._normalize_experience_level(
            infer_experience_level_from_text(
                title=title,
                description=description,
                tags=tags,
            )
        )

        combined_skill_text = "\n".join(
            part
            for part in [
                title,
                description,
                employment_type or "",
                " ".join(tags),
            ]
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
            description=description,
            responsibilities=[],
            qualifications=[],
            required_skills=extract_skill_hints(
                combined_skill_text,
                role_type=role_type,
                limit=12,
            ),
            preferred_skills=tags[:8],
            employment_type=employment_type,
            experience_level=experience_level,
            salary_min=None,
            salary_max=None,
            salary_currency=None,
        )

    def _normalize_experience_level(self, level: str | None) -> str:
        """Map helper output into the schema's allowed enum values."""
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

    def _extract_company(self, item: dict[str, Any]) -> str:
        company = self._safe_str(item.get("companyName"))
        if company:
            return company

        company_obj = item.get("company")
        if isinstance(company_obj, dict):
            return self._safe_str(company_obj.get("name"))
        if isinstance(company_obj, str):
            return company_obj.strip()

        return ""

    def _coerce_string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        cleaned: list[str] = []
        seen: set[str] = set()

        for item in value:
            text = self._safe_str(item)
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)

        return cleaned

    def _safe_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()