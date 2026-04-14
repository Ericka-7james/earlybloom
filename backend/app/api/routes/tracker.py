"""Tracker API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.db.database import (
    JobCacheRepository,
    ResumeRepository,
    get_supabase_admin,
    get_user_id_from_bearer_token,
)
from app.schemas.tracker import (
    TrackerPreferences,
    TrackerResponse,
    TrackerResumeSummary,
    TrackerStats,
    UpdateTrackerPreferencesRequest,
    UpdateTrackerPreferencesResponse,
)
from app.services.auth_service import fetch_profile_for_user_id
from app.services.jobs.user_profile import DEFAULT_RESOLVED_JOB_PROFILE

router = APIRouter(prefix="/tracker", tags=["tracker"])
logger = logging.getLogger(__name__)


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    """Resolve the authenticated user ID from bearer auth."""
    return get_user_id_from_bearer_token(authorization)


def get_resume_repository() -> ResumeRepository:
    """Create a resume repository instance."""
    return ResumeRepository(client=get_supabase_admin())


def get_job_cache_repository() -> JobCacheRepository:
    """Create a job cache repository instance."""
    return JobCacheRepository()


def _normalize_string_list(value: Any) -> list[str]:
    """Normalize a flexible value into a cleaned lowercase string list."""
    if not isinstance(value, list):
        return []

    output: list[str] = []
    seen: set[str] = set()

    for item in value:
        text = " ".join(str(item or "").strip().lower().split())
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)

    return output


def _build_preferences_from_profile(
    profile_row: dict[str, Any] | None,
) -> TrackerPreferences:
    """Map a profile row into tracker preferences."""
    defaults = DEFAULT_RESOLVED_JOB_PROFILE

    if not profile_row:
        return TrackerPreferences(
            desired_levels=list(defaults["desiredLevels"]),
            preferred_role_types=[],
            preferred_workplace_types=[],
            preferred_locations=[],
            is_lgbt_friendly_only=False,
        )

    desired_levels = _normalize_string_list(profile_row.get("desired_levels"))
    preferred_role_types = _normalize_string_list(
        profile_row.get("preferred_role_types")
    )
    preferred_workplace_types = _normalize_string_list(
        profile_row.get("preferred_workplace_types")
    )
    preferred_locations = _normalize_string_list(
        profile_row.get("preferred_locations")
    )

    return TrackerPreferences(
        desired_levels=desired_levels or list(defaults["desiredLevels"]),
        preferred_role_types=preferred_role_types,
        preferred_workplace_types=preferred_workplace_types,
        preferred_locations=preferred_locations,
        is_lgbt_friendly_only=bool(profile_row.get("is_lgbt_friendly_only")),
    )


def _serialize_resume(record: dict[str, Any] | None) -> TrackerResumeSummary | None:
    """Map a resume row into the tracker resume summary shape."""
    if not record:
        return None

    return TrackerResumeSummary(
        id=record.get("id"),
        original_filename=record.get("original_filename"),
        file_type=record.get("file_type"),
        parse_status=record.get("parse_status"),
        updated_at=record.get("updated_at"),
        ats_tags=record.get("ats_tags") or [],
        parse_warnings=record.get("parse_warnings") or [],
        parsed_json=record.get("parsed_json"),
    )


@router.get("", response_model=TrackerResponse)
def get_tracker(
    user_id: str = Depends(get_current_user_id),
    resume_repository: ResumeRepository = Depends(get_resume_repository),
    job_repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> TrackerResponse:
    """Return combined tracker data for the authenticated user."""
    try:
        profile_row = fetch_profile_for_user_id(user_id)
        latest_resume = resume_repository.get_latest_resume_for_user(user_id)

        saved_jobs = job_repository.list_saved_jobs_for_user(user_id=user_id)
        hidden_jobs = job_repository.list_hidden_jobs_for_user(user_id=user_id)

        return TrackerResponse(
            preferences=_build_preferences_from_profile(profile_row),
            resume=_serialize_resume(latest_resume),
            stats=TrackerStats(
                saved_jobs_count=len(saved_jobs),
                hidden_jobs_count=len(hidden_jobs),
            ),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load tracker.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load tracker right now.",
        ) from exc


@router.patch("/preferences", response_model=UpdateTrackerPreferencesResponse)
def update_tracker_preferences(
    payload: UpdateTrackerPreferencesRequest,
    user_id: str = Depends(get_current_user_id),
) -> UpdateTrackerPreferencesResponse:
    """Persist tracker preferences for the authenticated user."""
    try:
        admin = get_supabase_admin()
        current_profile = fetch_profile_for_user_id(user_id) or {}

        next_preferences = TrackerPreferences(
            desired_levels=(
                payload.desired_levels
                if payload.desired_levels is not None
                else current_profile.get("desired_levels")
                or DEFAULT_RESOLVED_JOB_PROFILE["desiredLevels"]
            ),
            preferred_role_types=(
                payload.preferred_role_types
                if payload.preferred_role_types is not None
                else current_profile.get("preferred_role_types")
                or []
            ),
            preferred_workplace_types=(
                payload.preferred_workplace_types
                if payload.preferred_workplace_types is not None
                else current_profile.get("preferred_workplace_types")
                or []
            ),
            preferred_locations=(
                payload.preferred_locations
                if payload.preferred_locations is not None
                else current_profile.get("preferred_locations")
                or []
            ),
            is_lgbt_friendly_only=(
                payload.is_lgbt_friendly_only
                if payload.is_lgbt_friendly_only is not None
                else bool(current_profile.get("is_lgbt_friendly_only"))
            ),
        )

        upsert_payload = {
            "user_id": user_id,
            "desired_levels": next_preferences.desired_levels,
            "preferred_role_types": next_preferences.preferred_role_types,
            "preferred_workplace_types": next_preferences.preferred_workplace_types,
            "preferred_locations": next_preferences.preferred_locations,
            "is_lgbt_friendly_only": next_preferences.is_lgbt_friendly_only,
        }

        result = (
            admin.table("profiles")
            .upsert(upsert_payload, on_conflict="user_id")
            .execute()
        )

        if getattr(result, "data", None) is None:
            raise RuntimeError("Tracker preferences upsert returned no data.")

        return UpdateTrackerPreferencesResponse(preferences=next_preferences)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update tracker preferences.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save tracker preferences right now.",
        ) from exc