"""Shared lightweight parsing helpers for turning large job blobs into structured fields."""

from __future__ import annotations

import re
from typing import Iterable

from app.services.jobs.cleaning import clean_bullet_text, dedupe_preserve_order
from app.services.jobs.constants import (
    COMMON_PREFERRED_MARKERS,
    COMMON_QUALIFICATION_HEADERS,
    COMMON_REQUIRED_SKILLS,
    COMMON_RESPONSIBILITY_HEADERS,
    HYBRID_KEYWORDS,
    ONSITE_KEYWORDS,
    REMOTE_KEYWORDS,
)
from app.services.jobs.providers.common.experience_rules import (
    extract_general_years_requirement,
    extract_production_years_requirement,
    infer_experience_level_from_text,
)
from app.services.jobs.providers.common.title_rules import (
    is_early_career_title,
    is_obviously_senior_title,
)


HEADER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 ,/&()'’-]{2,80}:?$")
BULLET_RE = re.compile(r"^\s*[-*•◦▪]+\s+")
SALARY_RANGE_RE = re.compile(
    r"(?P<currency>\$|USD)?\s*(?P<min>\d{2,3}(?:,\d{3})+|\d{2,3}k)\s*(?:-|to|–|—)\s*(?P<max>\d{2,3}(?:,\d{3})+|\d{2,3}k)",
    re.IGNORECASE,
)
SINGLE_SALARY_RE = re.compile(
    r"(?P<currency>\$|USD)\s*(?P<amount>\d{2,3}(?:,\d{3})+|\d{2,3}k)",
    re.IGNORECASE,
)

_SOFT_MID_PATTERNS = (
    r"\bsoftware engineer ii\b",
    r"\bengineer ii\b",
    r"\bdeveloper ii\b",
    r"\banalyst ii\b",
    r"\bspecialist ii\b",
    r"\blevel\s?2\b",
    r"\bmid[-\s]?level\b",
    r"\bintermediate\b",
    r"\bjourneyman\b",
)

_STRONG_SENIOR_DESCRIPTION_PATTERNS = (
    r"\b(?:8|9|10|1[1-9]|[2-9][0-9])\+?\s+years?\b",
    r"\b(?:minimum of|at least)\s+(?:8|9|10|1[1-9]|[2-9][0-9])\s+years?\b",
    r"\bpeople management\b",
    r"\bmanage a team\b",
    r"\blead a team\b",
    r"\bengineering manager\b",
    r"\barchitecture ownership\b",
    r"\bexecutive stakeholder\b",
)

_NEGATIVE_TITLE_PATTERNS = (
    r"\bassistant manager\b",
    r"\bproject manager\b",
    r"\bproduct manager\b",
)


def _normalize_header(value: str) -> str:
    return value.strip().lower().rstrip(":")


def _normalize_money(raw: str) -> int | None:
    value = raw.strip().lower().replace(",", "")
    if value.endswith("k"):
        numeric = value[:-1]
        if numeric.replace(".", "", 1).isdigit():
            return int(float(numeric) * 1000)
        return None
    if value.isdigit():
        return int(value)
    return None


def _normalize_experience_text(value: str | None) -> str:
    """Normalize text used for experience-level classification."""
    return " ".join(str(value or "").strip().lower().split())


def _is_soft_mid_title(title: str | None) -> bool:
    normalized_title = _normalize_experience_text(title)
    if not normalized_title:
        return False
    return any(re.search(pattern, normalized_title) for pattern in _SOFT_MID_PATTERNS)


def _has_strong_senior_description_signal(description: str | None) -> bool:
    normalized_description = _normalize_experience_text(description)
    if not normalized_description:
        return False
    return any(
        re.search(pattern, normalized_description)
        for pattern in _STRONG_SENIOR_DESCRIPTION_PATTERNS
    )


def split_lines(text: str | None) -> list[str]:
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def detect_remote_type(title: str | None, location: str | None, description: str | None) -> str:
    """Infer remote type from title, location, and description."""
    haystack = " ".join(filter(None, [title, location, description])).lower()

    if any(keyword in haystack for keyword in HYBRID_KEYWORDS):
        return "hybrid"
    if any(keyword in haystack for keyword in ONSITE_KEYWORDS):
        return "onsite"
    if any(keyword in haystack for keyword in REMOTE_KEYWORDS):
        return "remote"
    return "unknown"


