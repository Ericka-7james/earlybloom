from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.db.database import ResumeRepository, get_user_id_from_bearer_token
from app.schemas.resume import (
    ParseResumeRequest,
    ParseResumeResponse,
    ResumeLogResponse,
    ResumeRecordResponse,
)
from app.services.parser import parse_resume_text
from app.services.resumes.ats_tags import extract_ats_tags

router = APIRouter(prefix="/resume", tags=["resume"])


def get_current_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    """Resolve the authenticated user ID from the bearer token.

    Args:
        authorization: Authorization header value.

    Returns:
        Authenticated user ID.
    """
    return get_user_id_from_bearer_token(authorization)


def get_resume_repository() -> ResumeRepository:
    """Create a resume repository instance.

    Returns:
        Resume repository.
    """
    return ResumeRepository()


@router.get("/{resume_id}", response_model=ResumeRecordResponse)
def get_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeRecordResponse:
    """Fetch a single stored resume for the authenticated user.

    Args:
        resume_id: Resume record ID.
        user_id: Authenticated user ID.
        repository: Resume repository.

    Returns:
        Stored resume record.
    """
    record = repository.get_resume_for_user(resume_id=resume_id, user_id=user_id)
    return ResumeRecordResponse(**record)


@router.get("/{resume_id}/logs", response_model=list[ResumeLogResponse])
def get_resume_logs(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> list[ResumeLogResponse]:
    """Fetch processing logs for a stored resume.

    Args:
        resume_id: Resume record ID.
        user_id: Authenticated user ID.
        repository: Resume repository.

    Returns:
        Resume log entries.
    """
    repository.get_resume_for_user(resume_id=resume_id, user_id=user_id)
    logs = repository.list_resume_logs(resume_id=resume_id, user_id=user_id)
    return [ResumeLogResponse(**log) for log in logs]


@router.post("/{resume_id}/parse", response_model=ParseResumeResponse)
def parse_resume(
    resume_id: str,
    payload: ParseResumeRequest,
    user_id: str = Depends(get_current_user_id),
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ParseResumeResponse:
    """Parse extracted resume text and persist the result.

    Args:
        resume_id: Resume record ID.
        payload: Resume parse request.
        user_id: Authenticated user ID.
        repository: Resume repository.

    Returns:
        Parse response including parsed JSON, warnings, and ATS tags.
    """
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
        latest_error=None,
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