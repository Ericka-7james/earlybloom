from __future__ import annotations

import logging
import os
import re
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


class RemoteOKProvider(BaseJobProvider):
    """Fetch jobs from the RemoteOK public API.

    RemoteOK remains lower-trust for EarlyBloom due to inconsistent payload quality,
    but this provider keeps it normalized and staging-safe when enabled.
    """

    source_name = "remoteok"
    base_url = os.getenv("REMOTEOK_BASE_URL", "https://remoteok.com/api")

    def __init__(
        self,
        *,
        timeout_seconds: float = 6.0,
        max_jobs: int = 100,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_jobs = max_jobs

    @classmethod
    def from_env(cls) -> "RemoteOKProvider | None":
        settings = get_settings()
        enabled = str(
            getattr(settings, "JOB_PROVIDER_REMOTEOK_ENABLED", False)
        ).strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        return cls(
            timeout_seconds=float(getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)),
            max_jobs=int(getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from RemoteOK."""
        headers = {"User-Agent": "EarlyBloom/1.0"}
        jobs: list[NormalizedJob] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.get(self.base_url, headers=headers)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:
                logger.exception("RemoteOK fetch failed", exc_info=exc)
                return []

        items = self._extract_items(payload)
        if not items:
            return []

        for item in items:
            normalized = self._normalize_job(item)
            if normalized is not None:
                jobs.append(normalized)

            if len(jobs) >= self.max_jobs:
                return jobs[: self.max_jobs]

        return jobs[: self.max_jobs]

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or len(payload) <= 1:
            return []

        # RemoteOK commonly returns metadata as first item.
        return [item for item in payload[1:] if isinstance(item, dict)]

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        title = self._clean_remoteok_text(item.get("position"))
        company = self._clean_remoteok_text(item.get("company")) or "Unknown Company"
        location = self._clean_remoteok_text(item.get("location")) or "Remote"
        url = self._safe_str(item.get("url"))
        external_id = self._safe_str(item.get("id"))
        raw_description = self._clean_remoteok_text(item.get("description"))
        cleaned_description = strip_html(raw_description)

        tags = self._coerce_string_list(item.get("tags"))
        employment_type = None

        if not title or not company or not url:
            return None

        if is_obviously_senior_title(title):
            return None

        if not should_keep_title_for_earlybloom(title):
            return None

        remote, remote_type = self.infer_remote_type(
            title,
            location,
            cleaned_description,
            "remote",
            " ".join(tags),
        )

        role_type = infer_role_type_from_text(
            title=title,
            description=cleaned_description,
            tags=tags,
        )

        experience_level = self._normalize_experience_level(
            infer_experience_level_from_text(
                title=title,
                description=cleaned_description,
                tags=tags,
            )
        )

        combined_skill_text = "\n".join(
            part
            for part in [
                title,
                cleaned_description,
                " ".join(tags),
            ]
            if part
        )

        salary_min = self._extract_salary_min(item)
        salary_max = self._extract_salary_max(item)
        salary_currency = "USD" if salary_min is not None or salary_max is not None else None

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
            summary=self.summarize(cleaned_description or title),
            description=cleaned_description,
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
            salary_currency=salary_currency,
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

    def _extract_salary_min(self, item: dict[str, Any]) -> int | None:
        return self._coerce_int(item.get("salary_min"))

    def _extract_salary_max(self, item: dict[str, Any]) -> int | None:
        return self._coerce_int(item.get("salary_max"))

    def _coerce_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _coerce_string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        cleaned: list[str] = []
        seen: set[str] = set()

        for item in value:
            text = self._clean_remoteok_text(item)
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)

        return cleaned

    def _clean_remoteok_text(self, value: Any) -> str:
        """Normalize common RemoteOK encoding junk before shared cleaning."""
        text = str(value or "").strip()
        if not text:
            return ""

        replacements = {
            "\u00a0": " ",
            "&nbsp;": " ",
            "Â": "",
            "â": "'",
            "â": '"',
            "â": '"',
            "â": "-",
            "â": "-",
            "â¢": "•",
            "â¦": "...",
        }

        for bad, good in replacements.items():
            text = text.replace(bad, good)

        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _safe_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()
