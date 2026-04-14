from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


class AuthSettings:
    def __init__(self) -> None:
        self.frontend_origin = os.getenv(
            "EARLYBLOOM_FRONTEND_ORIGIN",
            "http://localhost:5173",
        ).strip()
        self.cors_origins = os.getenv("CORS_ORIGINS", "").strip()

        self.supabase_url = os.getenv("SUPABASE_URL", "").strip()
        self.supabase_publishable_key = os.getenv(
            "SUPABASE_PUBLISHABLE_KEY", ""
        ).strip()
        self.supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY", "").strip()

        self.jwt_secret = os.getenv("JWT_SECRET", "").strip()
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
        self.access_token_expire_minutes = _get_int(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        )

        self.access_cookie_name = os.getenv(
            "AUTH_COOKIE_ACCESS_NAME",
            "eb_access_token",
        ).strip()
        self.refresh_cookie_name = os.getenv(
            "AUTH_COOKIE_REFRESH_NAME",
            "eb_refresh_token",
        ).strip()

        self.access_cookie_max_age_seconds = _get_int(
            "AUTH_COOKIE_ACCESS_MAX_AGE_SECONDS",
            60 * 60,
        )
        self.refresh_cookie_max_age_seconds = _get_int(
            "AUTH_COOKIE_REFRESH_MAX_AGE_SECONDS",
            60 * 60 * 24 * 30,
        )

        self.auth_cookie_samesite = os.getenv(
            "AUTH_COOKIE_SAMESITE",
            "lax",
        ).strip().lower()
        self.auth_cookie_secure = _get_bool("AUTH_COOKIE_SECURE", False)
        self.auth_cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()

    def validate(self) -> None:
        missing: list[str] = []

        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_publishable_key:
            missing.append("SUPABASE_PUBLISHABLE_KEY")
        if not self.supabase_secret_key:
            missing.append("SUPABASE_SECRET_KEY")

        if missing:
            raise RuntimeError(
                f"Missing required auth environment variables: {', '.join(missing)}"
            )


auth_settings = AuthSettings()