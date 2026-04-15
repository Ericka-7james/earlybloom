from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response

from app.core.auth_settings import auth_settings
from app.db.database import ResumeRepository
from app.schemas.resume import (
    ParseResumeRequest,
    ParseResumeResponse,
    ResumeLogResponse,
    ResumeRecordResponse,
    UpsertResumeRecordRequest,
)
from app.services.auth_cookies import set_auth_cookies
from app.services.auth_service import CurrentSessionContext, verify_or_refresh_session
from app.services.parser import parse_resume_text
from app.services.resumes.ats_tags import extract_ats_tags

router = APIRouter(prefix="/resume", tags=["resume"])


def get_current_session_context(
    access_token: str | None = Cookie(
        default=None,
        alias=auth_settings.access_cookie_name,
    ),
    refresh_token: str | None = Cookie(
        default=None,
        alias=auth_settings.refresh_cookie_name,
    ),
) -> CurrentSessionContext:
    """Resolve the authenticated user from secure auth cookies."""
    return verify_or_refresh_session(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def get_resume_repository() -> ResumeRepository:
    """Create a resume repository instance."""
    return ResumeRepository()


@router.get("/current", response_model=ResumeRecordResponse)
def get_current_resume(
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeRecordResponse:
    """Fetch the latest resume for the authenticated user."""
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)

    user_id = str(getattr(current.user, "id"))
    record = repository.get_latest_resume_for_user(user_id=user_id)
    return ResumeRecordResponse(**record)


@router.post("/current", response_model=ResumeRecordResponse)
def create_or_update_current_resume(
    payload: UpsertResumeRecordRequest,
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeRecordResponse:
    """Create or update the authenticated user's active resume record."""
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)

    user_id = str(getattr(current.user, "id"))

    row = {
        "user_id": user_id,
        "original_filename": payload.original_filename,
        "file_size_bytes": payload.file_size_bytes,
        "file_type": payload.file_type or "application/pdf",
        "upload_source": payload.upload_source or "web",
        "storage_path": payload.storage_path,
        "parse_status": payload.parse_status or "pending",
        "raw_text": payload.raw_text,
        "parsed_json": payload.parsed_json,
        "ats_tags": payload.ats_tags or [],
        "parse_warnings": payload.parse_warnings or [],
    }

    result = (
        repository.client.table("resumes")
        .upsert(row, on_conflict="user_id")
        .execute()
    )

    data = result.data or []
    if not data:
        record = repository.get_latest_resume_for_user(user_id=user_id)
        return ResumeRecordResponse(**record)

    return ResumeRecordResponse(**data[0])


@router.get("/{resume_id}", response_model=ResumeRecordResponse)
def get_resume(
    resume_id: str,
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeRecordResponse:
    """Fetch a single stored resume for the authenticated user."""
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)

    user_id = str(getattr(current.user, "id"))
    record = repository.get_resume_for_user(resume_id=resume_id, user_id=user_id)
    return ResumeRecordResponse(**record)


@router.get("/{resume_id}/logs", response_model=list[ResumeLogResponse])
def get_resume_logs(
    resume_id: str,
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> list[ResumeLogResponse]:
    """Fetch processing logs for a stored resume."""
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)

    user_id = str(getattr(current.user, "id"))
    repository.get_resume_for_user(resume_id=resume_id, user_id=user_id)
    logs = repository.list_resume_logs(resume_id=resume_id, user_id=user_id)
    return [ResumeLogResponse(**log) for log in logs]


@router.post("/{resume_id}/parse", response_model=ParseResumeResponse)
def parse_resume(
    resume_id: str,
    payload: ParseResumeRequest,
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ParseResumeResponse:
    """Parse extracted resume text and persist the result."""
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)

    user_id = str(getattr(current.user, "id"))
    repository.get_resume_for_user(resume_id=resume_id, user_id=user_id)

    repository.create_resume_log(
        resume_id=resume_id,
        user_id=user_id,
        event_type="parse_started",
        event_status="info",
        message="Resume parse started.",
        metadata={
            "file_type": payload.file_type,
            "extraction_method": payload.extraction_method,
        },
    )

    parsed_json, warnings = parse_resume_text(
        payload.raw_text,
        file_type=payload.file_type,
        extraction_method=payload.extraction_method,
    )

    ats_tags = extract_ats_tags(parsed_json)

    updated_record = repository.update_resume_parse_result(
        resume_id=resume_id,
        user_id=user_id,
        parse_status="parsed",
        raw_text=payload.raw_text,
        parsed_json=parsed_json,
        parse_warnings=warnings,
        ats_tags=ats_tags,
    )

    repository.create_resume_log(
        resume_id=resume_id,
        user_id=user_id,
        event_type="parse_completed",
        event_status="success",
        message="Resume parsed successfully.",
        metadata={
            "warning_count": len(warnings),
            "confidence": parsed_json.get("meta", {}).get("confidence"),
            "ats_tag_count": len(ats_tags),
        },
    )

    return ParseResumeResponse(
        resume_id=resume_id,
        parse_status=updated_record["parse_status"],
        warnings=warnings,
        parsed_json=parsed_json,
        raw_text_preview=payload.raw_text[:280],
        ats_tags=ats_tags,
    )