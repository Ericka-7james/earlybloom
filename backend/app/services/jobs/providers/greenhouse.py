from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Iterable

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
    normalize_paragraph_text,
    split_bullets,
    strip_html,
)
from app.services.jobs.common.title_rules import (
    is_obviously_senior_title,
    should_keep_title_for_earlybloom,
)

logger = logging.getLogger(__name__)


class GreenhouseJobBoardProvider(BaseJobProvider):
    """
    Ingest jobs from curated Greenhouse board tokens.

    Notes:
    - Greenhouse Job Board API is board-token based, so coverage depends heavily
      on how many boards you curate.
    - `content=true` returns richer job bodies and exposed metadata.
    """

    source_name = "greenhouse"
    base_url = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(
        self,
        *,
        board_tokens: list[str],
        timeout_seconds: float = 6.0,
        max_jobs_per_board: int = 100,
        include_departments: list[str] | None = None,
        exclude_departments: list[str] | None = None,
        include_offices: list[str] | None = None,
        exclude_offices: list[str] | None = None,
    ) -> None:
        self.board_tokens = [token.strip() for token in board_tokens if token.strip()]
        self.timeout_seconds = timeout_seconds
        self.max_jobs_per_board = max(1, max_jobs_per_board)
        self.include_departments = self._normalize_filters(include_departments)
        self.exclude_departments = self._normalize_filters(exclude_departments)
        self.include_offices = self._normalize_filters(include_offices)
        self.exclude_offices = self._normalize_filters(exclude_offices)

    @classmethod
    def from_env(cls) -> "GreenhouseJobBoardProvider | None":
        settings = get_settings()

        print(
            "[greenhouse-from-env]",
            {
                "enabled": getattr(settings, "JOB_PROVIDER_GREENHOUSE_ENABLED", None),
                "tokens": getattr(settings, "JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", None),
            },
        )

        enabled = str(
            getattr(settings, "JOB_PROVIDER_GREENHOUSE_ENABLED", False)
        ).strip().lower()
        if enabled not in {"1", "true", "yes", "on"}:
            return None

        raw_tokens = getattr(settings, "JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", "") or ""
        board_tokens = [token.strip() for token in raw_tokens.split(",") if token.strip()]
        if not board_tokens:
            logger.warning(
                "Greenhouse provider enabled but JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS is empty."
            )
            return None

        return cls(
            board_tokens=board_tokens,
            timeout_seconds=float(getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)),
            max_jobs_per_board=int(
                getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)
            ),
            include_departments=cls._split_csv(
                getattr(settings, "JOB_PROVIDER_GREENHOUSE_INCLUDE_DEPARTMENTS", "")
            ),
            exclude_departments=cls._split_csv(
                getattr(settings, "JOB_PROVIDER_GREENHOUSE_EXCLUDE_DEPARTMENTS", "")
            ),
            include_offices=cls._split_csv(
                getattr(settings, "JOB_PROVIDER_GREENHOUSE_INCLUDE_OFFICES", "")
            ),
            exclude_offices=cls._split_csv(
                getattr(settings, "JOB_PROVIDER_GREENHOUSE_EXCLUDE_OFFICES", "")
            ),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        if not self.board_tokens:
            return []

        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            limits=limits,
            follow_redirects=True,
        ) as client:
            tasks = [self._fetch_board_jobs(client, token) for token in self.board_tokens]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        jobs: list[NormalizedJob] = []
        seen_ids: set[str] = set()

        for token, result in zip(self.board_tokens, results):
            if isinstance(result, Exception):
                logger.exception(
                    "Greenhouse board fetch failed for token=%s",
                    token,
                    exc_info=result,
                )
                continue

            for job in result:
                if job.id in seen_ids:
                    continue
                seen_ids.add(job.id)
                jobs.append(job)

        return jobs

    async def _fetch_board_jobs(
        self,
        client: httpx.AsyncClient,
        board_token: str,
    ) -> list[NormalizedJob]:
        url = f"{self.base_url}/{board_token}/jobs"
        params = {"content": "true"}

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []  # silently skip invalid boards
            raise

        payload = response.json()
        raw_jobs = payload.get("jobs", [])
        if not isinstance(raw_jobs, list):
            return []

        total_reported = (payload.get("meta") or {}).get("total")
        logger.info(
            "Greenhouse board=%s returned %s jobs (meta.total=%s)",
            board_token,
            len(raw_jobs),
            total_reported,
        )

        normalized: list[NormalizedJob] = []
        kept = 0

        for item in raw_jobs:
            if not isinstance(item, dict):
                continue

            if kept >= self.max_jobs_per_board:
                break

            if not self._passes_board_filters(item):
                continue

            job = self._normalize_job(item, board_token=board_token)
            if job is None:
                continue

            normalized.append(job)
            kept += 1

        return normalized

    def _normalize_job(
        self,
        item: dict[str, Any],
        *,
        board_token: str,
    ) -> NormalizedJob | None:
        title = self._safe_str(item.get("title"))
        absolute_url = self._safe_str(item.get("absolute_url"))
        external_id = self._safe_str(item.get("id"))
        internal_job_id = self._safe_str(item.get("internal_job_id"))
        content_html = self._safe_str(item.get("content"))
        updated_at = self._safe_str(item.get("updated_at"))
        requisition_id = self._safe_str(item.get("requisition_id"))

        if not title or not absolute_url:
            return None

        if is_obviously_senior_title(title):
            return None

        if not should_keep_title_for_earlybloom(title):
            return None

        metadata = item.get("metadata") or []
        if not isinstance(metadata, list):
            metadata = []

        description = strip_html(content_html)
        location_name = self._extract_location(item) or "Unknown"
        company_name = self._extract_company_name(item, board_token=board_token)
        tags = self._build_tags(item, metadata)

        remote, remote_type = self.infer_remote_type(
            title,
            location_name,
            description,
            " ".join(tags),
            self._safe_str(item.get("location")),
        )

        summary = self.summarize(description or title)

        responsibilities = self._extract_section_bullets(
            description,
            section_names=(
                "responsibilities",
                "what you'll do",
                "what you will do",
                "in this role you will",
                "about the role",
            ),
        )
        qualifications = self._extract_section_bullets(
            description,
            section_names=(
                "qualifications",
                "requirements",
                "what we're looking for",
                "you should have",
                "who you are",
            ),
        )
        preferred_skills = self._extract_section_bullets(
            description,
            section_names=(
                "nice to have",
                "preferred qualifications",
                "bonus",
                "bonus points",
            ),
            max_items=6,
        )

        employment_type = self.first_non_empty(
            [
                self._find_metadata_value(metadata, "employment type"),
                self._find_metadata_value(metadata, "job type"),
                self._find_metadata_value(metadata, "type"),
                self._find_metadata_value(metadata, "commitment"),
            ],
            default="",
        ) or None

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
                "\n".join(responsibilities),
                "\n".join(qualifications),
                "\n".join(preferred_skills),
                " ".join(tags),
                updated_at,
                requisition_id,
            ]
            if part
        )

        salary_min, salary_max, salary_currency = self._extract_salary_fields(
            metadata=metadata,
            description=description,
        )

        job_id = self.build_stable_job_id(
            external_id=external_id or internal_job_id,
            url=absolute_url,
            title=title,
            company=company_name,
            location=location_name,
        )

        return NormalizedJob(
            id=job_id,
            title=title,
            company=company_name,
            location=location_name,
            remote=remote,
            remote_type=remote_type,
            url=absolute_url,
            source=self.source_name,
            summary=summary,
            description=description,
            responsibilities=responsibilities,
            qualifications=qualifications,
            required_skills=extract_skill_hints(
                combined_skill_text,
                role_type=role_type,
                limit=12,
            ),
            preferred_skills=preferred_skills[:8],
            employment_type=employment_type,
            experience_level=experience_level,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
        )

    def _passes_board_filters(self, item: dict[str, Any]) -> bool:
        offices = self._extract_office_names(item)
        departments = self._extract_department_names(item)

        if self.include_offices and not self._matches_any(offices, self.include_offices):
            return False
        if self.exclude_offices and self._matches_any(offices, self.exclude_offices):
            return False

        if self.include_departments and not self._matches_any(
            departments, self.include_departments
        ):
            return False
        if self.exclude_departments and self._matches_any(
            departments, self.exclude_departments
        ):
            return False

        return True

    def _extract_company_name(self, item: dict[str, Any], *, board_token: str) -> str:
        metadata = item.get("metadata") or []
        if isinstance(metadata, list):
            for key in ("company", "organization", "brand"):
                value = self._find_metadata_value(metadata, key)
                if value:
                    return value

        absolute_url = self._safe_str(item.get("absolute_url"))
        if absolute_url:
            match = re.search(r"boards(?:-api)?\.greenhouse\.io/(?:[^/]+/)?([^/]+)/jobs", absolute_url)
            if match:
                token = match.group(1).strip()
                if token:
                    return self._humanize_token(token)

        return self._humanize_token(board_token) or "Unknown Company"

    def _build_tags(
        self,
        item: dict[str, Any],
        metadata: list[dict[str, Any]],
    ) -> list[str]:
        tags: list[str] = []

        tags.extend(self._metadata_values(metadata))
        tags.extend(self._extract_office_names(item))
        tags.extend(self._extract_department_names(item))

        deduped: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            cleaned = self._safe_str(tag)
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(cleaned)

        return deduped

    def _extract_location(self, item: dict[str, Any]) -> str:
        location = item.get("location") or {}
        if isinstance(location, dict):
            return self._safe_str(location.get("name"))
        return self._safe_str(location)

    def _extract_office_names(self, item: dict[str, Any]) -> list[str]:
        offices = item.get("offices") or []
        names: list[str] = []

        if isinstance(offices, list):
            for office in offices:
                if not isinstance(office, dict):
                    continue
                name = self._safe_str(office.get("name"))
                location = self._safe_str(office.get("location"))
                if name:
                    names.append(name)
                if location and location.casefold() != name.casefold():
                    names.append(location)

        location_name = self._extract_location(item)
        if location_name:
            names.append(location_name)

        return self._dedupe_strings(names)

    def _extract_department_names(self, item: dict[str, Any]) -> list[str]:
        departments = item.get("departments") or []
        names: list[str] = []

        if isinstance(departments, list):
            for dept in departments:
                if not isinstance(dept, dict):
                    continue
                name = self._safe_str(dept.get("name"))
                if name:
                    names.append(name)

                parent = dept.get("parent_id")
                if parent:
                    names.append(str(parent))

        return self._dedupe_strings(names)

    def _extract_salary_fields(
        self,
        *,
        metadata: list[dict[str, Any]],
        description: str,
    ) -> tuple[int | None, int | None, str | None]:
        candidate_text = "\n".join(
            [
                description,
                self._find_metadata_value(metadata, "salary"),
                self._find_metadata_value(metadata, "salary range"),
                self._find_metadata_value(metadata, "compensation"),
                self._find_metadata_value(metadata, "pay range"),
            ]
        ).strip()

        if not candidate_text:
            return None, None, None

        currency = "USD" if "$" in candidate_text or "usd" in candidate_text.lower() else None

        match = re.search(
            r"\$?\s*([0-9]{2,3}(?:,[0-9]{3})+|[0-9]{2,3}k)\s*(?:-|to)\s*\$?\s*([0-9]{2,3}(?:,[0-9]{3})+|[0-9]{2,3}k)",
            candidate_text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None, None, currency

        return (
            self._parse_salary_value(match.group(1)),
            self._parse_salary_value(match.group(2)),
            currency,
        )

    def _parse_salary_value(self, value: str) -> int | None:
        raw = value.strip().lower().replace(",", "")
        if raw.endswith("k"):
            try:
                return int(float(raw[:-1]) * 1000)
            except ValueError:
                return None
        try:
            return int(float(raw))
        except ValueError:
            return None

    def _extract_section_bullets(
        self,
        text: str,
        *,
        section_names: tuple[str, ...],
        max_items: int = 8,
    ) -> list[str]:
        if not text:
            return []

        normalized = normalize_paragraph_text(text)
        lowered = normalized.lower()

        section_index = -1
        matched_section = ""

        for section in section_names:
            pattern = f"{section.lower()}:"
            idx = lowered.find(pattern)
            if idx != -1:
                section_index = idx
                matched_section = section
                break

            idx = lowered.find(section.lower())
            if idx != -1:
                section_index = idx
                matched_section = section
                break

        if section_index == -1:
            return []

        remainder = normalized[section_index + len(matched_section):]
        next_header = re.search(r"\n[A-Z][A-Za-z0-9 &'/,\-\(\)]+:\n", remainder)
        if next_header:
            remainder = remainder[: next_header.start()]

        return split_bullets(remainder[:2000], max_items=max_items)

    def _find_metadata_value(self, metadata: list[dict[str, Any]], key: str) -> str:
        target = key.casefold()

        for item in metadata:
            if not isinstance(item, dict):
                continue
            name = self._safe_str(item.get("name")).casefold()
            if name == target:
                return self._safe_str(item.get("value"))

        return ""

    def _metadata_values(self, metadata: list[dict[str, Any]]) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()

        for item in metadata:
            if not isinstance(item, dict):
                continue

            name = self._safe_str(item.get("name"))
            value = self._safe_str(item.get("value"))
            if not value:
                continue

            combined = f"{name}: {value}" if name else value
            key = combined.casefold()
            if key in seen:
                continue

            seen.add(key)
            values.append(combined)

        return values

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

    @staticmethod
    def _split_csv(raw: str | None) -> list[str]:
        if not raw:
            return []
        return [part.strip() for part in raw.split(",") if part.strip()]

    @staticmethod
    def _normalize_filters(values: list[str] | None) -> list[str]:
        return [v.casefold().strip() for v in (values or []) if v and v.strip()]

    @staticmethod
    def _matches_any(candidates: Iterable[str], filters: list[str]) -> bool:
        lowered = [c.casefold().strip() for c in candidates if c and c.strip()]
        for candidate in lowered:
            for filter_value in filters:
                if filter_value in candidate:
                    return True
        return False

    @staticmethod
    def _humanize_token(token: str) -> str:
        cleaned = token.replace("-", " ").replace("_", " ").strip()
        if not cleaned:
            return ""
        return " ".join(part.capitalize() for part in cleaned.split())

    @staticmethod
    def _dedupe_strings(values: Iterable[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = str(value).strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(cleaned)

        return deduped

    def _safe_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()