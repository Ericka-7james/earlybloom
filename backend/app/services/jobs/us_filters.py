"""U.S.-focused trust and relevance helpers for job listings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.jobs.constants import (
    NON_US_LOCATION_KEYWORDS,
    REMOTE_KEYWORDS,
    US_STATE_CODES,
    US_STATE_NAMES,
)

STRICT_US_SIGNAL_SOURCES = {
    "arbeitnow",
    "remotive",
    "jobicy",
}

US_REMOTE_ONLY_PATTERNS = {
    "remote us",
    "remote - us",
    "remote, us",
    "remote united states",
    "remote - united states",
    "remote within the us",
    "remote within the united states",
    "remote across the us",
    "us only",
    "u.s. only",
    "usa only",
    "united states only",
    "must be based in the us",
    "must be based in the u.s.",
    "must be based in the united states",
    "must reside in the us",
    "must reside in the united states",
    "must be located in the us",
    "must be located in the united states",
    "authorized to work in the us",
    "authorized to work in the u.s.",
    "authorized to work in the united states",
    "must be authorized to work in the us",
    "must be authorized to work in the united states",
    "u.s. work authorization",
    "us work authorization",
    "eligible to work in the united states",
    "eligible to work in the us",
    "must work us hours",
    "must work eastern time",
    "must work central time",
    "must work pacific time",
    "must work in us time zones",
    "must work in eastern time",
    "must work in central time",
    "must work in pacific time",
    "must overlap with us time zones",
    "must overlap with eastern time",
    "must overlap with est hours",
    "must overlap with pst hours",
    "based in the united states",
    "based in the us",
    "u.s.-based",
    "us-based",
    "usa-based",
    "federal government",
    "telework eligible",
    "u.s. citizenship",
    "citizenship required",
}

GLOBAL_REMOTE_PATTERNS = {
    "work from anywhere",
    "anywhere in the world",
    "worldwide",
    "global remote",
    "remote worldwide",
    "open worldwide",
    "international candidates",
    "globally",
    "all countries",
    "remote anywhere",
    "work anywhere",
    "location independent",
    "work from anywhere in the world",
}

REGION_LIMIT_PATTERNS = {
    "emea",
    "apac",
    "latam",
    "latin america",
    "europe only",
    "uk only",
    "eu only",
    "canada only",
    "australia only",
    "india only",
}

US_TIMEZONE_PATTERNS = [
    re.compile(r"\b(?:eastern|central|mountain|pacific)\s+time\b", re.IGNORECASE),
    re.compile(r"\b(?:u\.s\.|us)\s+time\s+zones?\b", re.IGNORECASE),
    re.compile(r"\b(?:overlap|work|working|coverage|available|availability)\b.{0,30}\b(?:est|edt|cst|cdt|mst|mdt|pst|pdt)\b", re.IGNORECASE),
    re.compile(r"\b(?:est|edt|cst|cdt|mst|mdt|pst|pdt)\b.{0,20}\b(?:hours?|timezone|time zone|coverage|overlap|business hours)\b", re.IGNORECASE),
]

SCAM_PATTERNS = [
    re.compile(r"mention the word\s+\w+", re.IGNORECASE),
    re.compile(r"to prove you read this", re.IGNORECASE),
    re.compile(r"buy bitcoin", re.IGNORECASE),
    re.compile(r"\bbitcoin\b", re.IGNORECASE),
    re.compile(r"\bcrypto\b", re.IGNORECASE),
    re.compile(r"\btelegram\b", re.IGNORECASE),
    re.compile(r"\bwhatsapp\b", re.IGNORECASE),
    re.compile(r"\bcash app\b", re.IGNORECASE),
    re.compile(r"\bzelle\b", re.IGNORECASE),
    re.compile(r"text\s+\+?\d", re.IGNORECASE),
    re.compile(r"text us at", re.IGNORECASE),
    re.compile(r"email us immediately", re.IGNORECASE),
    re.compile(r"no experience.*\$\s?\d", re.IGNORECASE),
    re.compile(r"\$\s?2k\s*/?\s*week", re.IGNORECASE),
    re.compile(r"\$\s?3k\s*/?\s*week", re.IGNORECASE),
    re.compile(r"\$\s?[4-9]k\s*/?\s*week", re.IGNORECASE),
]


@dataclass(frozen=True)
class FilterDecision:
    keep: bool
    reason: str | None = None


def _safe_lower(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_text(*parts: str | None) -> str:
    text = " ".join(_safe_lower(part) for part in parts if part)
    return re.sub(r"\s+", " ", text).strip()


def looks_us_location(location: str | None) -> bool:
    """Return True when a location clearly looks U.S.-based."""
    loc = _safe_lower(location)
    if not loc:
        return False

    if any(token in loc for token in ("united states", "u.s.", "usa", "us-based", "u.s.-based")):
        return True

    if "remote" in loc and any(
        token in loc for token in (" us", "u.s.", "usa", "united states")
    ):
        return True

    for state in US_STATE_NAMES:
        if state in loc:
            return True

    tokens = re.split(r"[\s,()/|-]+", loc.upper())
    return any(token in US_STATE_CODES for token in tokens if token)


def looks_non_us_location(location: str | None) -> bool:
    """Return True when a location clearly looks non-U.S."""
    loc = _safe_lower(location)
    if not loc:
        return False

    if looks_us_location(loc):
        return False

    return any(keyword in loc for keyword in NON_US_LOCATION_KEYWORDS)


def has_non_us_hint(*values: str | None) -> bool:
    """Return True when any text clearly points to a non-U.S. role."""
    text = _normalize_text(*values)
    if not text:
        return False

    if any(pattern in text for pattern in REGION_LIMIT_PATTERNS):
        return True

    if has_us_eligibility_hint(*values):
        return False

    return any(keyword in text for keyword in NON_US_LOCATION_KEYWORDS)


def has_us_timezone_hint(*values: str | None) -> bool:
    """Return True when text implies U.S. working hours or timezone alignment."""
    text = _normalize_text(*values)
    if not text:
        return False

    return any(pattern.search(text) for pattern in US_TIMEZONE_PATTERNS)


def has_us_eligibility_hint(*values: str | None) -> bool:
    """Return True when text explicitly suggests U.S. work eligibility."""
    text = _normalize_text(*values)
    if not text:
        return False

    if any(pattern in text for pattern in US_REMOTE_ONLY_PATTERNS):
        return True

    return has_us_timezone_hint(text)


def is_remote_like(location: str | None, description: str | None, remote_flag: bool | None) -> bool:
    """Return True when the role appears to be remote in any lightweight way."""
    if remote_flag:
        return True

    text = _normalize_text(location, description)
    return any(keyword in text for keyword in REMOTE_KEYWORDS)


def is_global_remote_role(location: str | None, description: str | None, title: str | None) -> bool:
    """Return True when the remote scope looks worldwide or explicitly non-U.S."""
    text = _normalize_text(title, location, description)

    if any(pattern in text for pattern in GLOBAL_REMOTE_PATTERNS):
        return True

    if any(pattern in text for pattern in REGION_LIMIT_PATTERNS):
        return True

    return False


def is_us_remote_role(
    location: str | None,
    description: str | None,
    remote_flag: bool | None,
    title: str | None = None,
) -> bool:
    """Return True for remote jobs that are explicitly or strongly U.S.-restricted."""
    if not is_remote_like(location=location, description=description, remote_flag=remote_flag):
        return False

    text = _normalize_text(title, location, description)

    if any(pattern in text for pattern in US_REMOTE_ONLY_PATTERNS):
        return True

    if has_us_timezone_hint(text):
        return True

    if "remote" in text and looks_us_location(location):
        return True

    return False


def should_keep_us_focused_job(
    location: str | None,
    description: str | None,
    remote_flag: bool | None,
    title: str | None = None,
    source: str | None = None,
) -> bool:
    """Keep legitimate jobs that are clearly U.S.-based or plausibly U.S.-eligible.

    Source-aware behavior:
    - reject obvious non-U.S. and worldwide/region-limited roles
    - keep clear U.S. physical roles
    - for global-first sources, require an explicit U.S. signal
    - for U.S.-leaning or trusted sources, allow a small remote fallback path
    """
    source_name = _safe_lower(source)
    location_text = _safe_lower(location)
    text = _normalize_text(title, location, description)

    if looks_non_us_location(location_text):
        return False

    if is_global_remote_role(location=location, description=description, title=title):
        return False

    if looks_us_location(location_text):
        return True

    if is_us_remote_role(
        location=location,
        description=description,
        remote_flag=remote_flag,
        title=title,
    ):
        return True

    if has_non_us_hint(title, description, location) and not has_us_eligibility_hint(
        title,
        description,
        location,
    ):
        return False

    # Global-first / non-U.S.-first sources must prove U.S. eligibility.
    if source_name in STRICT_US_SIGNAL_SOURCES:
        return has_us_eligibility_hint(title, description, location)

    # For U.S.-leaning sources, allow a small fallback path for remote jobs
    # with weak metadata but some U.S. clues.
    if is_remote_like(location=location, description=description, remote_flag=remote_flag):
        if has_us_eligibility_hint(title, description, location):
            return True

        if any(state in text for state in US_STATE_NAMES):
            return True

    return False


def detect_spam_or_scam(
    title: str | None,
    company: str | None,
    location: str | None,
    description: str | None,
    url: str | None,
) -> bool:
    """Return True when a job contains obvious scam or spam signals."""
    text = _normalize_text(title, company, location, description, url)
    if not text:
        return False

    return any(pattern.search(text) for pattern in SCAM_PATTERNS)