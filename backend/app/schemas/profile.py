"""Schemas for profile data returned by account-facing endpoints.

This module defines the durable profile shape for EarlyBloom users.
Profile data represents longer-lived account and search identity settings,
rather than temporary page-only filter state.

The profile model is intentionally close to tracker preferences so the
frontend can render a consistent account snapshot while still preserving
a semantic distinction between:

1. Account/profile data
2. Search default preferences
3. Resume-derived signals
4. Page-local filter overrides
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


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


class ProfileSummary(BaseModel):
    """Represents durable user profile and search identity settings.

    This model is intended to describe the user's longer-lived account-facing
    preferences. These values may be shown on the Profile page and may also
    help initialize default tracker or jobs behavior.

    Attributes:
        display_name: User-facing display name for account surfaces.
        career_interests: Broad role or career themes the user wants to pursue.
        desired_levels: Preferred seniority levels such as entry-level or junior.
        preferred_role_types: Preferred role categories or job families.
        preferred_workplace_types: Preferred workplace modes such as remote or hybrid.
        preferred_locations: Preferred geographic locations for roles.
        is_lgbt_friendly_only: Whether LGBTQ-friendly roles should be prioritized
            as a durable account preference.
    """

    display_name: str | None = None
    career_interests: list[str] = Field(default_factory=list)
    desired_levels: list[str] = Field(
        default_factory=lambda: ["entry-level", "junior"]
    )
    preferred_role_types: list[str] = Field(default_factory=list)
    preferred_workplace_types: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    is_lgbt_friendly_only: bool = False

    @field_validator(
        "career_interests",
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