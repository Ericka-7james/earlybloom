from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.jobs.providers.base import BaseJobProvider

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

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []

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

    def _normalize_job(self, item: dict[str, Any]) -> dict[str, Any] | None:
        title = self._safe_str(item.get("title"))
        company = self._safe_str(item.get("company_name")) or "Unknown Company"
        location = self._safe_str(item.get("location")) or "Unknown"
        url = self._safe_str(item.get("url"))
        external_id = self._safe_str(item.get("slug") or item.get("id"))
        description_html = self._safe_str(item.get("description"))

        if not title or not company or not url:
            return None

        description = self.strip_html(description_html)
        tags = self._coerce_string_list(item.get("tags"))
        remote, remote_type = self.infer_remote_type(title, location, description, " ".join(tags))

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
            "posted_at": self._safe_str(item.get("created_at")) or None,
            "employment_type": None,
            "seniority_hint": self.infer_experience_level(title, description, " ".join(tags)),
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