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


class JSearchProvider(BaseJobProvider):
    """Fetch jobs from the JSearch API on RapidAPI."""

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

        jobs: list[NormalizedJob] = []

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
                        jobs.append(normalized)

                    if len(jobs) >= self.max_jobs:
                        return jobs[: self.max_jobs]

        return jobs[: self.max_jobs]

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        title = self._safe_str(item.get("job_title"))
        company = self._safe_str(item.get("employer_name")) or "Unknown Company"
        location = self._build_location(item) or "Unknown"
        url = self._safe_str(item.get("job_apply_link") or item.get("job_google_link"))
        external_id = self._safe_str(item.get("job_id"))
        description_raw = self._safe_str(item.get("job_description"))
        employment_type = self._safe_str(item.get("job_employment_type")) or None

        if not title or not company or not url:
            return None

        if is_obviously_senior_title(title):
            return None

        if not should_keep_title_for_earlybloom(title):
            return None

        description = strip_html(description_raw)
        summary = self.summarize(description or title)

        remote, remote_type = self.infer_remote_type(
            title,
            location,
            description,
            self._normalize_remote_hint(item.get("job_is_remote")),
            self._safe_str(item.get("job_location")),
            employment_type or "",
        )

        tags = self._coerce_string_list(
            [
                item.get("job_employment_type"),
                item.get("job_publisher"),
                item.get("job_city"),
                item.get("job_state"),
                item.get("job_country"),
                item.get("job_location"),
                item.get("employer_name"),
            ]
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

        salary_min, salary_max = self._extract_salary_range(item)

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
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=self._extract_salary_currency(item),
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

    def _build_location(self, item: dict[str, Any]) -> str:
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

    def _extract_salary_range(self, item: dict[str, Any]) -> tuple[int | None, int | None]:
        min_value = item.get("job_min_salary") or item.get("job_salary_min")
        max_value = item.get("job_max_salary") or item.get("job_salary_max")

        return self._coerce_int(min_value), self._coerce_int(max_value)

    def _extract_salary_currency(self, item: dict[str, Any]) -> str | None:
        currency = self._safe_str(
            item.get("job_salary_currency")
            or item.get("job_currency")
        )
        return currency or None

    def _normalize_remote_hint(self, value: Any) -> str:
        if value is True:
            return "remote"
        if value is False or value is None:
            return ""
        text = self._safe_str(value).lower()
        if text in {"true", "1", "yes", "remote"}:
            return "remote"
        return text

    def _coerce_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _coerce_string_list(self, values: list[Any]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for value in values:
            text = self._safe_str(value)
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