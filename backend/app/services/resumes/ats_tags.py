"""Helpers for deriving lightweight ATS tags from parsed resume data."""

from __future__ import annotations

from typing import Any


def extract_ats_tags(parsed_json: dict[str, Any]) -> list[str]:
    """Extract lightweight ATS tags from parsed resume JSON.

    Tags are intentionally simple and useful for UI display and coarse matching.
    The full parsed JSON remains the source of truth.

    Args:
        parsed_json: Parsed resume payload.

    Returns:
        A deduplicated ordered list of ATS-style tags.
    """
    summary = parsed_json.get("summary", {}) or {}
    skills = parsed_json.get("skills", {}) or {}
    experience = parsed_json.get("experience", []) or []

    tags: list[str] = []

    seniority = summary.get("seniority")
    if isinstance(seniority, str) and seniority.strip():
        tags.append(seniority.strip())

    estimated_years = summary.get("estimated_years_experience")
    if isinstance(estimated_years, int):
        tags.append(f"{estimated_years}_years_experience")

    for role_signal in summary.get("primary_role_signals", []) or []:
        if isinstance(role_signal, str) and role_signal.strip():
            tags.append(role_signal.strip())

    for keyword in summary.get("top_skill_keywords", []) or []:
        if isinstance(keyword, str) and keyword.strip():
            tags.append(keyword.strip())

    for skill in skills.get("normalized", []) or []:
        if isinstance(skill, str) and skill.strip():
            tags.append(skill.strip())

    for item in experience:
        if not isinstance(item, dict):
            continue
        for skill in item.get("normalized_skills", []) or []:
            if isinstance(skill, str) and skill.strip():
                tags.append(skill.strip())

    return _dedupe_preserve_order(tags)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """Deduplicate string values while preserving order.

    Args:
        values: Raw tag values.

    Returns:
        Deduplicated ordered tag list.
    """
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue

        lowered = normalized.casefold()
        if lowered in seen:
            continue

        seen.add(lowered)
        result.append(normalized)

    return result