"""Jobs API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.core.auth_settings import auth_settings
from app.schemas.jobs import JobsResponse
from app.services.auth_cookies import set_auth_cookies
from app.services.auth_service import (
    CurrentSessionContext,
    verify_or_refresh_session,
)
from app.services.jobs.job_ingestion import JobIngestionService
from app.services.jobs.user_profile import (
    DEFAULT_RESOLVED_JOB_PROFILE,
    resolve_job_profile_for_user_id,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


def get_job_ingestion_service() -> JobIngestionService:
    """Provide a configured job ingestion service.

    Provider registration is isolated in the providers package so new sources
    can be added without changing the API route layer.
    """
    from app.services.jobs.providers import get_configured_providers

    return JobIngestionService(providers=get_configured_providers())


def get_optional_session_context(
    access_token: str | None = Cookie(
        default=None,
        alias=auth_settings.access_cookie_name,
    ),
    refresh_token: str | None = Cookie(
        default=None,
        alias=auth_settings.refresh_cookie_name,
    ),
) -> CurrentSessionContext | None:
    """Resolve the current authenticated user from secure cookies when present.

    Anonymous users should still be able to browse jobs, so this helper returns
    None instead of raising when no valid session is available.
    """
    if not access_token and not refresh_token:
        return None

    try:
        return verify_or_refresh_session(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except Exception:
        return None


@router.get("", response_model=JobsResponse)
async def list_jobs(
    job_ingestion_service: JobIngestionService = Depends(get_job_ingestion_service),
) -> JobsResponse:
    """Return normalized jobs for downstream scoring, filtering, and UI display."""
    try:
        jobs = await job_ingestion_service.ingest_jobs()
        return JobsResponse(jobs=jobs, total=len(jobs))
    except Exception as exc:
        logger.exception("Failed to list jobs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load jobs at this time.",
        ) from exc


@router.get("/profile")
def get_jobs_profile(
    response: Response,
    current: CurrentSessionContext | None = Depends(get_optional_session_context),
) -> dict[str, Any]:
    """Return the resolved scoring profile for the current user.

    Logged-out users receive a safe default profile so the jobs page can still
    render entry-level and junior roles.
    """
    try:
        if current is None:
            return dict(DEFAULT_RESOLVED_JOB_PROFILE)

        if current.refreshed and current.session is not None:
            set_auth_cookies(response, current.session)

        user_id = str(getattr(current.user, "id"))
        return resolve_job_profile_for_user_id(user_id=user_id)
    except Exception as exc:
        logger.exception("Failed to resolve jobs profile.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job profile at this time.",
        ) from exc