"""Filtering utilities for job ingestion and ranking."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


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

SENIOR_TITLE_PATTERNS = [
    r"\bchief\b",
    r"\bciso\b",
    r"\bcto\b",
    r"\bcio\b",
    r"\bvp\b",
    r"\bvice president\b",
    r"\bdirector\b",
    r"\bhead\b",
    r"\bprincipal\b",
    r"\bstaff\b",
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\blead\b",
    r"\bmanager\b",
    r"\barchitect\b",
    r"\bofficer\b",
    r"\bcommander\b",
]

NOT_EARLY_CAREER_TITLE_PATTERNS = [
    r"\bit specialist\b",
    r"\bsystems administration\b",
    r"\bsysadmin\b",
    r"\bnetwork\b",
    r"\bnetworking\b",
    r"\bcustspt\b",
    r"\bcustomer support\b",
    r"\bsecurity officer\b",
    r"\binformation security\b",
    r"\binfosec\b",
    r"\btitle 32\b",
    r"\bnational guard\b",
    r"\bair national guard\b",
    r"\barmy national guard\b",
    r"\bprogram manager\b",
    r"\bproject manager\b",
]

EXPLICIT_JUNIOR_TITLE_PATTERNS = [
    r"\bjunior\b",
    r"\bjr\.?\b",
    r"\bentry\b",
    r"\bentry-level\b",
    r"\bnew grad\b",
    r"\brecent graduate\b",
    r"\bgraduate\b",
    r"\bearly career\b",
    r"\bassociate\b",
    r"\bintern\b",
    r"\bapprentice\b",
    r"\btrainee\b",
    r"\bfellow(ship)?\b",
    r"\bdevelopment program\b",
    r"\brotational\b",
]

JUNIOR_SAFE_TITLE_PATTERNS = [
    r"\bjunior software engineer\b",
    r"\bsoftware engineer i\b",
    r"\bsoftware engineer level 1\b",
    r"\bentry-level software engineer\b",
    r"\bassociate software engineer\b",
    r"\bfrontend developer\b",
    r"\bbackend developer\b",
    r"\bfull stack developer\b",
    r"\bqa engineer\b",
    r"\btest engineer\b",
    r"\bdata analyst\b",
    r"\bproduct analyst\b",
    r"\bsupport engineer\b",
    r"\bimplementation specialist\b",
    r"\bsolutions engineer\b",
    r"\bsecurity analyst\b",
    r"\bbusiness analyst\b",
]

MID_OR_HIGHER_HINTS = [
    r"\bii\b",
    r"\biii\b",
    r"\blevel\s?2\b",
    r"\blevel\s?3\b",
    r"\bintermediate\b",
    r"\bjourneyman\b",
    r"\b5\+?\s+years?\b",
    r"\b6\+?\s+years?\b",
    r"\b7\+?\s+years?\b",
    r"\b8\+?\s+years?\b",
]


@dataclass(frozen=True)
class JobFilterOptions:
    """Normalized filter options used during job filtering."""

    selected_levels: set[str]
    selected_role_types: set[str]


def _normalize_text(value: str | None) -> str:
    """Normalize text for regex matching."""
    return " ".join(str(value or "").strip().lower().split())


def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Return True when text matches any regex in the provided list."""
    return any(re.search(pattern, text) for pattern in patterns)


def normalize_levels(levels: Iterable[str] | None) -> set[str]:
    """Normalize user-selected job levels."""
    if not levels:
        return set(DEFAULT_LEVELS)

    normalized = {
        str(level).strip().lower()
        for level in levels
        if str(level).strip().lower() in SUPPORTED_LEVELS
    }
    return normalized or set(DEFAULT_LEVELS)


def normalize_role_types(role_types: Iterable[str] | None) -> set[str]:
    """Normalize user-selected role types."""
    if not role_types:
        return set()

    return {
        str(role_type).strip().lower()
        for role_type in role_types
        if str(role_type).strip().lower() in SUPPORTED_ROLE_TYPES
    }


def build_filter_options(
    levels: Iterable[str] | None,
    role_types: Iterable[str] | None,
) -> JobFilterOptions:
    """Build normalized filter options."""
    return JobFilterOptions(
        selected_levels=normalize_levels(levels),
        selected_role_types=normalize_role_types(role_types),
    )


def is_obviously_senior_title(title: str | None) -> bool:
    """Return True when the title clearly signals a senior role."""
    normalized_title = _normalize_text(title)
    if not normalized_title:
        return False

    return _matches_any_pattern(normalized_title, SENIOR_TITLE_PATTERNS)


def is_not_early_career_title(title: str | None) -> bool:
    """Return True for titles that are usually not a fit for early-career users."""
    normalized_title = _normalize_text(title)
    if not normalized_title:
        return False

    if _matches_any_pattern(normalized_title, NOT_EARLY_CAREER_TITLE_PATTERNS):
        return True

    if _matches_any_pattern(normalized_title, MID_OR_HIGHER_HINTS):
        return True

    return False


def has_explicit_junior_signal(title: str | None) -> bool:
    """Return True when a title contains explicit entry/junior wording."""
    normalized_title = _normalize_text(title)
    if not normalized_title:
        return False

    return _matches_any_pattern(normalized_title, EXPLICIT_JUNIOR_TITLE_PATTERNS)


def is_junior_safe_unknown_title(title: str | None) -> bool:
    """Return True only for unknown-level roles that are clearly junior-safe."""
    normalized_title = _normalize_text(title)
    if not normalized_title:
        return False

    if is_obviously_senior_title(normalized_title):
        return False

    if is_not_early_career_title(normalized_title) and not has_explicit_junior_signal(
        normalized_title
    ):
        return False

    if has_explicit_junior_signal(normalized_title):
        return True

    return _matches_any_pattern(normalized_title, JUNIOR_SAFE_TITLE_PATTERNS)


def matches_level_filter(
    *,
    title: str | None,
    normalized_level: str | None,
    selected_levels: set[str],
) -> bool:
    """Check whether a job matches selected experience-level filters."""
    level = _normalize_text(normalized_level)

    if is_obviously_senior_title(title):
        return False

    if is_not_early_career_title(title) and not has_explicit_junior_signal(title):
        if selected_levels.issubset(DEFAULT_LEVELS):
            return False

    if level == "mid-level" and "mid-level" not in selected_levels:
        return False

    if level == "senior" and "senior" not in selected_levels:
        return False

    if level in selected_levels:
        if level in DEFAULT_LEVELS and is_not_early_career_title(title):
            return has_explicit_junior_signal(title)
        return True

    if level == "unknown":
        return is_junior_safe_unknown_title(title)

    return False


def matches_role_type_filter(
    *,
    normalized_role_type: str | None,
    selected_role_types: set[str],
) -> bool:
    """Check whether a job matches selected role-type filters."""
    if not selected_role_types:
        return True

    role_type = _normalize_text(normalized_role_type)
    return role_type in selected_role_types


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