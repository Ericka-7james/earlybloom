from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


_ALLOWED_LEVELS = {"entry-level", "junior", "mid-level", "senior"}
_PASSWORD_SPECIAL_PATTERN = re.compile(r"""[!@#$%^&*(),.?":{}|<>_\-+=/\\[\]~`';]""")


class SignUpRequest(BaseModel):
    """Request body for creating a new account."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=10, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=80)
    desired_levels: list[str] = Field(
        default_factory=lambda: ["entry-level", "junior"]
    )
    is_lgbtq_friendly_only: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Performs lightweight email validation before handing off to Supabase."""
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Enter a valid email address.")

        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Enforces stronger password rules on the backend."""
        if len(value) < 10:
            raise ValueError("Password must be at least 10 characters long.")
        if any(ch.isspace() for ch in value):
            raise ValueError("Password cannot contain spaces.")
        if not any(ch.islower() for ch in value):
            raise ValueError("Password must include a lowercase letter.")
        if not any(ch.isupper() for ch in value):
            raise ValueError("Password must include an uppercase letter.")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must include a number.")
        if not _PASSWORD_SPECIAL_PATTERN.search(value):
            raise ValueError("Password must include a special character.")

        return value

    @field_validator("desired_levels")
    @classmethod
    def validate_desired_levels(cls, value: list[str]) -> list[str]:
        """Validates desired role levels."""
        if not value:
            raise ValueError("Choose at least one desired level.")

        normalized = []
        seen = set()

        for item in value:
            cleaned = item.strip().lower()
            if cleaned not in _ALLOWED_LEVELS:
                raise ValueError(f"Unsupported desired level: {item}")
            if cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)

        return normalized


class SignInRequest(BaseModel):
    """Request body for signing in with email and password."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Normalizes email for auth."""
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Enter a valid email address.")

        return value.lower()


class UpdateProfileRequest(BaseModel):
    """Request body for updating application profile preferences."""

    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: Optional[str] = Field(default=None, max_length=80)
    desired_levels: Optional[list[str]] = None
    is_lgbtq_friendly_only: Optional[bool] = None

    @field_validator("desired_levels")
    @classmethod
    def validate_desired_levels(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """Validates desired role levels if provided."""
        if value is None:
            return value

        if not value:
            raise ValueError("Choose at least one desired level.")

        normalized = []
        seen = set()

        for item in value:
            cleaned = item.strip().lower()
            if cleaned not in _ALLOWED_LEVELS:
                raise ValueError(f"Unsupported desired level: {item}")
            if cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)

        return normalized


class ProfileResponse(BaseModel):
    """Public profile payload returned to the frontend."""

    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    desired_levels: list[str] = Field(default_factory=list)
    is_lgbtq_friendly_only: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AuthUserResponse(BaseModel):
    """User summary returned to the frontend."""

    id: str
    email: Optional[str] = None
    email_confirmed_at: Optional[str] = None


class AuthSessionResponse(BaseModel):
    """Session summary returned to the frontend."""

    authenticated: bool
    requires_email_verification: bool = False
    user: Optional[AuthUserResponse] = None
    profile: Optional[ProfileResponse] = None


class AuthMessageResponse(BaseModel):
    """Simple message response."""

    message: str
    status: Literal["ok"] = "ok"