# backend/app/services/jobs/job_filters.py
"""Filtering utilities for job ingestion and ranking."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from app.services.jobs.common.title_rules import (
    is_ambiguous_but_keep_title,
    is_early_career_title,
    is_obviously_senior_title,
    normalize_title,
)

DEFAULT_LEVELS = {"entry-level", "junior"}

SUPPORTED_LEVELS = {
    "entry-level",
    "junior",
    "mid-level",
    "senior",
}

SUPPORTED_ROLE_TYPES = {
    "frontend",
    "backend",
    "full-stack",
    "software-engineering",
    "mobile",
    "data",
    "data-engineering",
    "data-analyst",
    "machine-learning",
    "ai",
    "devops",
    "sre",
    "cloud",
    "infrastructure",
    "cybersecurity",
    "qa",
    "test-automation",
    "product",
    "product-design",
    "ux",
    "solutions-engineering",
    "technical-support",
    "it",
    "business-analyst",
    "platform",
    "developer-tools",
}

MID_LEVEL_HINTS = [
    r"\bii\b",
    r"\biii\b",
    r"\blevel\s?2\b",
    r"\blevel\s?3\b",
    r"\bintermediate\b",
    r"\bjourneyman\b",
]

HARD_SENIOR_EXPERIENCE_HINTS = [
    r"\b5\+?\s+years?\b",
    r"\b6\+?\s+years?\b",
    r"\b7\+?\s+years?\b",
    r"\b8\+?\s+years?\b",
    r"\b9\+?\s+years?\b",
    r"\b10\+?\s+years?\b",
]

UNKNOWN_SAFE_PATTERNS = [
    r"\banalyst\b",
    r"\bspecialist\b",
    r"\bcoordinator\b",
    r"\bsupport\b",
    r"\btechnician\b",
    r"\badministrator\b",
    r"\boperator\b",
    r"\brepresentative\b",
    r"\bimplementation\b",
    r"\bhelp desk\b",
    r"\bservice desk\b",
    r"\bqa\b",
    r"\btester\b",
    r"\bdeveloper\b",
    r"\bengineer\b",
    r"\bit\b",
    r"\bsecurity\b",
    r"\bcyber\b",
    r"\bdata\b",
    r"\bproduct\b",
    r"\bsystems?\b",
    r"\bnetwork\b",
    r"\bsoftware\b",
    r"\bfrontend\b",
    r"\bbackend\b",
    r"\bfull stack\b",
]

ENTRY_JUNIOR_STRETCH_PATTERNS = [
    r"\bsoftware engineer i\b",
    r"\bassociate\b",
    r"\banalyst\b",
    r"\bspecialist\b",
    r"\bcoordinator\b",
    r"\btechnical support\b",
    r"\bit support\b",
    r"\bhelp desk\b",
    r"\bservice desk\b",
    r"\bimplementation\b",
    r"\bqa\b",
    r"\btest engineer\b",
    r"\bsecurity analyst\b",
    r"\bbusiness analyst\b",
    r"\bdata analyst\b",
    r"\bproduct analyst\b",
    r"\bsupport engineer\b",
]

ROLE_TYPE_ALIASES = {
    "software": "software-engineering",
    "it_support": "technical-support",
    "analyst": "business-analyst",
    "security": "cybersecurity",
    "cloud_devops": "devops",
}

US_STATE_CODE_TO_NAME = {
    "al": "alabama",
    "ak": "alaska",
    "az": "arizona",
    "ar": "arkansas",
    "ca": "california",
    "co": "colorado",
    "ct": "connecticut",
    "de": "delaware",
    "fl": "florida",
    "ga": "georgia",
    "hi": "hawaii",
    "id": "idaho",
    "il": "illinois",
    "in": "indiana",
    "ia": "iowa",
    "ks": "kansas",
    "ky": "kentucky",
    "la": "louisiana",
    "me": "maine",
    "md": "maryland",
    "ma": "massachusetts",
    "mi": "michigan",
    "mn": "minnesota",
    "ms": "mississippi",
    "mo": "missouri",
    "mt": "montana",
    "ne": "nebraska",
    "nv": "nevada",
    "nh": "new hampshire",
    "nj": "new jersey",
    "nm": "new mexico",
    "ny": "new york",
    "nc": "north carolina",
    "nd": "north dakota",
    "oh": "ohio",
    "ok": "oklahoma",
    "or": "oregon",
    "pa": "pennsylvania",
    "ri": "rhode island",
    "sc": "south carolina",
    "sd": "south dakota",
    "tn": "tennessee",
    "tx": "texas",
    "ut": "utah",
    "vt": "vermont",
    "va": "virginia",
    "wa": "washington",
    "wv": "west virginia",
    "wi": "wisconsin",
    "wy": "wyoming",
    "dc": "district of columbia",
}
US_STATE_NAME_TO_CODE = {name: code for code, name in US_STATE_CODE_TO_NAME.items()}


@dataclass(frozen=True)
class JobFilterOptions:
    """Normalized filter options used during job filtering."""

    selected_levels: set[str]
    selected_role_types: set[str]
    selected_location_query: str | None = None


def _normalize_text(value: str | None) -> str:
    """Normalize text for regex matching."""
    return " ".join(str(value or "").strip().lower().split())


def _normalize_search_text(value: str | None) -> str:
    """Normalize free-form search text for tolerant location matching."""
    text = str(value or "").strip().lower()
    text = re.sub(r"[|/]+", " ", text)
    text = re.sub(r"[()]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Return True when text matches any regex in the provided list."""
    return any(re.search(pattern, text) for pattern in patterns)