def detect_experience_level(title: str | None, description: str | None) -> str:
    """Detect a normalized experience level from title and description.

    Returns one of:
    - entry-level
    - junior
    - mid-level
    - senior
    - unknown

    EarlyBloom strategy:
    1. Obvious senior titles lose immediately.
    2. Early-career titles win quickly.
    3. Shared experience rules interpret years more carefully.
    4. 3 years general experience is softer than 3 years production software experience.
    """
    normalized_title = _normalize_experience_text(title)
    normalized_description = _normalize_experience_text(description)

    if not normalized_title and not normalized_description:
        return "unknown"

    for pattern in _NEGATIVE_TITLE_PATTERNS:
        if re.search(pattern, normalized_title):
            normalized_title = re.sub(pattern, "", normalized_title).strip()

    if is_obviously_senior_title(normalized_title):
        return "senior"

    if is_early_career_title(normalized_title):
        return "entry-level"

    shared_level = infer_experience_level_from_text(
        title=normalized_title,
        description=normalized_description,
        tags=None,
    )
    shared_level = _normalize_level_value(shared_level)

    production_years = extract_production_years_requirement(normalized_description)
    general_years = extract_general_years_requirement(normalized_description)

    if production_years is not None:
        if production_years >= 4:
            return "senior"
        if production_years == 3:
            return "mid-level"
        if production_years <= 2:
            return "junior"

    if general_years is not None:
        if general_years >= 5:
            return "senior"
        if general_years in {3, 4}:
            # Keep this softer for EarlyBloom. 3-4 general years is often
            # still a realistic stretch, not an automatic hard seniority wall.
            return "mid-level"
        if general_years <= 2:
            return "junior"

    if _has_strong_senior_description_signal(normalized_description):
        return "senior"

    if _is_soft_mid_title(normalized_title):
        return "mid-level"

    return shared_level


def _normalize_level_value(level: str | None) -> str:
    normalized = str(level or "").strip().lower()

    if normalized in {"entry", "entry-level"}:
        return "entry-level"
    if normalized == "junior":
        return "junior"
    if normalized in {"mid", "midlevel", "mid-level"}:
        return "mid-level"
    if normalized == "senior":
        return "senior"
    return "unknown"


def detect_employment_type(description: str | None) -> str | None:
    """Extract employment type from text."""
    if not description:
        return None

    text = description.lower()
    candidates = [
        ("full-time", {"full time", "full-time"}),
        ("part-time", {"part time", "part-time"}),
        ("contract", {"contract", "contractor"}),
        ("temporary", {"temporary", "temp"}),
        ("internship", {"intern", "internship"}),
    ]

    for label, terms in candidates:
        if any(term in text for term in terms):
            return label

    return None


def extract_salary(description: str | None) -> tuple[int | None, int | None, str | None]:
    """Extract a salary range from text when possible."""
    if not description:
        return None, None, None

    match = SALARY_RANGE_RE.search(description)
    if match:
        min_value = _normalize_money(match.group("min"))
        max_value = _normalize_money(match.group("max"))
        if min_value and max_value:
            return min_value, max_value, "USD"

    single = SINGLE_SALARY_RE.search(description)
    if single:
        amount = _normalize_money(single.group("amount"))
        if amount:
            return amount, amount, "USD"

    return None, None, None


def extract_summary(text: str | None, max_length: int = 320) -> str:
    """Get a concise summary from the first useful paragraph."""
    if not text:
        return ""

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for paragraph in paragraphs:
        if len(paragraph) < 40:
            continue
        summary = paragraph
        if len(summary) > max_length:
            summary = summary[: max_length - 3].rstrip() + "..."
        return summary

    return ""


def _is_header(line: str) -> bool:
    if not line:
        return False
    if len(line) > 90:
        return False
    return bool(HEADER_RE.match(line))


def _collect_bullets_under_section(lines: list[str], header_set: set[str]) -> list[str]:
    """Collect bullet items that appear below a known section header."""
    items: list[str] = []
    current_section: str | None = None

    for line in lines:
        normalized = _normalize_header(line)

        if _is_header(line):
            current_section = normalized
            continue

        if current_section in header_set and BULLET_RE.match(line):
            items.append(clean_bullet_text(line))
        elif current_section in header_set and len(line) < 220:
            items.append(clean_bullet_text(line))

    return dedupe_preserve_order(items)


def extract_responsibilities(text: str | None) -> list[str]:
    """Extract likely responsibilities from sectioned description text."""
    lines = split_lines(text)
    return _collect_bullets_under_section(lines, COMMON_RESPONSIBILITY_HEADERS)


def extract_qualifications(text: str | None) -> list[str]:
    """Extract likely qualifications from sectioned description text."""
    lines = split_lines(text)
    return _collect_bullets_under_section(lines, COMMON_QUALIFICATION_HEADERS)


def extract_skills_from_items(items: Iterable[str]) -> list[str]:
    """Extract normalized skills from bullet items."""
    found: list[str] = []

    for item in items:
        lowered = item.lower()
        for skill in COMMON_REQUIRED_SKILLS:
            if skill in lowered:
                found.append(skill)

    return dedupe_preserve_order(found)


def split_required_and_preferred_skills(
    qualifications: list[str],
    description: str | None,
) -> tuple[list[str], list[str]]:
    """Split skills into required and preferred buckets using surrounding language."""
    required_items: list[str] = []
    preferred_items: list[str] = []

    for item in qualifications:
        lowered = item.lower()
        if any(marker in lowered for marker in COMMON_PREFERRED_MARKERS):
            preferred_items.append(item)
        else:
            required_items.append(item)

    required_skills = extract_skills_from_items(required_items)
    preferred_skills = extract_skills_from_items(preferred_items)

    if not required_skills and description:
        required_skills = extract_skills_from_items(split_lines(description))

    return required_skills, preferred_skills