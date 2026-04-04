from __future__ import annotations

import hashlib
import html
import re
from abc import ABC, abstractmethod
from typing import Any
from typing import Iterable


_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_BULLET_SPLIT_RE = re.compile(r"(?:\n|•|\u2022|- )+")


class BaseJobProvider(ABC):
    """Base interface for all Layer 1 job providers.

    Providers should:
    - fetch raw source data
    - map source-specific payloads into a provider-normalized raw dict shape
    - avoid cross-provider policy decisions such as final filtering, dedupe,
      or schema enforcement

    Shared policy decisions live outside providers in the normalization,
    filtering, and ingestion layers.
    """

    source_name: str = "unknown"

    @abstractmethod
    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetch jobs in the provider-normalized raw shape."""
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
        """Build a stable provider-side job ID.

        Priority:
        1. external_id if present
        2. canonical URL if present
        3. title/company/location fingerprint

        Args:
            external_id: Provider-native identifier.
            url: Provider job URL.
            title: Job title.
            company: Company name.
            location: Human-readable location.

        Returns:
            Stable provider-side ID string.
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
        """Strip HTML tags and normalize whitespace.

        Args:
            value: Raw HTML-like text.

        Returns:
            Plain text with normalized spacing.
        """
        if not value:
            return ""

        text = html.unescape(value)
        text = _TAG_RE.sub(" ", text)
        text = _WHITESPACE_RE.sub(" ", text).strip()
        return text

    def summarize(self, text: str, max_length: int = 280) -> str:
        """Create a short summary from cleaned text.

        Args:
            text: Source text.
            max_length: Maximum summary length.

        Returns:
            Truncated summary text.
        """
        cleaned = self._normalize_text(text)
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[: max_length - 1].rstrip() + "…"

    def split_bullets(self, text: str | None, max_items: int = 8) -> list[str]:
        """Split bullet-like text into distinct items.

        Args:
            text: Raw bullet-ish text.
            max_items: Maximum items to return.

        Returns:
            Distinct bullet items preserving original order.
        """
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
        """Infer a coarse remote classification from candidate text.

        Args:
            *candidates: Text fragments such as title, location, description, tags.

        Returns:
            Tuple of (remote_flag, remote_type).
        """
        joined = " ".join(filter(None, candidates)).casefold()

        if "hybrid" in joined:
            return True, "hybrid"

        if (
            "remote" in joined
            or "work from home" in joined
            or "telework" in joined
            or "distributed" in joined
        ):
            return True, "remote"

        if "on-site" in joined or "onsite" in joined or "in office" in joined:
            return False, "onsite"

        return False, "unknown"

    def infer_experience_level(self, *candidates: str | None) -> str:
        """Infer a coarse experience hint from provider text.

        Args:
            *candidates: Text fragments such as title, description, or tags.

        Returns:
            One of:
            - junior
            - mid-level
            - senior
            - unknown
        """
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
            return "mid-level"
        if any(re.search(pattern, text) for pattern in junior_patterns):
            return "junior"
        return "unknown"

    def first_non_empty(self, values: Iterable[str | None], default: str = "") -> str:
        """Return the first non-empty stripped string.

        Args:
            values: Candidate string values.
            default: Fallback when none are usable.

        Returns:
            First usable string or default.
        """
        for value in values:
            if value and value.strip():
                return value.strip()
        return default

    def _canonicalize_url(self, url: str) -> str:
        """Canonicalize a URL for stable ID generation."""
        value = url.strip()
        value = re.sub(r"#.*$", "", value)
        value = re.sub(r"\?.*$", "", value)
        return value.rstrip("/")

    def _normalize_text(self, value: str | None) -> str:
        """Normalize internal text for matching and summaries."""
        if not value:
            return ""
        return _WHITESPACE_RE.sub(" ", value).strip()