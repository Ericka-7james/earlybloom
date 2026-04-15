"""Tracker API routes for EarlyBloom.

These routes provide:
- combined tracker data for the authenticated user
- tracker preference updates
- stable defaults when profile or resume data is missing

The tracker is an authenticated surface and always requires a verified session.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.routes.auth import get_current_session_context
from app.db.database import (
    JobCacheRepository,
    ResumeRepository,
    get_supabase_admin,
)
from app.schemas.profile import ProfileSummary
from app.schemas.tracker import (
    TrackerPreferences,
    TrackerResponse,
    TrackerResumeSummary,
    TrackerStats,
    UpdateTrackerPreferencesRequest,
    UpdateTrackerPreferencesResponse,
)
from app.services.auth_cookies import set_auth_cookies
from app.services.auth_service import (
    CurrentSessionContext,
    fetch_profile_for_user_id,
)
from app.services.jobs.user_profile import DEFAULT_RESOLVED_JOB_PROFILE

router = APIRouter(prefix="/tracker", tags=["tracker"])
logger = logging.getLogger(__name__)


def get_resume_repository() -> ResumeRepository:
    """Returns a resume repository instance.

    Returns:
        ResumeRepository: Repository for resume data access.
    """
    return ResumeRepository(client=get_supabase_admin())


def get_job_cache_repository() -> JobCacheRepository:
    """Returns a job-cache repository instance.

    Returns:
        JobCacheRepository: Repository for saved and hidden job access.
    """
    return JobCacheRepository()


def _normalize_string_list(value: Any) -> list[str]:
    """Normalizes a flexible value into a cleaned lowercase string list.

    Args:
        value: Raw list-like field.

    Returns:
        list[str]: Deduplicated normalized string list.
    """
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
    """Builds tracker preferences from a stored profile row.

    Args:
        profile_row: Stored profile row, if available.

    Returns:
        TrackerPreferences: Tracker preferences with stable defaults.
    """
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
        is_lgbt_friendly_only=bool(
            profile_row.get("is_lgbt_friendly_only")
            or profile_row.get("is_lgbtq_friendly_only")
        ),
    )


def _build_profile_summary(
    *,
    user_id: str,
    user_email: str | None,
    profile_row: dict[str, Any] | None,
) -> ProfileSummary:
    """Builds the tracker profile summary.

    Args:
        user_id: Authenticated user ID.
        user_email: Authenticated user email.
        profile_row: Stored profile row, if available.

    Returns:
        ProfileSummary: Profile summary with safe defaults.
    """
    if profile_row:
        return ProfileSummary(**profile_row)

    return ProfileSummary(
        user_id=user_id,
        email=user_email,
        display_name=None,
        desired_levels=list(DEFAULT_RESOLVED_JOB_PROFILE["desiredLevels"]),
        is_lgbtq_friendly_only=False,
        created_at=None,
        updated_at=None,
    )


def _serialize_resume(record: dict[str, Any] | None) -> TrackerResumeSummary | None:
    """Maps a resume row into the tracker resume summary shape.

    Args:
        record: Resume database row, if available.

    Returns:
        TrackerResumeSummary | None: Serialized tracker resume summary.
    """
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
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
    resume_repository: ResumeRepository = Depends(get_resume_repository),
    job_repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> TrackerResponse:
    """Returns combined tracker data for the authenticated user.

    Args:
        response: Outgoing response object.
        current: Verified current session context.
        resume_repository: Resume repository.
        job_repository: Job cache repository.

    Raises:
        HTTPException: If tracker data cannot be loaded.

    Returns:
        TrackerResponse: Combined tracker response payload.
    """
    try:
        if current.refreshed and current.session is not None:
            set_auth_cookies(response, current.session)

        user_id = str(getattr(current.user, "id"))
        user_email = getattr(current.user, "email", None)

        profile_row = fetch_profile_for_user_id(user_id)

        try:
            latest_resume = resume_repository.get_latest_resume_for_user(user_id)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                latest_resume = None
            else:
                raise

        saved_jobs = job_repository.list_saved_jobs_for_user(user_id=user_id)
        hidden_jobs = job_repository.list_hidden_jobs_for_user(user_id=user_id)

        return TrackerResponse(
            profile=_build_profile_summary(
                user_id=user_id,
                user_email=user_email,
                profile_row=profile_row,
            ),
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
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
) -> UpdateTrackerPreferencesResponse:
    """Persists tracker preferences for the authenticated user.

    Args:
        payload: Tracker preference update payload.
        response: Outgoing response object.
        current: Verified current session context.

    Raises:
        HTTPException: If preferences cannot be saved.

    Returns:
        UpdateTrackerPreferencesResponse: Updated preferences payload.
    """
    try:
        if current.refreshed and current.session is not None:
            set_auth_cookies(response, current.session)

        user_id = str(getattr(current.user, "id"))
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
                else bool(
                    current_profile.get("is_lgbt_friendly_only")
                    or current_profile.get("is_lgbtq_friendly_only")
                )
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