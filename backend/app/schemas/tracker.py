"""Schemas for tracker API responses and mutations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class TrackerPreferences(BaseModel):
    """Persistent user tracker preferences."""

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


class TrackerResumeSummary(BaseModel):
    """Frontend-friendly latest resume summary."""

    id: str | None = None
    original_filename: str | None = None
    file_type: str | None = None
    parse_status: str | None = None
    updated_at: str | None = None
    ats_tags: list[str] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)
    parsed_json: dict[str, Any] | None = None


class TrackerStats(BaseModel):
    """Counts shown on the tracker page."""

    saved_jobs_count: int = 0
    hidden_jobs_count: int = 0


class TrackerResponse(BaseModel):
    """Combined tracker payload."""

    preferences: TrackerPreferences
    resume: TrackerResumeSummary | None = None
    stats: TrackerStats


class UpdateTrackerPreferencesRequest(BaseModel):
    """Payload for updating tracker preferences."""

    desired_levels: list[str] | None = None
    preferred_role_types: list[str] | None = None
    preferred_workplace_types: list[str] | None = None
    preferred_locations: list[str] | None = None
    is_lgbt_friendly_only: bool | None = None


class UpdateTrackerPreferencesResponse(BaseModel):
    """Response after updating tracker preferences."""

    preferences: TrackerPreferences