"""Jobs API routes."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Response,
    status,
)

from app.core.auth_settings import auth_settings
from app.db.database import JobCacheRepository, get_user_id_from_bearer_token
from app.schemas.jobs import (
    JobTrackerMutationRequest,
    JobTrackerMutationResponse,
    JobsResponse,
    JobViewerState,
    PublicJob,
)
from app.services.auth_cookies import set_auth_cookies
from app.services.auth_service import (
    CurrentSessionContext,
    verify_or_refresh_session,
)
from app.services.jobs.job_ingestion import (
    JobIngestionService,
    map_normalized_job_to_response,
)
from app.services.jobs.user_profile import (
    DEFAULT_RESOLVED_JOB_PROFILE,
    resolve_job_profile_for_user_id,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


@dataclass
class ViewerContext:
    """Minimal viewer auth context for jobs routes."""

    user_id: str | None = None
    session: Any | None = None
    refreshed: bool = False


def get_job_ingestion_service() -> JobIngestionService:
    """Provide a configured job ingestion service."""
    from app.services.jobs.providers import get_configured_providers

    return JobIngestionService(providers=get_configured_providers())


def get_job_cache_repository() -> JobCacheRepository:
    """Provide a jobs cache repository instance."""
    return JobCacheRepository()


def _resolve_viewer_from_session(
    *,
    access_token: str | None,
    refresh_token: str | None,
) -> CurrentSessionContext | None:
    if not access_token and not refresh_token:
        return None

    try:
        return verify_or_refresh_session(
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except Exception:
        return None


def get_optional_viewer_context(
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(
        default=None,
        alias=auth_settings.access_cookie_name,
    ),
    refresh_token: str | None = Cookie(
        default=None,
        alias=auth_settings.refresh_cookie_name,
    ),
) -> ViewerContext:
    """Resolve the current viewer from secure cookies first, then bearer token.

    Guests should still be able to browse jobs.
    """
    current = _resolve_viewer_from_session(
        access_token=access_token,
        refresh_token=refresh_token,
    )
    if current is not None:
        return ViewerContext(
            user_id=str(getattr(current.user, "id")),
            session=current.session if current.refreshed else None,
            refreshed=bool(current.refreshed),
        )

    if authorization:
        try:
            user_id = get_user_id_from_bearer_token(authorization)
            return ViewerContext(user_id=user_id)
        except HTTPException:
            return ViewerContext()

    return ViewerContext()


def get_required_viewer_context(
    current: ViewerContext = Depends(get_optional_viewer_context),
) -> ViewerContext:
    """Require an authenticated viewer for tracker mutations."""
    if not current.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required for this action.",
        )
    return current


def _set_refreshed_auth_cookies_if_needed(
    response: Response,
    current: ViewerContext,
) -> None:
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)


def _serialize_public_jobs(jobs: list[dict[str, Any]]) -> list[PublicJob]:
    return [PublicJob.model_validate(job) for job in jobs]


def _build_tracker_mutation_response(
    *,
    repository: JobCacheRepository,
    user_id: str,
    public_job_id: str,
) -> JobTrackerMutationResponse:
    viewer_state_payload = repository.apply_viewer_state_to_jobs(
        user_id=user_id,
        jobs=[{"id": public_job_id}],
        exclude_hidden=False,
    )

    if viewer_state_payload:
        viewer_state = viewer_state_payload[0].get("viewer_state") or {}
    else:
        viewer_state = {
            "is_saved": False,
            "is_hidden": False,
            "saved_at": None,
            "hidden_at": None,
        }

    return JobTrackerMutationResponse(
        job_id=public_job_id,
        viewer_state=JobViewerState.model_validate(viewer_state),
    )


def _build_related_jobs_response(
    *,
    response: Response,
    current: ViewerContext,
    repository: JobCacheRepository,
    relation_type: str,
) -> JobsResponse:
    if relation_type == "saved":
      job_rows = repository.list_saved_jobs_for_user(user_id=current.user_id or "")
    elif relation_type == "hidden":
      job_rows = repository.list_hidden_jobs_for_user(user_id=current.user_id or "")
    else:
      raise ValueError(f"Unsupported relation_type={relation_type}")

    public_jobs: list[dict[str, Any]] = []

    for row in job_rows:
        normalized = repository.row_to_normalized_job(row)
        if normalized is None:
            continue
        public_jobs.append(map_normalized_job_to_response(normalized))

    public_jobs = repository.apply_viewer_state_to_jobs(
        user_id=current.user_id or "",
        jobs=public_jobs,
        exclude_hidden=False,
    )

    _set_refreshed_auth_cookies_if_needed(response, current)

    serialized_jobs = _serialize_public_jobs(public_jobs)
    return JobsResponse(jobs=serialized_jobs, total=len(serialized_jobs))


@router.get("", response_model=JobsResponse)
async def list_jobs(
    response: Response,
    current: ViewerContext = Depends(get_optional_viewer_context),
    job_ingestion_service: JobIngestionService = Depends(get_job_ingestion_service),
    repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> JobsResponse:
    """Return normalized jobs for downstream scoring, filtering, and UI display."""
    try:
        jobs = await job_ingestion_service.ingest_jobs()

        if current.user_id:
            jobs = repository.apply_viewer_state_to_jobs(
                user_id=current.user_id,
                jobs=jobs,
                exclude_hidden=True,
            )
            _set_refreshed_auth_cookies_if_needed(response, current)

        serialized_jobs = _serialize_public_jobs(jobs)
        return JobsResponse(jobs=serialized_jobs, total=len(serialized_jobs))
    except Exception as exc:
        logger.exception("Failed to list jobs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load jobs at this time.",
        ) from exc


@router.get("/profile")
def get_jobs_profile(
    response: Response,
    current: ViewerContext = Depends(get_optional_viewer_context),
) -> dict[str, Any]:
    """Return the resolved scoring profile for the current user."""
    try:
        if not current.user_id:
            return dict(DEFAULT_RESOLVED_JOB_PROFILE)

        _set_refreshed_auth_cookies_if_needed(response, current)
        return resolve_job_profile_for_user_id(user_id=current.user_id)
    except Exception as exc:
        logger.exception("Failed to resolve jobs profile.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job profile at this time.",
        ) from exc


@router.post(
    "/saved",
    response_model=JobTrackerMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_job(
    payload: JobTrackerMutationRequest,
    response: Response,
    current: ViewerContext = Depends(get_required_viewer_context),
    repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> JobTrackerMutationResponse:
    """Save a shared cached job for the authenticated user."""
    try:
        repository.save_job_for_user(
            user_id=current.user_id or "",
            public_job_id=payload.job_id,
        )
        _set_refreshed_auth_cookies_if_needed(response, current)

        return _build_tracker_mutation_response(
            repository=repository,
            user_id=current.user_id or "",
            public_job_id=payload.job_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to save job.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save this job right now.",
        ) from exc


@router.delete("/saved/{job_id}", response_model=JobTrackerMutationResponse)
def unsave_job(
    job_id: str,
    response: Response,
    current: ViewerContext = Depends(get_required_viewer_context),
    repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> JobTrackerMutationResponse:
    """Remove a saved-job relationship for the authenticated user."""
    try:
        repository.unsave_job_for_user(
            user_id=current.user_id or "",
            public_job_id=job_id,
        )
        _set_refreshed_auth_cookies_if_needed(response, current)

        return _build_tracker_mutation_response(
            repository=repository,
            user_id=current.user_id or "",
            public_job_id=job_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to unsave job.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to remove this saved job right now.",
        ) from exc


@router.post(
    "/hidden",
    response_model=JobTrackerMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def hide_job(
    payload: JobTrackerMutationRequest,
    response: Response,
    current: ViewerContext = Depends(get_required_viewer_context),
    repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> JobTrackerMutationResponse:
    """Hide a shared cached job for the authenticated user."""
    try:
        repository.hide_job_for_user(
            user_id=current.user_id or "",
            public_job_id=payload.job_id,
        )
        _set_refreshed_auth_cookies_if_needed(response, current)

        return _build_tracker_mutation_response(
            repository=repository,
            user_id=current.user_id or "",
            public_job_id=payload.job_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to hide job.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to hide this job right now.",
        ) from exc


@router.delete("/hidden/{job_id}", response_model=JobTrackerMutationResponse)
def unhide_job(
    job_id: str,
    response: Response,
    current: ViewerContext = Depends(get_required_viewer_context),
    repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> JobTrackerMutationResponse:
    """Remove a hidden-job relationship for the authenticated user."""
    try:
        repository.unhide_job_for_user(
            user_id=current.user_id or "",
            public_job_id=job_id,
        )
        _set_refreshed_auth_cookies_if_needed(response, current)

        return _build_tracker_mutation_response(
            repository=repository,
            user_id=current.user_id or "",
            public_job_id=job_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to unhide job.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to unhide this job right now.",
        ) from exc


@router.get("/saved", response_model=JobsResponse)
def list_saved_jobs(
    response: Response,
    current: ViewerContext = Depends(get_required_viewer_context),
    repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> JobsResponse:
    """List saved jobs for the authenticated user."""
    try:
        return _build_related_jobs_response(
            response=response,
            current=current,
            repository=repository,
            relation_type="saved",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list saved jobs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load saved jobs right now.",
        ) from exc


@router.get("/hidden", response_model=JobsResponse)
def list_hidden_jobs(
    response: Response,
    current: ViewerContext = Depends(get_required_viewer_context),
    repository: JobCacheRepository = Depends(get_job_cache_repository),
) -> JobsResponse:
    """List hidden jobs for the authenticated user."""
    try:
        return _build_related_jobs_response(
            response=response,
            current=current,
            repository=repository,
            relation_type="hidden",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list hidden jobs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load hidden jobs right now.",
        ) from exc