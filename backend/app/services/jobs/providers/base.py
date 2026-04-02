from __future__ import annotations

import hashlib
import html
import re
from abc import ABC, abstractmethod
from typing import Iterable

from app.schemas.jobs import NormalizedJob


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_BULLET_SPLIT_RE = re.compile(r"(?:\n|•|\u2022|- )+")


class BaseJobProvider(ABC):
    """
    Base interface for all job providers.

    Providers should:
    - fetch raw source data
    - map it into NormalizedJob
    - avoid provider-specific filtering beyond obvious source sanity checks

    Shared policy decisions (global filtering, dedupe, ranking) live outside providers.
    """

    source_name: str = "unknown"

    @abstractmethod
    async def fetch_jobs(self) -> list[NormalizedJob]:
        """Fetch and normalize jobs from a provider."""
        raise NotImplementedError

    def build_stable_job_id(
        self,
        *,
        external_id: str | None = None,
        url: str | None = None,
        title: str,
        company: str,
        location: str | None = None,
    ) -> str:
        """
        Build a stable ID for a normalized job.

        Priority:
        1. external_id if present
        2. URL if present
        3. title/company/location fingerprint
        """
        if external_id:
            raw = f"{self.source_name}|external|{external_id.strip()}"
        elif url:
            raw = f"{self.source_name}|url|{self._canonicalize_url(url)}"
        else:
            raw = (
                f"{self.source_name}|fallback|"
                f"{self._normalize_text(title)}|"
                f"{self._normalize_text(company)}|"
                f"{self._normalize_text(location or '')}"
            )

        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        return f"{self.source_name}_{digest}"

    def strip_html(self, value: str | None) -> str:
        if not value:
            return ""
        text = html.unescape(value)
        text = _TAG_RE.sub(" ", text)
        text = _WHITESPACE_RE.sub(" ", text).strip()
        return text

    def summarize(self, text: str, max_length: int = 280) -> str:
        cleaned = self._normalize_text(text)
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[: max_length - 1].rstrip() + "…"

    def split_bullets(self, text: str | None, max_items: int = 8) -> list[str]:
        if not text:
            return []
        cleaned = self.strip_html(text)
        parts = [
            self._normalize_text(part)
            for part in _BULLET_SPLIT_RE.split(cleaned)
            if self._normalize_text(part)
        ]
        seen: set[str] = set()
        result: list[str] = []
        for part in parts:
            key = part.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(part)
            if len(result) >= max_items:
                break
        return result

    def infer_remote_type(self, *candidates: str | None) -> tuple[bool, str]:
        joined = " ".join(filter(None, candidates)).casefold()

        if "hybrid" in joined:
            return True, "hybrid"
        if "remote" in joined or "work from home" in joined:
            return True, "remote"
        if "on-site" in joined or "onsite" in joined or "in office" in joined:
            return False, "onsite"
        return False, "unknown"

    def infer_experience_level(self, *candidates: str | None) -> str:
        text = " ".join(filter(None, candidates)).casefold()

        senior_patterns = [
            r"\bstaff\b",
            r"\bprincipal\b",
            r"\bsr\.?\b",
            r"\bsenior\b",
            r"\blead\b",
            r"\bmanager\b",
            r"\bdirector\b",
            r"\barchitect\b",
            r"\b[5-9]\+?\s+years\b",
            r"\b1[0-9]\+?\s+years\b",
        ]
        mid_patterns = [
            r"\bmid\b",
            r"\bintermediate\b",
            r"\b[3-4]\+?\s+years\b",
        ]
        junior_patterns = [
            r"\bentry\b",
            r"\bentry[- ]level\b",
            r"\bjunior\b",
            r"\bassociate\b",
            r"\bnew grad\b",
            r"\brecent grad\b",
            r"\bgraduate\b",
            r"\b0-?2\s+years\b",
            r"\b1-?2\s+years\b",
        ]

        if any(re.search(pattern, text) for pattern in senior_patterns):
            return "senior"
        if any(re.search(pattern, text) for pattern in mid_patterns):
            return "mid"
        if any(re.search(pattern, text) for pattern in junior_patterns):
            return "junior"
        return "unknown"

    def first_non_empty(self, values: Iterable[str | None], default: str = "") -> str:
        for value in values:
            if value and value.strip():
                return value.strip()
        return default

    def _canonicalize_url(self, url: str) -> str:
        value = url.strip()
        value = re.sub(r"#.*$", "", value)
        value = re.sub(r"\?.*$", "", value)
        return value.rstrip("/")

    def _normalize_text(self, value: str | None) -> str:
        if not value:
            return ""
        return _WHITESPACE_RE.sub(" ", value).strip()