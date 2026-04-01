from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from supabase import Client, create_client

from app.core.config import get_settings

settings = get_settings()
SUPABASE_URL = (settings.SUPABASE_URL or "").strip()
SUPABASE_SECRET_KEY = (settings.SUPABASE_SECRET_KEY or "").strip()

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_SECRET_KEY for backend database access."
    )

_supabase_admin: Client | None = None


def get_supabase_admin() -> Client:
    """Return a cached Supabase admin client.

    Returns:
        Cached Supabase admin client.
    """
    global _supabase_admin

    if _supabase_admin is None:
      _supabase_admin = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

    return _supabase_admin


def get_user_id_from_bearer_token(authorization_header: Optional[str]) -> str:
    """Resolve the authenticated Supabase user ID from a bearer token.

    Args:
        authorization_header: Raw Authorization header value.

    Returns:
        Authenticated Supabase user ID.

    Raises:
        HTTPException: If the token is missing, malformed, or invalid.
    """
    if not authorization_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    prefix = "Bearer "
    if not authorization_header.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format.",
        )

    access_token = authorization_header[len(prefix):].strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    supabase = get_supabase_admin()

    try:
        response = supabase.auth.get_user(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Supabase access token.",
        ) from exc

    user = getattr(response, "user", None)
    user_id = getattr(user, "id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase user could not be resolved from token.",
        )

    return str(user_id)


class ResumeRepository:
    """Repository for resume records and resume processing logs."""

    def __init__(self, client: Client | None = None) -> None:
        """Initialize the repository.

        Args:
            client: Optional Supabase client override.
        """
        self.client = client or get_supabase_admin()

    def get_resume_for_user(self, resume_id: str, user_id: str) -> Dict[str, Any]:
        """Fetch a specific resume belonging to a user.

        Args:
            resume_id: Resume record ID.
            user_id: Authenticated user ID.

        Returns:
            Resume record.

        Raises:
            HTTPException: If the resume does not exist for the user.
        """
        result = (
            self.client.table("resumes")
            .select("*")
            .eq("id", resume_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found.",
            )

        return data[0]

    def get_latest_resume_for_user(self, user_id: str) -> Dict[str, Any]:
        """Fetch the user's most recently updated resume.

        With the single-active-resume model, this is typically the user's only
        resume record, but ordering by updated time keeps the method safe and
        future-friendly.

        Args:
            user_id: Authenticated user ID.

        Returns:
            Most recently updated resume record.

        Raises:
            HTTPException: If the user has no stored resume.
        """
        result = (
            self.client.table("resumes")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found.",
            )

        return data[0]

    def update_resume_parse_result(
        self,
        *,
        resume_id: str,
        user_id: str,
        parse_status: str,
        raw_text: Optional[str] = None,
        parsed_json: Optional[Dict[str, Any]] = None,
        parse_warnings: Optional[list[str]] = None,
        latest_error: Optional[str] = None,
        ats_tags: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Update stored parse results for a resume.

        Args:
            resume_id: Resume record ID.
            user_id: Authenticated user ID.
            parse_status: Current parse state.
            raw_text: Extracted raw resume text.
            parsed_json: Structured parsed resume JSON.
            parse_warnings: Parse warnings generated by the parser.
            latest_error: Most recent parse error if any.
            ats_tags: Lightweight ATS-style tags derived from parsed JSON.

        Returns:
            Updated resume record.

        Raises:
            HTTPException: If the resume cannot be updated.
        """
        update_payload: Dict[str, Any] = {
            "parse_status": parse_status,
            "parse_warnings": parse_warnings or [],
            "latest_error": latest_error,
        }

        if raw_text is not None:
            update_payload["raw_text"] = raw_text

        if parsed_json is not None:
            update_payload["parsed_json"] = parsed_json

        if ats_tags is not None:
            update_payload["ats_tags"] = ats_tags

        result = (
            self.client.table("resumes")
            .update(update_payload)
            .eq("id", resume_id)
            .eq("user_id", user_id)
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or update failed.",
            )

        return data[0]

    def create_resume_log(
        self,
        *,
        resume_id: str,
        user_id: str,
        event_type: str,
        event_status: str = "info",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a resume processing log entry.

        Args:
            resume_id: Resume record ID.
            user_id: Authenticated user ID.
            event_type: Event type label.
            event_status: Event status label.
            message: Human-readable log message.
            metadata: Optional structured metadata.

        Returns:
            Created log record.

        Raises:
            HTTPException: If log creation fails.
        """
        result = (
            self.client.table("resume_logs")
            .insert(
                {
                    "resume_id": resume_id,
                    "user_id": user_id,
                    "event_type": event_type,
                    "event_status": event_status,
                    "message": message,
                    "metadata": metadata or {},
                }
            )
            .execute()
        )

        data = result.data or []
        if not data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create resume log.",
            )

        return data[0]

    def list_resume_logs(self, *, resume_id: str, user_id: str) -> list[Dict[str, Any]]:
        """List resume processing logs for a user's resume.

        Args:
            resume_id: Resume record ID.
            user_id: Authenticated user ID.

        Returns:
            Resume log records ordered from newest to oldest.
        """
        result = (
            self.client.table("resume_logs")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []