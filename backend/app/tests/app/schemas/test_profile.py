from __future__ import annotations

from app.schemas.profile import ProfileSummary, _normalize_string_list


def test_normalize_string_list_returns_empty_list_for_none():
    assert _normalize_string_list(None) == []


def test_normalize_string_list_wraps_scalar_and_normalizes():
    assert _normalize_string_list("  Software Engineer  ") == ["software engineer"]


def test_normalize_string_list_dedupes_and_removes_blank_values():
    result = _normalize_string_list(
        [" Remote ", "remote", "", None, "Hybrid", " hybrid "]
    )

    assert result == ["remote", "hybrid"]


def test_normalize_string_list_preserves_first_seen_order():
    result = _normalize_string_list(
        ["Data", "backend", "data", "frontend", "Backend", "ml"]
    )

    assert result == ["data", "backend", "frontend", "ml"]


def test_profile_summary_uses_defaults():
    profile = ProfileSummary()

    assert profile.display_name is None
    assert profile.career_interests == []
    assert profile.desired_levels == ["entry-level", "junior"]
    assert profile.preferred_role_types == []
    assert profile.preferred_workplace_types == []
    assert profile.preferred_locations == []
    assert profile.is_lgbt_friendly_only is False


def test_profile_summary_normalizes_all_list_fields():
    profile = ProfileSummary(
        display_name="E",
        career_interests=[" Software Engineering ", "software engineering", "Data"],
        desired_levels=[" Junior ", "Entry-Level", "junior"],
        preferred_role_types=["Backend", " backend ", "Frontend"],
        preferred_workplace_types=[" Remote ", "Hybrid", "remote"],
        preferred_locations=[" Atlanta, GA ", "atlanta, ga", "New York, NY"],
        is_lgbt_friendly_only=True,
    )

    assert profile.display_name == "E"
    assert profile.career_interests == ["software engineering", "data"]
    assert profile.desired_levels == ["junior", "entry-level"]
    assert profile.preferred_role_types == ["backend", "frontend"]
    assert profile.preferred_workplace_types == ["remote", "hybrid"]
    assert profile.preferred_locations == ["atlanta, ga", "new york, ny"]
    assert profile.is_lgbt_friendly_only is True


def test_profile_summary_accepts_scalar_values_for_list_fields():
    profile = ProfileSummary(
        career_interests="Product",
        desired_levels="Junior",
        preferred_role_types="Backend",
        preferred_workplace_types="Remote",
        preferred_locations="Atlanta, GA",
    )

    assert profile.career_interests == ["product"]
    assert profile.desired_levels == ["junior"]
    assert profile.preferred_role_types == ["backend"]
    assert profile.preferred_workplace_types == ["remote"]
    assert profile.preferred_locations == ["atlanta, ga"]


def test_profile_summary_converts_non_string_values_in_lists():
    profile = ProfileSummary(
        career_interests=["AI", 123, True],
        preferred_locations=["Atlanta", 404, False],
    )

    assert profile.career_interests == ["ai", "123", "true"]
    assert profile.preferred_locations == ["atlanta", "404"]


def test_profile_summary_drops_empty_values_after_normalization():
    profile = ProfileSummary(
        career_interests=["", "   ", None],
        preferred_role_types=["", "  ", None],
        preferred_workplace_types=["Remote", "", "   ", None],
    )

    assert profile.career_interests == []
    assert profile.preferred_role_types == []
    assert profile.preferred_workplace_types == ["remote"]