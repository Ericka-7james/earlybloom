from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response

from app.core.auth_settings import auth_settings
from app.schemas.auth import (
    AuthMessageResponse,
    AuthSessionResponse,
    SignInRequest,
    SignUpRequest,
    UpdateProfileRequest,
)
from app.services.auth_cookies import clear_auth_cookies, set_auth_cookies
from app.services.auth_service import (
    CurrentSessionContext,
    fetch_profile_for_user_id,
    sign_in_user,
    sign_out_session,
    sign_up_user,
    update_profile_for_user_id,
    verify_or_refresh_session,
    _to_profile_response,
    _to_user_response,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_session_context(
    access_token: str | None = Cookie(
        default=None,
        alias=auth_settings.access_cookie_name,
    ),
    refresh_token: str | None = Cookie(
        default=None,
        alias=auth_settings.refresh_cookie_name,
    ),
) -> CurrentSessionContext:
    """Resolves the current authenticated user from secure cookies."""
    return verify_or_refresh_session(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/sign-up", response_model=AuthSessionResponse)
def sign_up(payload: SignUpRequest, response: Response) -> AuthSessionResponse:
    """Creates a new account and stores session cookies when available."""
    auth_response, session = sign_up_user(payload)

    if session is not None:
      set_auth_cookies(response, session)

    return auth_response


@router.post("/sign-in", response_model=AuthSessionResponse)
def sign_in(payload: SignInRequest, response: Response) -> AuthSessionResponse:
    """Signs a user in and stores session cookies."""
    auth_response, session = sign_in_user(payload)
    set_auth_cookies(response, session)
    return auth_response


@router.post("/sign-out", response_model=AuthMessageResponse)
def sign_out(
    response: Response,
    access_token: str | None = Cookie(
        default=None,
        alias=auth_settings.access_cookie_name,
    ),
    refresh_token: str | None = Cookie(
        default=None,
        alias=auth_settings.refresh_cookie_name,
    ),
) -> AuthMessageResponse:
    """Signs the user out and clears cookies."""
    sign_out_session(access_token=access_token, refresh_token=refresh_token)
    clear_auth_cookies(response)
    return AuthMessageResponse(message="Signed out successfully.")


@router.get("/session", response_model=AuthSessionResponse)
def get_session(
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
) -> AuthSessionResponse:
    """Returns the current authenticated session summary."""
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)

    profile_row = fetch_profile_for_user_id(str(getattr(current.user, "id")))

    return AuthSessionResponse(
        authenticated=True,
        requires_email_verification=False,
        user=_to_user_response(current.user),
        profile=_to_profile_response(profile_row),
    )


@router.patch("/profile", response_model=AuthSessionResponse)
def update_profile(
    payload: UpdateProfileRequest,
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
) -> AuthSessionResponse:
    """Updates the current user's application profile preferences."""
    if current.refreshed and current.session is not None:
        set_auth_cookies(response, current.session)

    user_id = str(getattr(current.user, "id"))
    user_email = getattr(current.user, "email", None)

    profile_row = update_profile_for_user_id(
        user_id=user_id,
        user_email=user_email,
        payload=payload,
    )

    return AuthSessionResponse(
        authenticated=True,
        requires_email_verification=False,
        user=_to_user_response(current.user),
        profile=_to_profile_response(profile_row),
    )


@router.get("/me", response_model=AuthSessionResponse)
def get_me(
    response: Response,
    current: CurrentSessionContext = Depends(get_current_session_context),
) -> AuthSessionResponse:
    """Alias route for current session/profile lookup."""
    return get_session(response=response, current=current)