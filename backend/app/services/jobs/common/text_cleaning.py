from __future__ import annotations

import html
import re
from typing import Any

HTML_TAG_RE = re.compile(r"<[^>]+>")
BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•·▪‣◦]|(?:\d+[\).\s]))\s*")


def strip_html(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*/p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_paragraph_text(text: str) -> str:
    value = str(text or "")
    if not value:
        return ""

    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    value = html.unescape(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def collapse_whitespace(text: str) -> str:
    return " ".join(str(text or "").split())


def split_bullets(text: str, *, max_items: int = 8, min_length: int = 2) -> list[str]:
    """
    Split mixed provider text into useful bullet-like items.
    Works with:
    - newline bullets
    - numbered lists
    - dense semicolon-separated fragments
    """
    value = normalize_paragraph_text(text)
    if not value:
        return []

    raw_parts: list[str] = []

    if "\n" in value:
        for line in value.splitlines():
            cleaned = BULLET_PREFIX_RE.sub("", line).strip(" -•\t")
            if cleaned:
                raw_parts.append(cleaned)

    if not raw_parts:
        semicolon_parts = [part.strip() for part in value.split(";")]
        raw_parts.extend(part for part in semicolon_parts if part)

    if not raw_parts:
        sentence_parts = re.split(r"(?<=[.!?])\s+", value)
        raw_parts.extend(part.strip() for part in sentence_parts if part.strip())

    deduped: list[str] = []
    seen: set[str] = set()

    for part in raw_parts:
        cleaned = collapse_whitespace(part).strip(" -•\t")
        if len(cleaned) < min_length:
            continue
        folded = cleaned.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        deduped.append(cleaned)
        if len(deduped) >= max_items:
            break

    return deduped