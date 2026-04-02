from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.jobs import NormalizedJob
from app.services.jobs.providers.base import BaseJobProvider

logger = logging.getLogger(__name__)


class RemotiveProvider(BaseJobProvider):
    """Fetch jobs from the Remotive public API.

    This source is useful as a relatively clean remote-focused provider. It
    should be treated as a trusted Layer 1 source, but not as authoritative as
    USAJOBS for title or seniority truth.

    Docs:
        https://remotive.com/remote-jobs/api
    """

    source_name = "remotive"
    base_url = os.getenv("REMOTIVE_BASE_URL", "https://remotive.com/api/remote-jobs")

    def __init__(
        self,
        *,
        timeout_seconds: float = 6.0,
        max_jobs: int = 100,
        category: str | None = None,
        search: str | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_jobs = max_jobs
        self.category = (category or "").strip() or None
        self.search = (search or "").strip() or None

    @classmethod
    def from_env(cls) -> "RemotiveProvider | None":
        """Build a Remotive provider from application settings."""
        settings = get_settings()
        enabled = str(
            getattr(settings, "JOB_PROVIDER_REMOTIVE_ENABLED", True)
        ).strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        return cls(
            timeout_seconds=float(getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)),
            max_jobs=int(getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)),
            category=getattr(settings, "JOB_PROVIDER_REMOTIVE_CATEGORY", None),
            search=getattr(settings, "JOB_PROVIDER_REMOTIVE_SEARCH", None),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from Remotive."""
        params: dict[str, str] = {}
        if self.category:
            params["category"] = self.category
        if self.search:
            params["search"] = self.search

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:
                logger.exception("Remotive fetch failed", exc_info=exc)
                return []

        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        normalized_jobs: list[NormalizedJob] = []
        for item in jobs[: self.max_jobs]:
            if not isinstance(item, dict):
                continue

            normalized = self._normalize_job(item)
            if normalized is not None:
                normalized_jobs.append(normalized)

        return normalized_jobs

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        """Normalize a single Remotive job."""
        title = self._safe_str(item.get("title"))
        company = self._safe_str(item.get("company_name")) or "Unknown Company"
        location = self._safe_str(
            item.get("candidate_required_location")
            or item.get("location")
            or "Remote"
        )
        url = self._safe_str(item.get("url"))
        external_id = self._safe_str(item.get("id"))
        description_html = self._safe_str(item.get("description"))

        if not title or not url:
            return None

        description = self.strip_html(description_html)
        remote, remote_type = self.infer_remote_type(
            title,
            location,
            description,
            "remote",
        )

        category = self._safe_str(item.get("category"))
        job_type = self._safe_str(item.get("job_type"))
        tags = self._coerce_string_list(item.get("tags"))

        responsibilities = self._extract_section_bullets(
            description_html,
            section_names=("responsibilities", "what you will do", "what you'll do"),
        )
        qualifications = self._extract_section_bullets(
            description_html,
            section_names=("requirements", "qualifications", "what we’re looking for", "what we're looking for"),
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
            employment_type=job_type or None,
            experience_level=self.infer_experience_level(title, description, category, " ".join(tags)),
        )

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
        """Extract coarse skill hints from description and source tags."""
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
            "angular",
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