def normalize_levels(levels: Iterable[str] | None) -> set[str]:
    """Normalize user-selected job levels.

    A missing or empty value means no backend level filter.
    """
    if levels is None:
        return set()

    return {
        str(level).strip().lower()
        for level in levels
        if str(level).strip().lower() in SUPPORTED_LEVELS
    }


def normalize_role_types(role_types: Iterable[str] | None) -> set[str]:
    """Normalize user-selected role types.

    A missing or empty value means no backend role-type filter.
    """
    if role_types is None:
        return set()

    normalized: set[str] = set()
    for role_type in role_types:
        value = str(role_type).strip().lower()
        if value in SUPPORTED_ROLE_TYPES:
            normalized.add(value)
            continue

        alias = ROLE_TYPE_ALIASES.get(value)
        if alias and alias in SUPPORTED_ROLE_TYPES:
            normalized.add(alias)

    return normalized


def normalize_location_query(location_query: str | None) -> str | None:
    """Normalize a free-form location query."""
    normalized = _normalize_search_text(location_query)
    return normalized or None


def build_filter_options(
    levels: Iterable[str] | None,
    role_types: Iterable[str] | None,
    location_query: str | None = None,
) -> JobFilterOptions:
    """Build normalized filter options."""
    return JobFilterOptions(
        selected_levels=normalize_levels(levels),
        selected_role_types=normalize_role_types(role_types),
        selected_location_query=normalize_location_query(location_query),
    )


def has_mid_level_hint(title: str | None) -> bool:
    """Return True when a title suggests mid-level but not necessarily senior."""
    normalized_title = _normalize_text(title)
    if not normalized_title:
        return False

    return _matches_any_pattern(normalized_title, MID_LEVEL_HINTS)


def has_hard_senior_experience_hint(text: str | None) -> bool:
    """Return True when text contains a strong seniority hint."""
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return False

    return _matches_any_pattern(normalized_text, HARD_SENIOR_EXPERIENCE_HINTS)


def is_unknown_level_safe_title(title: str | None) -> bool:
    """Return True when an unknown-level title is still plausible for EB users."""
    normalized_title = normalize_title(title)
    if not normalized_title:
        return False

    if is_obviously_senior_title(normalized_title):
        return False

    if is_early_career_title(normalized_title):
        return True

    if is_ambiguous_but_keep_title(normalized_title):
        return True

    return _matches_any_pattern(normalized_title, UNKNOWN_SAFE_PATTERNS)


def is_entry_junior_stretch_title(title: str | None) -> bool:
    """Return True for titles that are realistic for entry/junior users to consider."""
    normalized_title = _normalize_text(title)
    if not normalized_title:
        return False

    if is_obviously_senior_title(normalized_title):
        return False

    if is_early_career_title(normalized_title):
        return True

    if _matches_any_pattern(normalized_title, ENTRY_JUNIOR_STRETCH_PATTERNS):
        return True

    return False


