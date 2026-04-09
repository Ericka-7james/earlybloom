from __future__ import annotations

import logging
import os
import re
from typing import Any, Iterable

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
    normalize_paragraph_text,
    split_bullets,
    strip_html,
)
from app.services.jobs.providers.common.title_rules import (
    is_obviously_senior_title,
    should_keep_title_for_earlybloom,
)

logger = logging.getLogger(__name__)


class USAJOBSProvider(BaseJobProvider):
    """Fetch jobs from the USAJOBS Search API."""

    source_name = "usajobs"
    base_url = os.getenv("USAJOBS_BASE_URL", "https://data.usajobs.gov/api/search")

    def __init__(
        self,
        *,
        api_key: str,
        user_agent: str,
        timeout_seconds: float = 6.0,
        max_jobs: int = 100,
        results_per_page: int = 50,
        job_category_code: str | None = None,
        position_offer_type_code: str | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.user_agent = user_agent.strip()
        self.timeout_seconds = timeout_seconds
        self.max_jobs = max_jobs
        self.results_per_page = max(1, min(results_per_page, 500))
        self.job_category_code = (job_category_code or "").strip() or None
        self.position_offer_type_code = (position_offer_type_code or "").strip() or None

    @classmethod
    def from_env(cls) -> "USAJOBSProvider | None":
        """Build a USAJOBS provider from application settings."""
        settings = get_settings()

        api_key = getattr(settings, "USAJOBS_API_KEY", "") or ""
        user_agent = getattr(settings, "USAJOBS_USER_AGENT", "") or ""
        enabled = str(
            getattr(settings, "JOB_PROVIDER_USAJOBS_ENABLED", True)
        ).strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        if not api_key or not user_agent:
            logger.warning(
                "USAJOBS provider enabled but USAJOBS_API_KEY or USAJOBS_USER_AGENT is missing."
            )
            return None

        return cls(
            api_key=api_key,
            user_agent=user_agent,
            timeout_seconds=float(getattr(settings, "JOB_PROVIDER_TIMEOUT_SECONDS", 6.0)),
            max_jobs=int(getattr(settings, "JOB_PROVIDER_MAX_JOBS_PER_SOURCE", 100)),
            results_per_page=int(getattr(settings, "USAJOBS_RESULTS_PER_PAGE", 50)),
            job_category_code=getattr(settings, "USAJOBS_JOB_CATEGORY_CODE", None),
            position_offer_type_code=getattr(
                settings, "USAJOBS_POSITION_OFFER_TYPE_CODE", None
            ),
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from USAJOBS."""
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": self.user_agent,
            "Authorization-Key": self.api_key,
        }

        pages_to_fetch = max(
            1,
            (self.max_jobs + self.results_per_page - 1) // self.results_per_page,
        )
        normalized_jobs: list[NormalizedJob] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for page in range(1, pages_to_fetch + 1):
                params: dict[str, Any] = {
                    "ResultsPerPage": self.results_per_page,
                    "Page": page,
                }

                if self.job_category_code:
                    params["JobCategoryCode"] = self.job_category_code

                if self.position_offer_type_code:
                    params["PositionOfferTypeCode"] = self.position_offer_type_code

                try:
                    response = await client.get(
                        self.base_url,
                        headers=headers,
                        params=params,
                    )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as exc:
                    logger.exception("USAJOBS fetch failed on page=%s", page, exc_info=exc)
                    break

                items = payload.get("SearchResult", {}).get("SearchResultItems", [])
                if not isinstance(items, list) or not items:
                    break

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    normalized = self._normalize_job(item)
                    if normalized is None:
                        continue

                    normalized_jobs.append(normalized)

                    if len(normalized_jobs) >= self.max_jobs:
                        return normalized_jobs[: self.max_jobs]

                if len(items) < self.results_per_page:
                    break

        return normalized_jobs[: self.max_jobs]

    def _normalize_job(self, item: dict[str, Any]) -> NormalizedJob | None:
        """Normalize a single USAJOBS search result item."""
        descriptor = item.get("MatchedObjectDescriptor") or {}
        if not isinstance(descriptor, dict):
            return None

        title = self._safe_str(descriptor.get("PositionTitle"))
        url = self._safe_str(descriptor.get("PositionURI"))
        external_id = self._safe_str(descriptor.get("PositionID"))
        company = self._safe_str(descriptor.get("OrganizationName")) or "USAJOBS"
        location = self._extract_location(descriptor) or "Unknown"
        raw_description = self._build_description(descriptor)
        tags = self._extract_tags(descriptor)

        if not title or not url:
            return None

        if is_obviously_senior_title(title):
            return None

        if not should_keep_title_for_earlybloom(title):
            return None

        plain_description = strip_html(raw_description)
        summary = self.summarize(plain_description or title)

        remote, remote_type = self.infer_remote_type(
            title,
            location,
            plain_description,
            self._safe_str(descriptor.get("PositionLocationDisplay")),
            self._safe_str(descriptor.get("QualificationSummary")),
            self._safe_str(
                (descriptor.get("UserArea", {}) or {}).get("Details", {}).get("JobSummary")
            ),
            " ".join(tags),
        )

        job_id = self.build_stable_job_id(
            external_id=external_id,
            url=url,
            title=title,
            company=company,
            location=location,
        )

        responsibilities = self._extract_section_bullets(
            raw_description,
            section_names=("responsibilities", "major duties"),
        )
        qualifications = self._extract_section_bullets(
            raw_description,
            section_names=("qualifications",),
        )
        preferred_skills = self._extract_section_bullets(
            raw_description,
            section_names=("how you will be evaluated", "education"),
            max_items=6,
        )

        role_type = infer_role_type_from_text(
            title=title,
            description=plain_description,
            tags=tags,
        )

        experience_level = self._normalize_experience_level(
            infer_experience_level_from_text(
                title=title,
                description=plain_description,
                tags=tags,
            )
        )

        combined_skill_text = "\n".join(
            part
            for part in [
                title,
                plain_description,
                "\n".join(responsibilities),
                "\n".join(qualifications),
                " ".join(tags),
            ]
            if part
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
            description=plain_description,
            responsibilities=responsibilities,
            qualifications=qualifications,
            required_skills=extract_skill_hints(
                combined_skill_text,
                role_type=role_type,
                limit=12,
            ),
            preferred_skills=preferred_skills,
            employment_type=self._extract_employment_type(descriptor),
            experience_level=experience_level,
            salary_min=self._extract_salary_min(descriptor),
            salary_max=self._extract_salary_max(descriptor),
            salary_currency="USD",
        )

    def _normalize_experience_level(self, level: str | None) -> str:
        """Map shared helper output into the schema's allowed enum values."""
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

    def _extract_location(self, descriptor: dict[str, Any]) -> str:
        """Build a readable location string from USAJOBS location objects."""
        locations = descriptor.get("PositionLocation", [])
        chunks: list[str] = []

        if isinstance(locations, list):
            for location in locations:
                if not isinstance(location, dict):
                    continue
                city = self._safe_str(location.get("CityName"))
                region = self._safe_str(
                    location.get("CountrySubDivision") or location.get("CountryCode")
                )
                chunk = ", ".join(part for part in [city, region] if part)
                if chunk:
                    chunks.append(chunk)

        if chunks:
            return ", ".join(dict.fromkeys(chunks))

        return self._safe_str(descriptor.get("PositionLocationDisplay"))

    def _build_description(self, descriptor: dict[str, Any]) -> str:
        """Build a structured description from USAJOBS fields."""
        details = (descriptor.get("UserArea", {}) or {}).get("Details", {}) or {}

        sections: list[str] = []
        self._append_section(sections, "Job Summary", details.get("JobSummary"))
        self._append_section(sections, "Qualifications", descriptor.get("QualificationSummary"))
        self._append_section(sections, "Responsibilities", details.get("MajorDuties"))
        self._append_section(sections, "Education", details.get("Education"))
        self._append_section(sections, "How You Will Be Evaluated", details.get("Evaluations"))
        self._append_section(sections, "How To Apply", details.get("HowToApply"))

        return "\n\n".join(sections).strip()

    def _append_section(self, sections: list[str], heading: str, content: Any) -> None:
        """Append a rendered section if content exists."""
        body = self._render_section_body(content)
        if not body:
            return

        section = f"{heading}:\n{body}".strip()
        if section not in sections:
            sections.append(section)

    def _render_section_body(self, content: Any) -> str:
        """Render USAJOBS field content into readable text."""
        if content is None:
            return ""

        if isinstance(content, str):
            return normalize_paragraph_text(content)

        if isinstance(content, list):
            return self._render_list_content(content)

        if isinstance(content, dict):
            values: list[str] = []
            for value in content.values():
                rendered = self._render_section_body(value)
                if rendered:
                    values.append(rendered)
            return "\n".join(values).strip()

        return normalize_paragraph_text(str(content))

    def _render_list_content(self, items: Iterable[Any]) -> str:
        """Render a list of values into bullets or paragraphs."""
        rendered_items: list[str] = []
        for item in items:
            rendered = self._render_section_body(item)
            if rendered:
                rendered_items.append(rendered.strip())

        if not rendered_items:
            return ""

        if all("\n" not in item and len(item) <= 500 for item in rendered_items):
            return "\n".join(f"- {item}" for item in rendered_items)

        return "\n\n".join(rendered_items)

    def _extract_employment_type(self, descriptor: dict[str, Any]) -> str | None:
        """Extract employment type from position schedule."""
        schedules = descriptor.get("PositionSchedule", [])
        if isinstance(schedules, list) and schedules:
            first = schedules[0]
            if isinstance(first, dict):
                return self._safe_str(first.get("Name")) or None
            return self._safe_str(first) or None
        return None

    def _extract_tags(self, descriptor: dict[str, Any]) -> list[str]:
        """Extract useful category tags from USAJOBS fields."""
        tags: list[str] = []

        categories = descriptor.get("JobCategory", [])
        if isinstance(categories, list):
            for item in categories:
                if isinstance(item, dict):
                    value = self._safe_str(item.get("Name"))
                    if value:
                        tags.append(value)

        hiring_paths = (
            (descriptor.get("UserArea", {}) or {})
            .get("Details", {})
            .get("HiringPath", [])
        )
        if isinstance(hiring_paths, list):
            for item in hiring_paths:
                if isinstance(item, dict):
                    value = self._safe_str(item.get("Name"))
                    if value:
                        tags.append(value)

        deduped: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            key = tag.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(tag)

        return deduped

    def _extract_salary_min(self, descriptor: dict[str, Any]) -> int | None:
        """Extract minimum salary from remuneration data."""
        remuneration = descriptor.get("PositionRemuneration", [])
        if not isinstance(remuneration, list) or not remuneration:
            return None

        value = remuneration[0].get("MinimumRange")
        try:
            return int(float(value)) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _extract_salary_max(self, descriptor: dict[str, Any]) -> int | None:
        """Extract maximum salary from remuneration data."""
        remuneration = descriptor.get("PositionRemuneration", [])
        if not isinstance(remuneration, list) or not remuneration:
            return None

        value = remuneration[0].get("MaximumRange")
        try:
            return int(float(value)) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _extract_section_bullets(
        self,
        text: str,
        *,
        section_names: tuple[str, ...],
        max_items: int = 8,
    ) -> list[str]:
        """Extract bullets from a named section in the rendered provider text."""
        if not text:
            return []

        lowered = text.lower()
        matched_index = -1
        matched_name = ""

        for name in section_names:
            index = lowered.find(f"{name.lower()}:")
            if index != -1:
                matched_index = index
                matched_name = name
                break

        if matched_index == -1:
            return []

        remainder = text[matched_index + len(matched_name) + 1 :]
        next_header = re.search(r"\n[A-Z][A-Za-z /]+:\n", remainder)
        if next_header:
            remainder = remainder[: next_header.start()]

        return split_bullets(remainder[:1500], max_items=max_items)

    def _safe_str(self, value: Any) -> str:
        """Return a stripped string representation for arbitrary values."""
        if value is None:
            return ""
        return str(value).strip()
