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

US_REMOTE_ONLY_PATTERNS = {
    "remote us",
    "remote - us",
    "remote, us",
    "remote united states",
    "remote - united states",
    "us only",
    "u.s. only",
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
    "no visa sponsorship",
    "cannot sponsor",
    "unable to sponsor",
    "eligible to work in the united states",
    "must work us hours",
    "must work eastern time",
    "must work central time",
    "must work pacific time",
    "must work in us time zones",
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
}

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

    if "united states" in loc or "u.s." in loc or "usa" in loc:
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
    return any(keyword in loc for keyword in NON_US_LOCATION_KEYWORDS)


def has_non_us_hint(*values: str | None) -> bool:
    """Return True when any text clearly points to a non-U.S. role."""
    text = _normalize_text(*values)
    if not text:
        return False
    return any(keyword in text for keyword in NON_US_LOCATION_KEYWORDS)


def is_remote_like(location: str | None, description: str | None, remote_flag: bool | None) -> bool:
    """Return True when the role appears to be remote in any lightweight way."""
    if remote_flag:
        return True

    text = _normalize_text(location, description)
    return any(keyword in text for keyword in REMOTE_KEYWORDS)


def is_global_remote_role(location: str | None, description: str | None, title: str | None) -> bool:
    """Return True when the remote scope looks worldwide or explicitly non-U.S."""
    text = _normalize_text(title, location, description)
    return any(pattern in text for pattern in GLOBAL_REMOTE_PATTERNS)


def is_us_remote_role(
    location: str | None,
    description: str | None,
    remote_flag: bool | None,
    title: str | None = None,
) -> bool:
    """Return True for remote jobs that are explicitly U.S.-restricted."""
    if not is_remote_like(location=location, description=description, remote_flag=remote_flag):
        return False

    text = _normalize_text(title, location, description)
    return any(pattern in text for pattern in US_REMOTE_ONLY_PATTERNS)


def should_keep_us_focused_job(
    location: str | None,
    description: str | None,
    remote_flag: bool | None,
    title: str | None = None,
) -> bool:
    """Keep only legitimate jobs that are clearly U.S.-based or clearly U.S.-remote."""
    if looks_non_us_location(location):
        return False

    if looks_us_location(location):
        return True

    if is_global_remote_role(location=location, description=description, title=title):
        return False

    if has_non_us_hint(title, description) and not is_us_remote_role(
        location=location,
        description=description,
        remote_flag=remote_flag,
        title=title,
    ):
        return False

    if is_us_remote_role(
        location=location,
        description=description,
        remote_flag=remote_flag,
        title=title,
    ):
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