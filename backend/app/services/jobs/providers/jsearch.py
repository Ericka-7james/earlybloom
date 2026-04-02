from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.jobs import NormalizedJob
from app.services.jobs.providers.base import BaseJobProvider

logger = logging.getLogger(__name__)


class JSearchProvider(BaseJobProvider):
    """Fetch jobs from the JSearch API on RapidAPI.

    This provider is a breadth source. It is useful for broader market coverage
    but should not be treated as the single source of truth because it aggregates
    listings from multiple origins.

    Docs:
        https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    """

    source_name = "jsearch"
    base_url = os.getenv("JSEARCH_BASE_URL", "https://jsearch.p.rapidapi.com/search")

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 6.0,
        max_jobs: int = 100,
        query: str = "software engineer OR software developer OR IT support",
        page: int = 1,
        num_pages: int = 1,
        country: str = "us",
        date_posted: str | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds
        self.max_jobs = max_jobs
        self.query = query
        self.page = max(1, page)
        self.num_pages = max(1, num_pages)
        self.country = country
        self.date_posted = (date_posted or "").strip() or None

    @classmethod
    def from_env(cls) -> "JSearchProvider | None":
        """Build a JSearch provider from application settings."""
        settings = get_settings()

        enabled = str(
            getattr(settings, "JOB_PROVIDER_JSEARCH_ENABLED", True)
        ).strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        api_key = (
            getattr(settings, "JSEARCH_API_KEY", None)
            or os.getenv("RAPIDAPI_KEY", "")
            or os.getenv("JSEARCH_API_KEY", "")
        )
        if not api_key:
            logger.warning("JSearch provider enabled but JSEARCH_API_KEY/RAPIDAPI_KEY is missing.")
            return None

        return cls(
            api_key=api_key,
            timeout_seconds=float(getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)),
            max_jobs=int(getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)),
            query=getattr(
                settings,
                "JOB_PROVIDER_JSEARCH_QUERY",
                "software engineer OR software developer OR IT support",
            ),
            page=int(getattr(settings, "JOB_PROVIDER_JSEARCH_PAGE", 1)),
            num_pages=int(getattr(settings, "JOB_PROVIDER_JSEARCH_NUM_PAGES", 1)),
            country=getattr(settings, "JOB_PROVIDER_JSEARCH_COUNTRY", "us"),
            date_posted=getattr(settings, "JOB_PROVIDER_JSEARCH_DATE_POSTED", None),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from JSearch."""
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        normalized_jobs: list[NormalizedJob] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for page_offset in range(self.num_pages):
                params: dict[str, Any] = {
                    "query": self.query,
                    "page": self.page + page_offset,
                    "num_pages": 1,
                    "country": self.country,
                }
                if self.date_posted:
                    params["date_posted"] = self.date_posted

                try:
                    response = await client.get(self.base_url, headers=headers, params=params)
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as exc:
                    logger.exception(
                        "JSearch fetch failed on page=%s",
                        self.page + page_offset,
                        exc_info=exc,
                    )
                    break

                items = payload.get("data", [])
                if not isinstance(items, list) or not items:
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

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        """Normalize a single JSearch job."""
        title = self._safe_str(item.get("job_title"))
        company = self._safe_str(item.get("employer_name")) or "Unknown Company"
        location = self._build_location(item) or "Unknown"
        url = self._safe_str(
            item.get("job_apply_link")
            or item.get("job_google_link")
            or item.get("job_offer_expiration_datetime_utc")
        )
        external_id = self._safe_str(item.get("job_id"))
        description = self._safe_str(item.get("job_description"))

        if not title or not url:
            return None

        remote, remote_type = self.infer_remote_type(
            title,
            location,
            description,
            self._safe_str(item.get("job_is_remote")),
            self._safe_str(item.get("job_employment_type")),
        )

        responsibilities = self._extract_section_bullets(
            description,
            section_names=("responsibilities", "what you will do", "what you'll do"),
        )
        qualifications = self._extract_section_bullets(
            description,
            section_names=("requirements", "qualifications", "minimum qualifications"),
        )
        preferred_skills = self._extract_section_bullets(
            description,
            section_names=("preferred qualifications", "nice to have", "bonus"),
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
            required_skills=self._extract_skill_hints(description),
            preferred_skills=preferred_skills,
            employment_type=self._safe_str(item.get("job_employment_type")) or None,
            experience_level=self.infer_experience_level(title, description),
        )

    def _build_location(self, item: dict[str, Any]) -> str:
        """Build a readable location string from JSearch location fields."""
        city = self._safe_str(item.get("job_city"))
        state = self._safe_str(item.get("job_state"))
        country = self._safe_str(item.get("job_country"))

        parts = [part for part in [city, state, country] if part]
        if parts:
            return ", ".join(parts)

        raw_location = self._safe_str(item.get("job_location"))
        if raw_location:
            return raw_location

        if bool(item.get("job_is_remote")):
            return "Remote"

        return ""

    def _extract_section_bullets(
        self,
        text: str,
        *,
        section_names: tuple[str, ...],
        max_items: int = 8,
    ) -> list[str]:
        """Extract bullet-like items from common plain-text sections."""
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

    def _extract_skill_hints(self, description: str) -> list[str]:
        """Extract coarse skill hints from plain-text descriptions."""
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
            "linux",
            "azure",
            "gcp",
        ]
        lowered = description.casefold()
        return [skill for skill in skill_bank if skill in lowered][:10]

    def _safe_str(self, value: Any) -> str:
        """Return a stripped string representation for arbitrary values."""
        if value is None:
            return ""
        return str(value).strip()