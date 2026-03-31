from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.supabase_clients import (
    get_supabase_public_client,
    get_supabase_service_client,
)
from app.schemas.auth import (
    AuthSessionResponse,
    AuthUserResponse,
    ProfileResponse,
    SignInRequest,
    SignUpRequest,
    UpdateProfileRequest,
)


@dataclass
class CurrentSessionContext:
    """Represents the verified current user session."""

    access_token: str
    refresh_token: str | None
    user: Any
    session: Any | None = None
    refreshed: bool = False


def _http_error(
    status_code: int,
    message: str,
) -> HTTPException:
    """Creates a consistent HTTPException."""
    return HTTPException(status_code=status_code, detail=message)


def _profile_select_columns() -> str:
    """Returns shared profile projection."""
    return (
        "user_id,"
        "email,"
        "display_name,"
        "desired_levels,"
        "is_lgbtq_friendly_only,"
        "created_at,"
        "updated_at"
    )


def _to_optional_iso_string(value: Any) -> str | None:
    """Converts datetimes to ISO strings and leaves strings alone."""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _to_user_response(user: Any) -> AuthUserResponse:
    """Maps a Supabase user object into the API response model."""
    return AuthUserResponse(
        id=str(getattr(user, "id")),
        email=getattr(user, "email", None),
        email_confirmed_at=_to_optional_iso_string(
            getattr(user, "email_confirmed_at", None)
        ),
    )


def _to_profile_response(profile_row: dict[str, Any] | None) -> ProfileResponse | None:
    """Maps a profile row into the API response model."""
    if not profile_row:
        return None

    return ProfileResponse(**profile_row)


def fetch_profile_for_user_id(user_id: str) -> dict[str, Any] | None:
    """Fetches a profile row using trusted server-side access."""
    service_client = get_supabase_service_client()

    result = (
        service_client.table("profiles")
        .select(_profile_select_columns())
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    return result.data


def update_profile_for_user_id(
    user_id: str,
    user_email: str | None,
    payload: UpdateProfileRequest,
) -> dict[str, Any]:
    """Updates profile fields for a single verified user."""
    existing = fetch_profile_for_user_id(user_id) or {
        "user_id": user_id,
        "email": user_email,
        "desired_levels": ["entry-level", "junior"],
        "is_lgbtq_friendly_only": False,
    }

    row = {
        "user_id": user_id,
        "email": existing.get("email") or user_email,
        "display_name": (
            payload.display_name
            if payload.display_name is not None
            else existing.get("display_name")
        ),
        "desired_levels": (
            payload.desired_levels
            if payload.desired_levels is not None
            else existing.get("desired_levels", ["entry-level", "junior"])
        ),
        "is_lgbtq_friendly_only": (
            payload.is_lgbtq_friendly_only
            if payload.is_lgbtq_friendly_only is not None
            else existing.get("is_lgbtq_friendly_only", False)
        ),
    }

    service_client = get_supabase_service_client()

    result = (
        service_client.table("profiles")
        .upsert(row, on_conflict="user_id")
        .execute()
    )

    data = result.data or []
    return data[0] if data else row


def sign_up_user(payload: SignUpRequest) -> tuple[AuthSessionResponse, Any | None]:
    """Signs up a user through Supabase Auth.

    This route does not manually create a profile row. Profile creation should
    be handled by a database trigger on auth.users so we only create app
    profile records after a real auth row exists.
    """
    public_client = get_supabase_public_client()

    try:
        auth_response = public_client.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "display_name": payload.display_name,
                    }
                },
            }
        )
    except Exception as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    user = getattr(auth_response, "user", None)
    session = getattr(auth_response, "session", None)

    if not user or not getattr(user, "id", None):
        raise _http_error(
            status.HTTP_400_BAD_REQUEST,
            "Unable to create the account.",
        )

    response = AuthSessionResponse(
        authenticated=session is not None,
        requires_email_verification=session is None,
        user=_to_user_response(user),
        profile=None,
    )

    return response, session


def sign_in_user(payload: SignInRequest) -> tuple[AuthSessionResponse, Any]:
    """Signs in a user with email and password."""
    public_client = get_supabase_public_client()

    try:
        auth_response = public_client.auth.sign_in_with_password(
            {
                "email": payload.email,
                "password": payload.password,
            }
        )
    except Exception as exc:
        raise _http_error(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password.",
        ) from exc

    user = getattr(auth_response, "user", None)
    session = getattr(auth_response, "session", None)

    if not user or not session:
        raise _http_error(
            status.HTTP_401_UNAUTHORIZED,
            "Unable to establish a session.",
        )

    profile_row = fetch_profile_for_user_id(str(getattr(user, "id")))

    response = AuthSessionResponse(
        authenticated=True,
        requires_email_verification=False,
        user=_to_user_response(user),
        profile=_to_profile_response(profile_row),
    )

    return response, session


def verify_or_refresh_session(
    access_token: str | None,
    refresh_token: str | None,
) -> CurrentSessionContext:
    """Verifies the current session, refreshing it if needed."""
    public_client = get_supabase_public_client()

    if access_token:
        try:
            user_response = public_client.auth.get_user(access_token)
            user = getattr(user_response, "user", None)
            if user:
                return CurrentSessionContext(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user=user,
                    session=None,
                    refreshed=False,
                )
        except Exception:
            pass

    if not refresh_token:
        raise _http_error(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")

    try:
        refreshed = public_client.auth.refresh_session(refresh_token)
    except Exception as exc:
        raise _http_error(
            status.HTTP_401_UNAUTHORIZED,
            "Your session has expired. Please sign in again.",
        ) from exc

    session = getattr(refreshed, "session", None)
    user = getattr(refreshed, "user", None)

    if not session:
        session = refreshed

    if not user:
        try:
            user_response = public_client.auth.get_user(getattr(session, "access_token"))
            user = getattr(user_response, "user", None)
        except Exception as exc:
            raise _http_error(
                status.HTTP_401_UNAUTHORIZED,
                "Unable to refresh the session.",
            ) from exc

    if not user:
        raise _http_error(
            status.HTTP_401_UNAUTHORIZED,
            "Unable to refresh the session.",
        )

    return CurrentSessionContext(
        access_token=getattr(session, "access_token"),
        refresh_token=getattr(session, "refresh_token", refresh_token),
        user=user,
        session=session,
        refreshed=True,
    )


def sign_out_session(access_token: str | None, refresh_token: str | None) -> None:
    """Signs out the current session in Supabase when possible."""
    if not access_token or not refresh_token:
        return

    public_client = get_supabase_public_client()

    try:
        public_client.auth.set_session(access_token, refresh_token)
        public_client.auth.sign_out()
    except Exception:
        return