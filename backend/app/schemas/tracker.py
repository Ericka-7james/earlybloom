"""Schemas for tracker API responses and mutations.

This module defines the canonical tracker payload returned to the frontend.
The tracker response intentionally separates four concerns:

1. profile
   Durable user-facing account and search identity settings.

2. preferences
   Persistent tracker and jobs defaults used to initialize search behavior.

3. resume
   Latest uploaded resume summary and parser output snapshot.

4. stats
   Computed saved and hidden job counts shown in tracker surfaces.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.profile import ProfileSummary


def _normalize_string_list(value: object) -> list[str]:
    """Normalize a flexible input into a deduplicated lowercase string list.

    Args:
        value: Incoming raw value. This may be None, a scalar, or a list.

    Returns:
        A cleaned list of lowercase strings with duplicates and empty values
        removed while preserving first-seen order.
    """
    if value is None:
        return []

    if not isinstance(value, list):
        value = [value]

    normalized: list[str] = []
    seen: set[str] = set()

    for item in value:
        text = " ".join(str(item or "").strip().lower().split())
        if not text or text in seen:
            continue

        seen.add(text)
        normalized.append(text)

    return normalized


class TrackerPreferences(BaseModel):
    """Represents persistent tracker search defaults for a user.

    These preferences are used to seed jobs and tracker experiences with
    durable defaults. They are narrower in purpose than the full profile
    model, even though some fields overlap.

    Attributes:
        desired_levels: Preferred experience levels for role discovery.
        preferred_role_types: Preferred job families or role categories.
        preferred_workplace_types: Preferred workplace modes such as remote,
            hybrid, or onsite.
        preferred_locations: Preferred locations for job discovery.
        is_lgbt_friendly_only: Whether LGBTQ-friendly roles should be used as
            a persistent filter default.
    """

    desired_levels: list[str] = Field(
        default_factory=lambda: ["entry-level", "junior"]
    )
    preferred_role_types: list[str] = Field(default_factory=list)
    preferred_workplace_types: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    is_lgbt_friendly_only: bool = False

    @field_validator(
        "desired_levels",
        "preferred_role_types",
        "preferred_workplace_types",
        "preferred_locations",
        mode="before",
    )
    @classmethod
    def normalize_string_lists(cls, value: object) -> list[str]:
        """Normalize string-list fields into a stable frontend-friendly shape.

        Args:
            value: Raw incoming value from the database or request payload.

        Returns:
            A normalized list of lowercase strings.
        """
        return _normalize_string_list(value)


class TrackerResumeSummary(BaseModel):
    """Represents the latest frontend-facing resume summary.

    This shape is intentionally lightweight enough for tracker and profile
    surfaces while still exposing the latest parser snapshot.

    Attributes:
        id: Resume record ID.
        original_filename: Original uploaded file name.
        file_type: Resume MIME type.
        parse_status: Current parse state.
        updated_at: ISO timestamp of the most recent update.
        ats_tags: Extracted ATS-oriented tags derived from parsing.
        parse_warnings: Parser warnings or non-fatal extraction notes.
        parsed_json: Structured parsed resume payload when available.
    """

    id: str | None = None
    original_filename: str | None = None
    file_type: str | None = None
    parse_status: str | None = None
    updated_at: str | None = None
    ats_tags: list[str] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)
    parsed_json: dict[str, Any] | None = None


class TrackerStats(BaseModel):
    """Represents computed tracker counts shown in account surfaces.

    Attributes:
        saved_jobs_count: Number of jobs currently saved by the user.
        hidden_jobs_count: Number of jobs currently hidden by the user.
    """

    saved_jobs_count: int = 0
    hidden_jobs_count: int = 0


class TrackerResponse(BaseModel):
    """Represents the full tracker payload returned to the frontend.

    Attributes:
        profile: Durable account-facing profile summary.
        preferences: Persistent tracker search defaults.
        resume: Latest resume summary, if one exists.
        stats: Computed tracker counts.
    """

    profile: ProfileSummary
    preferences: TrackerPreferences
    resume: TrackerResumeSummary | None = None
    stats: TrackerStats


class UpdateTrackerPreferencesRequest(BaseModel):
    """Represents a partial update payload for tracker preferences.

    Any field omitted from the request should preserve its current stored value.

    Attributes:
        desired_levels: Updated preferred experience levels.
        preferred_role_types: Updated preferred role categories.
        preferred_workplace_types: Updated preferred workplace modes.
        preferred_locations: Updated preferred job locations.
        is_lgbt_friendly_only: Updated LGBTQ-friendly-only default flag.
    """

    desired_levels: list[str] | None = None
    preferred_role_types: list[str] | None = None
    preferred_workplace_types: list[str] | None = None
    preferred_locations: list[str] | None = None
    is_lgbt_friendly_only: bool | None = None

    @field_validator(
        "desired_levels",
        "preferred_role_types",
        "preferred_workplace_types",
        "preferred_locations",
        mode="before",
    )
    @classmethod
    def normalize_optional_string_lists(cls, value: object) -> list[str] | None:
        """Normalize optional string-list fields while preserving omission.

        Args:
            value: Raw incoming field value.

        Returns:
            None when the field is omitted, otherwise a normalized list of
            lowercase strings.
        """
        if value is None:
            return None

        return _normalize_string_list(value)


class UpdateTrackerPreferencesResponse(BaseModel):
    """Represents the response returned after updating tracker preferences.

    Attributes:
        preferences: Persisted tracker preferences after the update.
    """

    preferences: TrackerPreferences