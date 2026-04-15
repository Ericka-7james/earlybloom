from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Response

from app.core.auth_settings import auth_settings


def _cookie_domain() -> str | None:
    """Return the configured cookie domain, or None when unset."""
    domain = auth_settings.auth_cookie_domain.strip()
    return domain or None


def set_auth_cookies(response: Response, session: Any) -> None:
    """Set access and refresh token cookies from a Supabase session object."""
    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)
    expires_in = int(getattr(session, "expires_in", 3600) or 3600)

    access_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    refresh_expires = datetime.now(timezone.utc) + timedelta(
        seconds=auth_settings.refresh_cookie_max_age_seconds
    )

    if access_token:
        response.set_cookie(
            key=auth_settings.access_cookie_name,
            value=access_token,
            httponly=True,
            secure=auth_settings.auth_cookie_secure,
            samesite=auth_settings.auth_cookie_samesite,
            max_age=expires_in,
            expires=access_expires,
            domain=_cookie_domain(),
            path="/",
        )

    if refresh_token:
        response.set_cookie(
            key=auth_settings.refresh_cookie_name,
            value=refresh_token,
            httponly=True,
            secure=auth_settings.auth_cookie_secure,
            samesite=auth_settings.auth_cookie_samesite,
            max_age=auth_settings.refresh_cookie_max_age_seconds,
            expires=refresh_expires,
            domain=_cookie_domain(),
            path="/",
        )


def clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies from the browser."""
    response.delete_cookie(
        key=auth_settings.access_cookie_name,
        domain=_cookie_domain(),
        path="/",
    )
    response.delete_cookie(
        key=auth_settings.refresh_cookie_name,
        domain=_cookie_domain(),
        path="/",
    )