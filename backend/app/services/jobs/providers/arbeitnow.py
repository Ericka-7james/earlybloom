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
    strip_html,
)
from app.services.jobs.common.title_rules import (
    is_obviously_senior_title,
    should_keep_title_for_earlybloom,
)

logger = logging.getLogger(__name__)


class ArbeitNowProvider(BaseJobProvider):
    """Fetch jobs from the ArbeitNow public API."""

    source_name = "arbeitnow"
    base_url = os.getenv("ARBEITNOW_BASE_URL", "https://www.arbeitnow.com/api/job-board-api")

    def __init__(
        self,
        *,
        timeout_seconds: float = 6.0,
        max_jobs: int = 100,
        pages: int = 2,
        remote_only: bool = False,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_jobs = max_jobs
        self.pages = max(1, pages)
        self.remote_only = remote_only

    @classmethod
    def from_env(cls) -> "ArbeitNowProvider | None":
        settings = get_settings()
        enabled = str(
            getattr(settings, "JOB_PROVIDER_ARBEITNOW_ENABLED", True)
        ).strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        return cls(
            timeout_seconds=float(getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)),
            max_jobs=int(getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)),
            pages=int(getattr(settings, "JOB_PROVIDER_ARBEITNOW_PAGES", 2)),
            remote_only=bool(getattr(settings, "JOB_PROVIDER_ARBEITNOW_REMOTE_ONLY", False)),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from ArbeitNow."""
        jobs: list[NormalizedJob] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for page in range(1, self.pages + 1):
                params: dict[str, Any] = {"page": page}
                if self.remote_only:
                    params["remote"] = "true"

                try:
                    response = await client.get(self.base_url, params=params)
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as exc:
                    logger.exception("ArbeitNow fetch failed on page=%s", page, exc_info=exc)
                    break

                items = payload.get("data", [])
                if not isinstance(items, list) or not items:
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

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        title = self._safe_str(item.get("title"))
        company = self._safe_str(item.get("company_name")) or "Unknown Company"
        location = self._safe_str(item.get("location")) or "Unknown"
        url = self._safe_str(item.get("url"))
        external_id = self._safe_str(item.get("slug") or item.get("id"))
        description_html = self._safe_str(item.get("description"))
        tags = self._coerce_string_list(item.get("tags"))

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
            employment_type=None,
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