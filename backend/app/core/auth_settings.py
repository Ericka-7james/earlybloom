from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AuthSettings:
    def __init__(self) -> None:
        self.frontend_origin = os.getenv(
            "EARLYBLOOM_FRONTEND_ORIGIN",
            "http://localhost:5173",
        )
        self.cors_origins = os.getenv("CORS_ORIGINS", "")

        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
        self.supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY", "")

        self.jwt_secret = os.getenv("JWT_SECRET", "")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )

        self.access_cookie_name = os.getenv("AUTH_COOKIE_ACCESS_NAME", "eb_access_token")
        self.refresh_cookie_name = os.getenv("AUTH_COOKIE_REFRESH_NAME", "eb_refresh_token")
        self.auth_cookie_samesite = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
        self.auth_cookie_secure = _get_bool("AUTH_COOKIE_SECURE", False)
        self.auth_cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", "")

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