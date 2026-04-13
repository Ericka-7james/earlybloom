from __future__ import annotations

import os
from dataclasses import dataclass


_ALLOWED_SAMESITE_VALUES = {"lax", "strict", "none"}


@dataclass(frozen=True)
class AuthSettings:
    """Auth-specific settings for EarlyBloom backend."""

    supabase_url: str = os.getenv("SUPABASE_URL", "").strip()
    supabase_publishable_key: str = os.getenv(
        "SUPABASE_PUBLISHABLE_KEY", ""
    ).strip()
    supabase_secret_key: str = os.getenv("SUPABASE_SECRET_KEY", "").strip()

    frontend_origin: str = os.getenv(
        "EARLYBLOOM_FRONTEND_ORIGIN",
        "http://localhost:5173",
    ).strip()

    access_cookie_name: str = os.getenv(
        "AUTH_ACCESS_COOKIE_NAME",
        "earlybloom_access_token",
    ).strip()
    refresh_cookie_name: str = os.getenv(
        "AUTH_REFRESH_COOKIE_NAME",
        "earlybloom_refresh_token",
    ).strip()

    cookie_domain: str = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()
    cookie_samesite: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    cookie_secure: bool = (
        os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() == "true"
    )

    refresh_cookie_max_age_seconds: int = int(
        os.getenv("AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS", "2592000").strip()
    )

    def validate(self) -> None:
        """Validates required settings at startup."""
        missing = []

        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_publishable_key:
            missing.append("SUPABASE_PUBLISHABLE_KEY")
        if not self.supabase_secret_key:
            missing.append("SUPABASE_SECRET_KEY")

        if missing:
            raise RuntimeError(
                "Missing required auth environment variables: "
                + ", ".join(missing)
            )

        if self.cookie_samesite not in _ALLOWED_SAMESITE_VALUES:
            raise RuntimeError(
                "AUTH_COOKIE_SAMESITE must be one of: lax, strict, none."
            )

        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise RuntimeError(
                "AUTH_COOKIE_SECURE must be true when AUTH_COOKIE_SAMESITE is 'none'."
            )

        if self.refresh_cookie_max_age_seconds <= 0:
            raise RuntimeError(
                "AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS must be a positive integer."
            )

    @property
    def cookie_domain_or_none(self) -> str | None:
        """Returns the cookie domain or None when unset."""
        return self.cookie_domain or None


auth_settings = AuthSettings()