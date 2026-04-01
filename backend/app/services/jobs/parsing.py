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

_EXPERIENCE_LEVEL_ORDER = {
    "unknown": 0,
    "entry-level": 1,
    "junior": 2,
    "mid-level": 3,
    "senior": 4,
}

_TITLE_PATTERNS_BY_LEVEL: dict[str, tuple[str, ...]] = {
    "senior": (
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
    ),
    "mid-level": (
        r"\bmid[-\s]?level\b",
        r"\bintermediate\b",
        r"\bii\b",
        r"\biii\b",
        r"\blevel\s?2\b",
        r"\blevel\s?3\b",
        r"\bjourneyman\b",
        r"\bexperienced\b",
    ),
    "junior": (
        r"\bjunior\b",
        r"\bjr\.?\b",
        r"\bassociate\b",
        r"\bgraduate\b",
        r"\bnew grad\b",
        r"\bearly career\b",
        r"\bapprentice\b",
        r"\btrainee\b",
    ),
    "entry-level": (
        r"\bentry[-\s]?level\b",
        r"\bintern(ship)?\b",
        r"\bco-?op\b",
        r"\bfellow(ship)?\b",
        r"\brotation(?:al)?\b",
        r"\bdevelopment program\b",
    ),
}

_DESCRIPTION_PATTERNS_BY_LEVEL: dict[str, tuple[str, ...]] = {
    "senior": (
        r"\b(?:8|9|10|1[1-9]|[2-9][0-9])\+?\s+years?\b",
        r"\b(?:minimum of|at least)\s+(?:8|9|10|1[1-9]|[2-9][0-9])\s+years?\b",
        r"\bmanag(?:e|ing)\b",
        r"\blead(?:ership)?\b",
        r"\bown(?:er|ership)\b",
        r"\bmentor(?:ing)?\b",
        r"\bstrategy\b",
        r"\broadmap\b",
    ),
    "mid-level": (
        r"\b(?:3|4|5|6|7)\+?\s+years?\b",
        r"\b(?:minimum of|at least)\s+(?:3|4|5|6|7)\s+years?\b",
        r"\bintermediate\b",
        r"\bmid[-\s]?level\b",
    ),
    "junior": (
        r"\b(?:0|1|2)\+?\s+years?\b",
        r"\b(?:0\s*-\s*2|1\s*-\s*2|0\s*-\s*3)\s+years?\b",
        r"\b(?:minimum of|at least)\s+(?:0|1|2)\s+years?\b",
        r"\bnew grad\b",
        r"\brecent graduate\b",
        r"\bearly career\b",
        r"\bentry into\b",
    ),
    "entry-level": (
        r"\bno experience required\b",
        r"\bno prior experience\b",
        r"\bentry[-\s]?level\b",
        r"\bintern(ship)?\b",
        r"\btraining provided\b",
    ),
}

_NEGATIVE_TITLE_PATTERNS = (
    r"\bassistant manager\b",
    r"\bproject manager\b",
    r"\bproduct manager\b",
)

_TITLE_WEIGHT = 3
_DESCRIPTION_WEIGHT = 1


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


def _normalize_experience_text(value: str | None) -> str:
    """Normalize text used for experience-level classification."""
    return " ".join(str(value or "").strip().lower().split())


def _count_pattern_hits(text: str, patterns: tuple[str, ...]) -> int:
    """Count regex pattern hits within normalized text."""
    return sum(1 for pattern in patterns if re.search(pattern, text))


def _extract_year_values(text: str) -> list[int]:
    """Extract likely years-of-experience integers from text."""
    values: list[int] = []

    for match in re.finditer(r"\b(\d{1,2})\+?\s+years?\b", text):
        values.append(int(match.group(1)))

    for match in re.finditer(r"\b(\d{1,2})\s*-\s*(\d{1,2})\s+years?\b", text):
        values.append(int(match.group(2)))

    for match in re.finditer(
        r"\b(?:minimum of|at least)\s+(\d{1,2})\s+years?\b",
        text,
    ):
        values.append(int(match.group(1)))

    return values


def _classify_years_signal(years: list[int]) -> str:
    """Map extracted years-of-experience values to a normalized level."""
    if not years:
        return "unknown"

    strongest = max(years)

    if strongest >= 8:
        return "senior"
    if strongest >= 3:
        return "mid-level"
    if strongest >= 0:
        return "junior"

    return "unknown"


def _best_scored_level(scores: dict[str, int]) -> str:
    """Return the highest-confidence experience level from weighted scores."""
    best_level = "unknown"
    best_score = 0

    for level, score in scores.items():
        if score > best_score:
            best_level = level
            best_score = score
        elif score == best_score and score > 0:
            if _EXPERIENCE_LEVEL_ORDER[level] > _EXPERIENCE_LEVEL_ORDER[best_level]:
                best_level = level

    return best_level if best_score > 0 else "unknown"


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

    Detection strategy:
    1. Strong title signals win first.
    2. Description signals contribute weighted evidence.
    3. Years-of-experience evidence acts as a structured fallback.
    4. Conflicting weak signals fall back to the strongest weighted level.
    """
    normalized_title = _normalize_experience_text(title)
    normalized_description = _normalize_experience_text(description)

    if not normalized_title and not normalized_description:
        return "unknown"

    for pattern in _NEGATIVE_TITLE_PATTERNS:
        if re.search(pattern, normalized_title):
            normalized_title = re.sub(pattern, "", normalized_title)

    title_scores = {
        level: _count_pattern_hits(normalized_title, patterns) * _TITLE_WEIGHT
        for level, patterns in _TITLE_PATTERNS_BY_LEVEL.items()
    }
    description_scores = {
        level: _count_pattern_hits(normalized_description, patterns) * _DESCRIPTION_WEIGHT
        for level, patterns in _DESCRIPTION_PATTERNS_BY_LEVEL.items()
    }

    combined_scores = {
        level: title_scores.get(level, 0) + description_scores.get(level, 0)
        for level in ("entry-level", "junior", "mid-level", "senior")
    }

    title_winner = _best_scored_level(title_scores)
    if title_winner == "senior":
        return "senior"

    if title_winner in {"entry-level", "junior"} and title_scores[title_winner] >= _TITLE_WEIGHT:
        return title_winner

    years_signal = _classify_years_signal(_extract_year_values(normalized_description))
    if years_signal == "senior":
        return "senior"

    combined_winner = _best_scored_level(combined_scores)
    if combined_winner != "unknown":
        if years_signal != "unknown":
            if _EXPERIENCE_LEVEL_ORDER[years_signal] > _EXPERIENCE_LEVEL_ORDER[combined_winner]:
                return years_signal
        return combined_winner

    return years_signal


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