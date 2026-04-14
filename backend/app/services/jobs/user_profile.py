"""Resolved job-profile service for scoring and filtering."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.db.database import ResumeRepository, get_supabase_admin
from app.services.auth_service import fetch_profile_for_user_id


DEFAULT_RESOLVED_JOB_PROFILE: dict[str, Any] = {
    "desiredLevels": ["entry-level", "junior"],
    "preferredRoleTypes": [],
    "preferredWorkplaceTypes": [],
    "preferredLocations": [],
    "skills": [],
    "isLgbtFriendlyOnly": False,
}


def resolve_job_profile_for_user_id(user_id: str) -> dict[str, Any]:
    """Resolve the current user's scoring profile from mock or live data."""
    settings = get_settings()

    if settings.JOB_DATA_MODE == "mock":
        return dict(DEFAULT_RESOLVED_JOB_PROFILE)

    profile_row = fetch_profile_for_user_id(user_id)
    latest_resume = _fetch_latest_resume_for_user_id(user_id)
    parsed_json = latest_resume.get("parsed_json") if latest_resume else None

    desired_levels = _normalize_string_list(
        profile_row.get("desired_levels") if profile_row else None
    ) or list(DEFAULT_RESOLVED_JOB_PROFILE["desiredLevels"])

    preferred_role_types = _normalize_string_list(
        profile_row.get("preferred_role_types") if profile_row else None
    )

    preferred_workplace_types = _normalize_string_list(
        profile_row.get("preferred_workplace_types") if profile_row else None
    )

    preferred_locations = _normalize_string_list(
        profile_row.get("preferred_locations") if profile_row else None
    )

    skills = _extract_resume_skills(parsed_json)

    return {
        "desiredLevels": desired_levels,
        "preferredRoleTypes": preferred_role_types,
        "preferredWorkplaceTypes": preferred_workplace_types,
        "preferredLocations": preferred_locations,
        "skills": skills,
        "isLgbtFriendlyOnly": bool(
            profile_row.get("is_lgbt_friendly_only") if profile_row else False
        ),
    }


def _fetch_latest_resume_for_user_id(user_id: str) -> dict[str, Any] | None:
    """Fetch the user's most recent resume row, if present."""
    repository = ResumeRepository(client=get_supabase_admin())

    try:
        return repository.get_latest_resume_for_user(user_id)
    except Exception:
        return None


def _extract_resume_skills(parsed_json: Any) -> list[str]:
    """Extract a normalized skill list from flexible parsed resume JSON."""
    if not isinstance(parsed_json, dict):
        return []

    candidates: list[str] = []

    direct_keys = [
        "skills",
        "technical_skills",
        "technologies",
        "tools",
        "keywords",
        "top_skills",
    ]

    for key in direct_keys:
        value = parsed_json.get(key)
        candidates.extend(_coerce_strings(value))

    skills_block = parsed_json.get("skills")
    if isinstance(skills_block, dict):
        candidates.extend(_coerce_strings(skills_block.get("normalized")))
        candidates.extend(_coerce_strings(skills_block.get("raw")))

    summary_block = parsed_json.get("summary")
    if isinstance(summary_block, dict):
        candidates.extend(_coerce_strings(summary_block.get("top_skill_keywords")))

    sections = parsed_json.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_title = str(section.get("title") or "").strip().lower()
            if "skill" not in section_title and "technology" not in section_title:
                continue
            candidates.extend(_coerce_strings(section.get("items")))

    experience = parsed_json.get("experience")
    if isinstance(experience, list):
        for item in experience:
            if not isinstance(item, dict):
                continue
            candidates.extend(_coerce_strings(item.get("technologies")))
            candidates.extend(_coerce_strings(item.get("skills")))
            candidates.extend(_coerce_strings(item.get("normalized_skills")))

    ats_tags = parsed_json.get("ats_tags")
    candidates.extend(_coerce_strings(ats_tags))

    return _dedupe_normalized_strings(candidates)


def _coerce_strings(value: Any) -> list[str]:
    """Coerce flexible values into a list of strings."""
    if value is None:
        return []

    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]

    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    output.append(stripped)
            elif isinstance(item, dict):
                for key in ("name", "label", "value", "skill", "technology"):
                    candidate = item.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        output.append(candidate.strip())
                        break
        return output

    return []


def _normalize_string_list(values: Any) -> list[str]:
    """Normalize a list of string-like values."""
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip().lower()
        if cleaned:
            normalized.append(cleaned)

    return _dedupe_normalized_strings(normalized)


def _dedupe_normalized_strings(values: list[str]) -> list[str]:
    """Dedupe normalized strings while preserving order."""
    seen: set[str] = set()
    output: list[str] = []

    for value in values:
        cleaned = " ".join(str(value).strip().lower().split())
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)

    return output