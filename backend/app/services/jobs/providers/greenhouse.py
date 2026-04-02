from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from app.schemas.jobs import NormalizedJob
from app.services.jobs.providers.base import BaseJobProvider

logger = logging.getLogger(__name__)


class GreenhouseJobBoardProvider(BaseJobProvider):
    """
    Ingests jobs from curated Greenhouse board tokens.

    Example board token:
    - stripe
    - plaid
    - ramp
    - andurilindustries

    Endpoint format:
    https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
    """

    source_name = "greenhouse"
    base_url = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(
        self,
        *,
        board_tokens: list[str],
        timeout_seconds: float = 6.0,
        max_jobs_per_board: int = 100,
    ) -> None:
        self.board_tokens = [token.strip() for token in board_tokens if token.strip()]
        self.timeout_seconds = timeout_seconds
        self.max_jobs_per_board = max_jobs_per_board

    @classmethod
    def from_env(cls) -> "GreenhouseJobBoardProvider | None":
        raw_tokens = os.getenv("JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", "")
        enabled = os.getenv("JOB_PROVIDER_GREENHOUSE_ENABLED", "false").strip().lower()

        if enabled not in {"1", "true", "yes", "on"}:
            return None

        board_tokens = [token.strip() for token in raw_tokens.split(",") if token.strip()]
        if not board_tokens:
            logger.warning(
                "Greenhouse provider enabled but JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS is empty."
            )
            return None

        timeout_seconds = float(os.getenv("JOB_PROVIDER_TIMEOUT_SECONDS", "6.0"))
        max_jobs_per_board = int(os.getenv("JOB_PROVIDER_MAX_JOBS_PER_SOURCE", "100"))

        return cls(
            board_tokens=board_tokens,
            timeout_seconds=timeout_seconds,
            max_jobs_per_board=max_jobs_per_board,
        )

    async def fetch_jobs(self) -> list[NormalizedJob]:
        if not self.board_tokens:
            return []

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            tasks = [self._fetch_board_jobs(client, token) for token in self.board_tokens]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        jobs: list[NormalizedJob] = []
        for token, result in zip(self.board_tokens, results):
            if isinstance(result, Exception):
                logger.exception("Greenhouse board fetch failed for token=%s", token, exc_info=result)
                continue
            jobs.extend(result)

        return jobs

    async def _fetch_board_jobs(
        self,
        client: httpx.AsyncClient,
        board_token: str,
    ) -> list[NormalizedJob]:
        url = f"{self.base_url}/{board_token}/jobs"
        params = {"content": "true"}

        response = await client.get(url, params=params)
        response.raise_for_status()

        payload = response.json()
        raw_jobs = payload.get("jobs", [])[: self.max_jobs_per_board]

        normalized: list[NormalizedJob] = []
        for item in raw_jobs:
            job = self._normalize_job(item, board_token=board_token)
            if job is not None:
                normalized.append(job)

        return normalized

    def _normalize_job(
        self,
        item: dict[str, Any],
        *,
        board_token: str,
    ) -> NormalizedJob | None:
        title = self._safe_str(item.get("title"))
        absolute_url = self._safe_str(item.get("absolute_url"))
        external_id = str(item.get("id") or "").strip()

        if not title or not absolute_url:
            return None

        metadata = item.get("metadata") or []
        content = self._safe_str(item.get("content"))

        location_name = self._extract_location(item)
        company_name = self._guess_company_name(board_token, content)
        remote, remote_type = self.infer_remote_type(
            title,
            location_name,
            content,
            " ".join(self._metadata_values(metadata)),
        )

        description = self.strip_html(content)
        summary = self.summarize(description or title)
        experience_level = self.infer_experience_level(title, description)

        responsibilities = self._extract_section_bullets(
            content,
            section_names=("responsibilities", "what you'll do", "what you will do"),
        )
        qualifications = self._extract_section_bullets(
            content,
            section_names=("qualifications", "requirements", "what we're looking for"),
        )

        required_skills = self._extract_skill_hints(description)
        preferred_skills = self._extract_section_bullets(
            content,
            section_names=("nice to have", "preferred qualifications", "bonus"),
            max_items=6,
        )

        employment_type = self.first_non_empty(
            [
                self._find_metadata_value(metadata, "employment type"),
                self._find_metadata_value(metadata, "job type"),
                self._find_metadata_value(metadata, "type"),
            ],
            default="",
        ) or None

        job_id = self.build_stable_job_id(
            external_id=external_id,
            url=absolute_url,
            title=title,
            company=company_name,
            location=location_name,
        )

        return NormalizedJob(
            id=job_id,
            title=title,
            company=company_name,
            location=location_name or "Unknown",
            remote=remote,
            remote_type=remote_type,
            url=absolute_url,
            source=self.source_name,
            summary=summary,
            description=description,
            responsibilities=responsibilities,
            qualifications=qualifications,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            employment_type=employment_type,
            experience_level=experience_level,
        )

    def _extract_location(self, item: dict[str, Any]) -> str:
        location = item.get("location") or {}
        if isinstance(location, dict):
            return self._safe_str(location.get("name"))
        return self._safe_str(location)

    def _guess_company_name(self, board_token: str, content: str) -> str:
        """
        Greenhouse job-board responses do not always include an explicit company field.
        For a first pass, use a cleaned board token as the company fallback.
        """
        token_name = board_token.replace("-", " ").replace("_", " ").strip()
        if token_name:
            return " ".join(part.capitalize() for part in token_name.split())
        return "Unknown Company"

    def _metadata_values(self, metadata: list[dict[str, Any]]) -> list[str]:
        values: list[str] = []
        for item in metadata:
            if not isinstance(item, dict):
                continue
            value = self._safe_str(item.get("value"))
            if value:
                values.append(value)
        return values

    def _find_metadata_value(self, metadata: list[dict[str, Any]], key: str) -> str:
        target = key.casefold()
        for item in metadata:
            if not isinstance(item, dict):
                continue
            name = self._safe_str(item.get("name")).casefold()
            if name == target:
                return self._safe_str(item.get("value"))
        return ""

    def _extract_section_bullets(
        self,
        html_text: str,
        *,
        section_names: tuple[str, ...],
        max_items: int = 8,
    ) -> list[str]:
        if not html_text:
            return []

        plain = self.strip_html(html_text).lower()
        raw_plain = self.strip_html(html_text)

        section_index = -1
        matched_section = ""
        for section in section_names:
            idx = plain.find(section.lower())
            if idx != -1:
                section_index = idx
                matched_section = section
                break

        if section_index == -1:
            return []

        remainder = raw_plain[section_index + len(matched_section) :]
        truncated = remainder[:1500]
        return self.split_bullets(truncated, max_items=max_items)

    def _extract_skill_hints(self, description: str) -> list[str]:
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
        ]
        lowered = description.casefold()
        matches = [skill for skill in skill_bank if skill in lowered]
        return matches[:10]

    def _safe_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()