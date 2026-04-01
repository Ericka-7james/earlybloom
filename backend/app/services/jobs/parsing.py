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


def _normalize_header(value: str) -> str:
    return value.strip().lower().rstrip(":")


def _normalize_money(raw: str) -> int | None:
    value = raw.strip().lower().replace(",", "")
    if value.endswith("k"):
        numeric = value[:-1]
        if numeric.isdigit():
            return int(numeric) * 1000
        return None
    if value.isdigit():
        return int(value)
    return None


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
    """Infer experience level using lightweight keyword rules."""
    haystack = " ".join(filter(None, [title, description])).lower()

    if any(term in haystack for term in {"entry level", "entry-level", "new grad", "graduate", "early career", "associate"}):
        return "entry-level"
    if any(term in haystack for term in {"junior", "jr.", "jr ", "level i", "level 1"}):
        return "junior"
    if any(term in haystack for term in {"senior", "sr.", "sr ", "staff", "principal", "lead"}):
        return "senior"
    if any(term in haystack for term in {"mid", "mid-level", "intermediate", "level ii", "level 2"}):
        return "mid"

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
            # Accept short non-bullet lines in sections too.
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

    # Fallback: search full description if sectioned qualifications are thin.
    if not required_skills and description:
        required_skills = extract_skills_from_items(split_lines(description))

    return required_skills, preferred_skills