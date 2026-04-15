from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router as auth_router


VALID_SIGN_UP_PASSWORD = "Supersecret123!"


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)
    return app


def make_auth_session_response(
    *,
    authenticated: bool = True,
    requires_email_verification: bool = False,
    user_id: str = "user-123",
    email: str = "test@example.com",
    profile: dict | None = None,
) -> dict:
    return {
        "authenticated": authenticated,
        "requires_email_verification": requires_email_verification,
        "user": {
            "id": user_id,
            "email": email,
            "email_confirmed_at": None,
        },
        "profile": profile,
    }


def make_current_session_context(
    *,
    user_id: str = "user-123",
    email: str = "test@example.com",
    refreshed: bool = False,
    session: object | None = None,
):
    return SimpleNamespace(
        access_token="access-token",
        refresh_token="refresh-token",
        user=SimpleNamespace(
            id=user_id,
            email=email,
            email_confirmed_at=None,
        ),
        session=session,
        refreshed=refreshed,
    )


def test_sign_up_returns_auth_response_and_sets_cookies_when_session_exists(monkeypatch):
    from app.api.routes import auth as auth_module

    app = build_test_app()
    client = TestClient(app)

    auth_response = make_auth_session_response(
        authenticated=True,
        requires_email_verification=False,
    )

    fake_session = SimpleNamespace(
        access_token="new-access",
        refresh_token="new-refresh",
        expires_in=3600,
    )

    captured = {"payload": None, "session": None}

    def fake_sign_up_user(payload):
        captured["payload"] = payload
        return auth_response, fake_session

    def fake_set_auth_cookies(response, session):
        captured["session"] = session
        response.set_cookie("test-cookie", "set")

    monkeypatch.setattr(auth_module, "sign_up_user", fake_sign_up_user)
    monkeypatch.setattr(auth_module, "set_auth_cookies", fake_set_auth_cookies)

    response = client.post(
        "/auth/sign-up",
        json={
            "email": "test@example.com",
            "password": VALID_SIGN_UP_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json() == auth_response
    assert captured["payload"].email == "test@example.com"
    assert captured["payload"].password == VALID_SIGN_UP_PASSWORD
    assert captured["session"] is fake_session
    assert "test-cookie=set" in response.headers.get("set-cookie", "")


def test_sign_up_skips_cookie_write_when_session_is_none(monkeypatch):
    from app.api.routes import auth as auth_module

    app = build_test_app()
    client = TestClient(app)

    auth_response = make_auth_session_response(
        authenticated=False,
        requires_email_verification=True,
    )

    cookie_calls = {"count": 0}

    def fake_sign_up_user(payload):
        return auth_response, None

    def fake_set_auth_cookies(response, session):
        cookie_calls["count"] += 1

    monkeypatch.setattr(auth_module, "sign_up_user", fake_sign_up_user)
    monkeypatch.setattr(auth_module, "set_auth_cookies", fake_set_auth_cookies)

    response = client.post(
        "/auth/sign-up",
        json={
            "email": "test@example.com",
            "password": VALID_SIGN_UP_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json() == auth_response
    assert cookie_calls["count"] == 0


def test_sign_in_returns_auth_response_and_sets_cookies(monkeypatch):
    from app.api.routes import auth as auth_module

    app = build_test_app()
    client = TestClient(app)

    auth_response = make_auth_session_response()

    fake_session = SimpleNamespace(
        access_token="signed-in-access",
        refresh_token="signed-in-refresh",
        expires_in=3600,
    )

    captured = {"payload": None, "session": None}

    def fake_sign_in_user(payload):
        captured["payload"] = payload
        return auth_response, fake_session

    def fake_set_auth_cookies(response, session):
        captured["session"] = session
        response.set_cookie("test-cookie", "signed-in")

    monkeypatch.setattr(auth_module, "sign_in_user", fake_sign_in_user)
    monkeypatch.setattr(auth_module, "set_auth_cookies", fake_set_auth_cookies)

    response = client.post(
        "/auth/sign-in",
        json={
            "email": "test@example.com",
            "password": "supersecret123",
        },
    )

    assert response.status_code == 200
    assert response.json() == auth_response
    assert captured["payload"].email == "test@example.com"
    assert captured["payload"].password == "supersecret123"
    assert captured["session"] is fake_session


def test_sign_out_calls_service_with_cookie_tokens_and_clears_cookies(monkeypatch):
    from app.api.routes import auth as auth_module

    app = build_test_app()
    client = TestClient(app)

    captured = {
        "access_token": None,
        "refresh_token": None,
        "cleared": False,
    }

    def fake_sign_out_session(*, access_token, refresh_token):
        captured["access_token"] = access_token
        captured["refresh_token"] = refresh_token

    def fake_clear_auth_cookies(response):
        captured["cleared"] = True

    monkeypatch.setattr(auth_module, "sign_out_session", fake_sign_out_session)
    monkeypatch.setattr(auth_module, "clear_auth_cookies", fake_clear_auth_cookies)

    client.cookies.set(
        auth_module.auth_settings.access_cookie_name,
        "cookie-access",
    )
    client.cookies.set(
        auth_module.auth_settings.refresh_cookie_name,
        "cookie-refresh",
    )

    response = client.post("/auth/sign-out")

    assert response.status_code == 200

    body = response.json()
    assert body["message"] == "Signed out successfully."
    assert body["status"] == "ok"

    assert captured["access_token"] == "cookie-access"
    assert captured["refresh_token"] == "cookie-refresh"
    assert captured["cleared"] is True


def test_get_session_returns_authenticated_session_payload(monkeypatch):
    from app.api.routes import auth as auth_module

    app = build_test_app()
    client = TestClient(app)

    current = make_current_session_context()

    app.dependency_overrides[
        auth_module.get_current_session_context
    ] = lambda: current

    monkeypatch.setattr(
        auth_module,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "user_id": user_id,
            "email": "test@example.com",
            "display_name": "E",
            "desired_levels": ["entry-level", "junior"],
            "is_lgbtq_friendly_only": False,
            "created_at": None,
            "updated_at": None,
        },
    )

    monkeypatch.setattr(
        auth_module,
        "_to_user_response",
        lambda user: {
            "id": str(user.id),
            "email": user.email,
            "email_confirmed_at": None,
        },
    )

    monkeypatch.setattr(auth_module, "_to_profile_response", lambda row: row)

    response = client.get("/auth/session")

    assert response.status_code == 200

    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["id"] == "user-123"
    assert body["profile"]["display_name"] == "E"

    app.dependency_overrides.clear()


def test_get_session_reissues_cookies_when_session_was_refreshed(monkeypatch):
    from app.api.routes import auth as auth_module

    app = build_test_app()
    client = TestClient(app)

    refreshed_session = SimpleNamespace(
        access_token="refreshed-access",
        refresh_token="refreshed-refresh",
        expires_in=3600,
    )

    current = make_current_session_context(
        refreshed=True,
        session=refreshed_session,
    )

    captured = {"session": None}

    def fake_set_auth_cookies(response, session):
        captured["session"] = session
        response.set_cookie("test-cookie", "refreshed")

    app.dependency_overrides[
        auth_module.get_current_session_context
    ] = lambda: current

    monkeypatch.setattr(auth_module, "set_auth_cookies", fake_set_auth_cookies)
    monkeypatch.setattr(auth_module, "fetch_profile_for_user_id", lambda _: None)
    monkeypatch.setattr(
        auth_module,
        "_to_user_response",
        lambda user: {
            "id": str(user.id),
            "email": user.email,
            "email_confirmed_at": None,
        },
    )
    monkeypatch.setattr(auth_module, "_to_profile_response", lambda row: row)

    response = client.get("/auth/session")

    assert response.status_code == 200
    assert captured["session"] is refreshed_session

    app.dependency_overrides.clear()


def test_get_me_behaves_like_session_alias(monkeypatch):
    from app.api.routes import auth as auth_module

    app = build_test_app()
    client = TestClient(app)

    current = make_current_session_context()

    app.dependency_overrides[
        auth_module.get_current_session_context
    ] = lambda: current

    monkeypatch.setattr(auth_module, "fetch_profile_for_user_id", lambda _: None)
    monkeypatch.setattr(
        auth_module,
        "_to_user_response",
        lambda user: {
            "id": str(user.id),
            "email": user.email,
            "email_confirmed_at": None,
        },
    )
    monkeypatch.setattr(auth_module, "_to_profile_response", lambda row: row)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["authenticated"] is True

    app.dependency_overrides.clear()