def matches_level_filter(
    *,
    title: str | None,
    normalized_level: str | None,
    selected_levels: set[str],
) -> bool:
    """Check whether a job matches selected experience-level filters."""
    level = _normalize_text(normalized_level)
    title_text = _normalize_text(title)

    if is_obviously_senior_title(title_text):
        return False

    if level == "senior":
        return False

    if has_hard_senior_experience_hint(title_text):
        return False

    if not selected_levels:
        return True

    if level == "mid-level":
        if "mid-level" in selected_levels:
            return True

        if selected_levels.issubset(DEFAULT_LEVELS):
            return is_entry_junior_stretch_title(title_text)

        return False

    if level in {"entry-level", "junior"}:
        return level in selected_levels

    if level == "unknown":
        if "mid-level" in selected_levels and is_unknown_level_safe_title(title_text):
            return True

        if selected_levels.issubset(DEFAULT_LEVELS):
            return is_unknown_level_safe_title(title_text)

        return is_unknown_level_safe_title(title_text)

    return is_unknown_level_safe_title(title_text)


def matches_role_type_filter(
    *,
    normalized_role_type: str | None,
    selected_role_types: set[str],
) -> bool:
    """Check whether a job matches selected role-type filters."""
    if not selected_role_types:
        return True

    role_type = _normalize_text(normalized_role_type)
    if not role_type:
        return True

    role_type = ROLE_TYPE_ALIASES.get(role_type, role_type)
    return role_type in selected_role_types


def _expand_location_query(location_query: str) -> set[str]:
    """Expand a location query into tolerant equivalents."""
    normalized = _normalize_search_text(location_query)
    if not normalized:
        return set()

    values = {normalized}

    if normalized == "remote":
        values.update({"telework", "work from home", "wfh"})

    if normalized == "hybrid":
        values.add("flexible hybrid")

    if normalized in {"onsite", "on-site", "on site"}:
        values.update({"onsite", "on-site", "on site", "in office", "in-office"})

    if normalized in US_STATE_CODE_TO_NAME:
        values.add(US_STATE_CODE_TO_NAME[normalized])

    if normalized in US_STATE_NAME_TO_CODE:
        values.add(US_STATE_NAME_TO_CODE[normalized])

    return values


def should_match_location_query(
    *,
    location_query: str | None,
    title: str | None,
    location: str | None,
    location_display: str | None,
    description: str | None,
    remote_flag: bool | None,
    remote_type: str | None,
) -> bool:
    """Return True when a job matches a flexible location query."""
    normalized_query = normalize_location_query(location_query)
    if not normalized_query:
        return True

    haystack = _normalize_search_text(
        " ".join(
            part
            for part in [
                title or "",
                location or "",
                location_display or "",
                description or "",
                remote_type or "",
                "remote" if remote_flag else "",
            ]
            if part
        )
    )

    if not haystack:
        return False

    expanded = _expand_location_query(normalized_query)
    if any(value in haystack for value in expanded):
        return True

    query_tokens = [token for token in re.split(r"[,\s]+", normalized_query) if token]
    if len(query_tokens) <= 1:
        return False

    expanded_tokens = set(query_tokens)

    for token in query_tokens:
        if token in US_STATE_CODE_TO_NAME:
            expanded_tokens.add(US_STATE_CODE_TO_NAME[token])

        if token in US_STATE_NAME_TO_CODE:
            expanded_tokens.add(US_STATE_NAME_TO_CODE[token])

    return all(token in haystack for token in expanded_tokens)


def should_include_job(
    *,
    title: str | None,
    normalized_level: str | None,
    normalized_role_type: str | None,
    options: JobFilterOptions,
) -> bool:
    """Return True when a job passes both level and role filters."""
    return (
        matches_level_filter(
            title=title,
            normalized_level=normalized_level,
            selected_levels=options.selected_levels,
        )
        and matches_role_type_filter(
            normalized_role_type=normalized_role_type,
            selected_role_types=options.selected_role_types,
        )
    )