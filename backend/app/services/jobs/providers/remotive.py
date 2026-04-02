from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.jobs.providers.base import BaseJobProvider

logger = logging.getLogger(__name__)


class RemotiveProvider(BaseJobProvider):
    """Fetch jobs from the Remotive public API."""

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

    async def fetch_jobs(self) -> list[dict[str, Any]]:
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

        items = payload.get("jobs", [])
        if not isinstance(items, list):
            return []

        jobs: list[dict[str, Any]] = []
        for item in items[: self.max_jobs]:
            if not isinstance(item, dict):
                continue

            normalized = self._normalize_job(item)
            if normalized is not None:
                jobs.append(normalized)

        return jobs

    def _normalize_job(self, item: dict[str, Any]) -> dict[str, Any] | None:
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

        if not title or not company or not url:
            return None

        description = self.strip_html(description_html)
        remote, remote_type = self.infer_remote_type(title, location, description, "remote")
        category = self._safe_str(item.get("category"))
        job_type = self._safe_str(item.get("job_type"))
        tags = self._coerce_string_list(item.get("tags"))

        return {
            "source": self.source_name,
            "external_id": external_id or self.build_stable_job_id(
                external_id=external_id,
                url=url,
                title=title,
                company=company,
                location=location,
            ),
            "title": title,
            "company": company,
            "location": location,
            "remote": remote,
            "remote_type": remote_type,
            "url": url,
            "salary_min": None,
            "salary_max": None,
            "currency": None,
            "description": description_html or description,
            "summary": self.summarize(description or title),
            "posted_at": self._safe_str(item.get("publication_date")) or None,
            "employment_type": job_type or None,
            "seniority_hint": self.infer_experience_level(title, description, category, " ".join(tags)),
            "tags": tags,
        }

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