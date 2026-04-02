from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.jobs import NormalizedJob
from app.services.jobs.providers.base import BaseJobProvider

logger = logging.getLogger(__name__)


class JobicyProvider(BaseJobProvider):
    """Fetch jobs from the Jobicy remote jobs API.

    This provider is optional. It is useful as a supplemental remote source but
    should sit behind a toggle so it does not complicate the core Layer 1 path.

    Docs:
        https://jobicy.com/api/v2/remote-jobs
    """

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
        """Build a Jobicy provider from application settings."""
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
        normalized_jobs: list[NormalizedJob] = []

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
                        normalized_jobs.append(normalized)

                    if len(normalized_jobs) >= self.max_jobs:
                        return normalized_jobs[: self.max_jobs]

        return normalized_jobs[: self.max_jobs]

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        """Extract job items from varying Jobicy response shapes."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            jobs = payload.get("jobs") or payload.get("posts") or payload.get("data") or []
            if isinstance(jobs, list):
                return [item for item in jobs if isinstance(item, dict)]

        return []

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        """Normalize a single Jobicy job."""
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

        if not title or not url:
            return None

        description = self.strip_html(description_html)
        tags = self._coerce_string_list(item.get("jobTags") or item.get("tags"))
        remote, remote_type = self.infer_remote_type(title, location, description, "remote")

        responsibilities = self._extract_section_bullets(
            description_html,
            section_names=("responsibilities", "what you will do", "what you'll do"),
        )
        qualifications = self._extract_section_bullets(
            description_html,
            section_names=("requirements", "qualifications"),
        )
        preferred_skills = self._extract_section_bullets(
            description_html,
            section_names=("nice to have", "preferred qualifications", "bonus"),
            max_items=6,
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
            summary=self.summarize(description or title),
            description=description,
            responsibilities=responsibilities,
            qualifications=qualifications,
            required_skills=self._extract_skill_hints(description, tags),
            preferred_skills=preferred_skills,
            employment_type=self._safe_str(item.get("jobType")) or None,
            experience_level=self.infer_experience_level(title, description, " ".join(tags)),
        )

    def _extract_company(self, item: dict[str, Any]) -> str:
        """Extract a company name from varying Jobicy fields."""
        company = self._safe_str(item.get("companyName"))
        if company:
            return company

        company_obj = item.get("company")
        if isinstance(company_obj, dict):
            return self._safe_str(company_obj.get("name"))
        if isinstance(company_obj, str):
            return company_obj.strip()

        return ""

    def _extract_section_bullets(
        self,
        text: str,
        *,
        section_names: tuple[str, ...],
        max_items: int = 8,
    ) -> list[str]:
        """Extract bullet-like items from common HTML sections."""
        lowered = text.lower()
        for section_name in section_names:
            marker = section_name.lower()
            index = lowered.find(marker)
            if index == -1:
                continue
            snippet = text[index : index + 1800]
            bullets = self.split_bullets(snippet, max_items=max_items)
            if bullets:
                return bullets
        return []

    def _extract_skill_hints(self, description: str, tags: list[str]) -> list[str]:
        """Extract coarse skill hints from provider text and tags."""
        skill_bank = [
            "python",
            "java",
            "javascript",
            "typescript",
            "react",
            "node",
            "aws",
            "docker",
            "kubernetes",
            "sql",
            "postgres",
            "graphql",
            "rest",
            "fastapi",
            "django",
            "flask",
            "go",
            "rust",
            "c++",
            "next.js",
            "vue",
        ]
        combined = f"{description} {' '.join(tags)}".casefold()
        return [skill for skill in skill_bank if skill in combined][:10]

    def _coerce_string_list(self, value: Any) -> list[str]:
        """Coerce an arbitrary value into a clean list of strings."""
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
        """Return a stripped string representation for arbitrary values."""
        if value is None:
            return ""
        return str(value).strip()