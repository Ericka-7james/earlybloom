from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.jobs.providers.base import BaseJobProvider

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

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []

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

    def _normalize_job(self, item: dict[str, Any]) -> dict[str, Any] | None:
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

        if not title or not company or not url:
            return None

        description = self.strip_html(description_html)
        tags = self._coerce_string_list(item.get("jobTags") or item.get("tags"))
        remote, remote_type = self.infer_remote_type(title, location, description, "remote")

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
            "posted_at": self._safe_str(
                item.get("pubDate") or item.get("published") or item.get("date")
            ) or None,
            "employment_type": self._safe_str(item.get("jobType")) or None,
            "seniority_hint": self.infer_experience_level(title, description, " ".join(tags)),
            "tags": tags,
        }

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