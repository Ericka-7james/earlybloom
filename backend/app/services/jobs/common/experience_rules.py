from __future__ import annotations

import re
from typing import Any

from app.services.jobs.common.title_rules import (
    is_early_career_title,
    is_obviously_senior_title,
)

GENERAL_EXPERIENCE_PATTERNS = [
    re.compile(r"\b(\d+)\+?\s+years?\s+of\s+experience\b", re.IGNORECASE),
    re.compile(r"\bminimum\s+of\s+(\d+)\+?\s+years?\b", re.IGNORECASE),
    re.compile(r"\bat\s+least\s+(\d+)\s+years?\b", re.IGNORECASE),
]

PRODUCTION_EXPERIENCE_PATTERNS = [
    re.compile(
        r"\b(\d+)\+?\s+years?\s+of\s+(?:professional|production|hands[- ]on)\s+"
        r"(?:software|engineering|development|devops|security|data)\s+experience\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d+)\+?\s+years?\s+(?:building|developing|supporting|shipping)\s+"
        r"(?:software|applications|platforms|systems)\b",
        re.IGNORECASE,
    ),
]

EARLY_CAREER_TAG_SIGNALS = {
    "recent graduates",
    "recent graduate",
    "students",
    "student",
    "internship",
    "intern",
    "apprenticeship",
    "fellowship",
    "pathways",
    "new grad",
}


def _extract_min_years(patterns: list[re.Pattern[str]], text: str) -> int | None:
    values: list[int] = []
    for pattern in patterns:
        for match in pattern.finditer(text or ""):
            try:
                values.append(int(match.group(1)))
            except (TypeError, ValueError, IndexError):
                continue
    return min(values) if values else None


def extract_general_years_requirement(text: str) -> int | None:
    return _extract_min_years(GENERAL_EXPERIENCE_PATTERNS, text)


def extract_production_years_requirement(text: str) -> int | None:
    return _extract_min_years(PRODUCTION_EXPERIENCE_PATTERNS, text)


def has_early_career_tag_signal(tags: list[str] | None) -> bool:
    normalized = {str(tag or "").strip().casefold() for tag in (tags or [])}
    return any(signal in normalized for signal in EARLY_CAREER_TAG_SIGNALS)


def infer_experience_level_from_text(
    *,
    title: str,
    description: str,
    tags: list[str] | None = None,
) -> str:
    """
    Layer 1 friendly inference:
    - early-career tags/titles win
    - obvious senior titles win
    - general 1-3 years stays softer
    - production-specific 3+ years is more serious
    """
    title = str(title or "")
    description = str(description or "")

    if is_early_career_title(title) or has_early_career_tag_signal(tags):
        return "entry-level"

    if is_obviously_senior_title(title):
        return "senior"

    production_years = extract_production_years_requirement(description)
    general_years = extract_general_years_requirement(description)

    if production_years is not None:
        if production_years <= 1:
            return "entry-level"
        if production_years <= 3:
            return "mid"
        if production_years >= 4:
            return "senior"

    if general_years is not None:
        if general_years <= 1:
            return "entry-level"
        if general_years <= 3:
            return "junior"
        if general_years == 4:
            return "mid"
        if general_years >= 5:
            return "senior"

    lowered = f"{title} {description}".casefold()

    soft_mid_markers = [
        "2+ years",
        "3+ years",
        "some experience",
        "prior experience",
        "experience preferred",
    ]
    if any(marker in lowered for marker in soft_mid_markers):
        return "mid"

    return "unknown"


def is_hard_senior_experience_requirement(
    *,
    title: str,
    description: str,
) -> bool:
    """
    Use this for strong provider-side exclusion or downgrading logic.
    This is intentionally stricter than general experience inference.
    """
    if is_obviously_senior_title(title):
        return True

    production_years = extract_production_years_requirement(description)
    if production_years is not None and production_years >= 4:
        return True

    lowered = str(description or "").casefold()
    hard_markers = [
        "staff level",
        "principal level",
        "technical leadership",
        "architecture ownership",
        "people management",
        "mentor junior engineers",
        "lead a team of engineers",
    ]
    return any(marker in lowered for marker in hard_markers)