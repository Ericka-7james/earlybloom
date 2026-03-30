from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from supabase import Client, create_client


def _read_setting(name: str) -> str | None:
    try:
        from app.core.config import settings  # type: ignore

        value = getattr(settings, name, None)
        if value:
            return value
    except Exception:
        pass

    return os.getenv(name)


SUPABASE_URL = _read_setting("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = _read_setting("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY for backend database access."
    )

_supabase_admin: Client | None = None


def get_supabase_admin() -> Client:
    global _supabase_admin

    if _supabase_admin is None:
        _supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    return _supabase_admin


def get_user_id_from_bearer_token(authorization_header: Optional[str]) -> str:
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
    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_admin()

    def get_resume_for_user(self, resume_id: str, user_id: str) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
        update_payload: Dict[str, Any] = {
            "parse_status": parse_status,
            "parse_warnings": parse_warnings or [],
            "latest_error": latest_error,
        }

        if raw_text is not None:
            update_payload["raw_text"] = raw_text

        if parsed_json is not None:
            update_payload["parsed_json"] = parsed_json

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
        result = (
            self.client.table("resume_logs")
            .select("*")
            .eq("resume_id", resume_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []