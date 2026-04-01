"""Helpers for stripping HTML and cleaning noisy job descriptions."""

from __future__ import annotations

import html
import re
from typing import Iterable


HTML_TAG_RE = re.compile(r"<[^>]+>")
MULTISPACE_RE = re.compile(r"[ \t]+")
MULTINEWLINE_RE = re.compile(r"\n{3,}")
BULLET_PREFIX_RE = re.compile(r"^\s*[-*•◦▪]+\s*")

NOISE_PATTERNS = [
    re.compile(r"click here to apply.*", re.IGNORECASE),
    re.compile(r"apply now.*", re.IGNORECASE),
    re.compile(r"please reference job id.*", re.IGNORECASE),
    re.compile(r"equal opportunity employer.*", re.IGNORECASE),
    re.compile(r"e-verify.*", re.IGNORECASE),
    re.compile(r"recruitment fraud.*", re.IGNORECASE),
    re.compile(r"beware of scams.*", re.IGNORECASE),
    re.compile(r"follow us on .*", re.IGNORECASE),
    re.compile(r"visit our careers page.*", re.IGNORECASE),
    re.compile(r"this job has been posted by.*", re.IGNORECASE),
]

SPAM_LINE_PATTERNS = [
    re.compile(r".*mention the word.*", re.IGNORECASE),
    re.compile(r".*to prove you read this.*", re.IGNORECASE),
    re.compile(r".*buy bitcoin.*", re.IGNORECASE),
    re.compile(r".*crypto.*payment.*", re.IGNORECASE),
    re.compile(r".*contact.*telegram.*", re.IGNORECASE),
    re.compile(r".*contact.*whatsapp.*", re.IGNORECASE),
    re.compile(r".*text us at.*", re.IGNORECASE),
    re.compile(r".*text me at.*", re.IGNORECASE),
    re.compile(r".*email us immediately.*", re.IGNORECASE),
]

FOOTER_START_PATTERNS = [
    re.compile(r"^equal opportunity employer\b", re.IGNORECASE),
    re.compile(r"^e-verify\b", re.IGNORECASE),
    re.compile(r"^reasonable accommodation\b", re.IGNORECASE),
    re.compile(r"^privacy policy\b", re.IGNORECASE),
    re.compile(r"^terms of use\b", re.IGNORECASE),
]


def strip_html(raw_text: str | None) -> str:
    """Remove HTML tags and normalize escaped content."""
    if not raw_text:
        return ""

    text = html.unescape(raw_text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div\s*>", "\n", text, flags=re.IGNORECASE)
    text = HTML_TAG_RE.sub(" ", text)
    text = text.replace("\r", "\n")
    text = MULTISPACE_RE.sub(" ", text)
    text = MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


def normalize_whitespace(text: str | None) -> str:
    """Collapse noisy whitespace while preserving readable paragraph breaks."""
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = MULTISPACE_RE.sub(" ", text)
    text = MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


def remove_noise_lines(text: str | None) -> str:
    """Remove provider noise and obvious junk lines."""
    if not text:
        return ""

    cleaned_lines: list[str] = []
    skipping_footer = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        if skipping_footer:
            continue

        if any(pattern.match(stripped) for pattern in FOOTER_START_PATTERNS):
            skipping_footer = True
            continue

        if any(pattern.match(stripped) for pattern in NOISE_PATTERNS):
            continue

        if any(pattern.match(stripped) for pattern in SPAM_LINE_PATTERNS):
            continue

        cleaned_lines.append(stripped)

    cleaned = "\n".join(cleaned_lines)
    cleaned = MULTINEWLINE_RE.sub("\n\n", cleaned)
    return cleaned.strip()


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    """Deduplicate strings while preserving original order."""
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        lowered = normalized.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)

    return result


def dedupe_lines(text: str | None) -> str:
    """Remove repeated lines while preserving order."""
    if not text:
        return ""

    kept = dedupe_preserve_order(text.splitlines())
    return "\n".join(kept).strip()


def truncate_description(text: str | None, max_chars: int = 12000) -> str:
    """Keep descriptions serverless-safe and UI-friendly."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].strip()


def clean_bullet_text(text: str) -> str:
    """Normalize bullet point text."""
    text = BULLET_PREFIX_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -•*")


def clean_description(raw_text: str | None) -> str:
    """Run the full text cleanup pipeline for job descriptions."""
    text = strip_html(raw_text)
    text = remove_noise_lines(text)
    text = dedupe_lines(text)
    text = normalize_whitespace(text)
    text = truncate_description(text)
    return text