from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthSettings:
    """Auth-specific settings for EarlyBloom backend."""

    supabase_url: str = os.getenv("SUPABASE_URL", "").strip()
    supabase_publishable_key: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
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


auth_settings = AuthSettings()