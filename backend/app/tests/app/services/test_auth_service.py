from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.schemas.auth import SignInRequest, SignUpRequest, UpdateProfileRequest
from app.services import auth_service


class FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class FakeProfilesQuery:
    def __init__(self, client: "FakeServiceClient"):
        self.client = client
        self.payload = None
        self.on_conflict = None
        self.user_id = None
        self.selected = None

    def select(self, columns: str):
        self.selected = columns
        return self

    def eq(self, key: str, value):
        if key == "user_id":
            self.user_id = value
        return self

    def maybe_single(self):
        return self

    def upsert(self, payload, on_conflict: str):
        self.payload = payload
        self.on_conflict = on_conflict
        self.client.upsert_calls.append(
          {"payload": payload, "on_conflict": on_conflict}
        )
        return self

    def execute(self):
        if self.payload is not None:
            return FakeExecuteResult(self.client.upsert_result)
        return FakeExecuteResult(self.client.fetch_result)


class FakeServiceClient:
    def __init__(self, fetch_result=None, upsert_result=None):
        self.fetch_result = fetch_result
        self.upsert_result = upsert_result if upsert_result is not None else []
        self.upsert_calls: list[dict] = []
        self.table_calls: list[str] = []

    def table(self, name: str):
        self.table_calls.append(name)
        assert name == "profiles"
        return FakeProfilesQuery(self)


class FakePublicAuth:
    def __init__(
        self,
        *,
        sign_up_response=None,
        sign_up_exc: Exception | None = None,
        sign_in_response=None,
        sign_in_exc: Exception | None = None,
        get_user_response=None,
        get_user_exc: Exception | None = None,
        refresh_response=None,
        refresh_exc: Exception | None = None,
        set_session_exc: Exception | None = None,
        sign_out_exc: Exception | None = None,
    ):
        self.sign_up_response = sign_up_response
        self.sign_up_exc = sign_up_exc
        self.sign_in_response = sign_in_response
        self.sign_in_exc = sign_in_exc
        self.get_user_response = get_user_response
        self.get_user_exc = get_user_exc
        self.refresh_response = refresh_response
        self.refresh_exc = refresh_exc
        self.set_session_exc = set_session_exc
        self.sign_out_exc = sign_out_exc

        self.sign_up_calls: list[dict] = []
        self.sign_in_calls: list[dict] = []
        self.get_user_calls: list[str] = []
        self.refresh_calls: list[str] = []
        self.set_session_calls: list[tuple[str, str]] = []
        self.sign_out_calls = 0

    def sign_up(self, payload: dict):
        self.sign_up_calls.append(payload)
        if self.sign_up_exc:
            raise self.sign_up_exc
        return self.sign_up_response

    def sign_in_with_password(self, payload: dict):
        self.sign_in_calls.append(payload)
        if self.sign_in_exc:
            raise self.sign_in_exc
        return self.sign_in_response

    def get_user(self, access_token: str):
        self.get_user_calls.append(access_token)
        if self.get_user_exc:
            raise self.get_user_exc
        return self.get_user_response

    def refresh_session(self, refresh_token: str):
        self.refresh_calls.append(refresh_token)
        if self.refresh_exc:
            raise self.refresh_exc
        return self.refresh_response

    def set_session(self, access_token: str, refresh_token: str):
        self.set_session_calls.append((access_token, refresh_token))
        if self.set_session_exc:
            raise self.set_session_exc

    def sign_out(self):
        self.sign_out_calls += 1
        if self.sign_out_exc:
            raise self.sign_out_exc


class FakePublicClient:
    def __init__(self, auth: FakePublicAuth):
        self.auth = auth


def make_user(
    *,
    user_id: str = "user-123",
    email: str = "test@example.com",
    email_confirmed_at=None,
):
    return SimpleNamespace(
        id=user_id,
        email=email,
        email_confirmed_at=email_confirmed_at,
    )


def make_sign_up_request() -> SignUpRequest:
    return SignUpRequest(
        email="test@example.com",
        password="Supersecret123!",
        display_name="Er",
        avatar="petaloo",
        desired_levels=["entry-level", "junior"],
        is_lgbtq_friendly_only=True,
    )


def make_sign_in_request() -> SignInRequest:
    return SignInRequest(
        email="test@example.com",
        password="supersecret123",
    )


def test_http_error_builds_http_exception():
    exc = auth_service._http_error(418, "teapot")

    assert isinstance(exc, HTTPException)
    assert exc.status_code == 418
    assert exc.detail == "teapot"


def test_profile_select_columns_returns_expected_projection():
    assert auth_service._profile_select_columns() == (
        "user_id,"
        "email,"
        "display_name,"
        "avatar,"
        "desired_levels,"
        "is_lgbtq_friendly_only,"
        "created_at,"
        "updated_at"
    )


def test_to_optional_iso_string_handles_none_datetime_and_string():
    now = datetime.now(timezone.utc)

    assert auth_service._to_optional_iso_string(None) is None
    assert auth_service._to_optional_iso_string(now) == now.isoformat()
    assert auth_service._to_optional_iso_string("abc") == "abc"


def test_to_user_response_maps_user_fields():
    confirmed = datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)
    user = make_user(email_confirmed_at=confirmed)

    result = auth_service._to_user_response(user)

    assert result.id == "user-123"
    assert result.email == "test@example.com"
    assert result.email_confirmed_at == confirmed.isoformat()


def test_to_profile_response_returns_none_for_missing_profile():
    assert auth_service._to_profile_response(None) is None


def test_to_profile_response_maps_profile_row():
    row = {
        "user_id": "user-123",
        "email": "test@example.com",
        "display_name": "Er",
        "avatar": "petaloo",
        "desired_levels": ["entry-level", "junior"],
        "is_lgbtq_friendly_only": True,
        "created_at": None,
        "updated_at": None,
    }

    result = auth_service._to_profile_response(row)

    assert result.user_id == "user-123"
    assert result.display_name == "Er"
    assert result.avatar == "petaloo"
    assert result.is_lgbtq_friendly_only is True


def test_fetch_profile_for_user_id_returns_profile_row(monkeypatch):
    service_client = FakeServiceClient(
        fetch_result={
            "user_id": "user-123",
            "display_name": "Er",
        }
    )
    monkeypatch.setattr(
        auth_service,
        "get_supabase_service_client",
        lambda: service_client,
    )

    result = auth_service.fetch_profile_for_user_id("user-123")

    assert result == {
        "user_id": "user-123",
        "display_name": "Er",
        "avatar": "petaloo",
        "desired_levels": ["entry-level", "junior"],
        "is_lgbtq_friendly_only": False,
    }
    assert service_client.table_calls == ["profiles"]


def test_update_profile_for_user_id_merges_existing_profile(monkeypatch):
    service_client = FakeServiceClient(
        upsert_result=[
            {
                "user_id": "user-123",
                "email": "test@example.com",
                "display_name": "Updated Er",
                "avatar": "petaloo",
                "desired_levels": ["junior"],
                "is_lgbtq_friendly_only": True,
            }
        ]
    )

    monkeypatch.setattr(
        auth_service,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "user_id": user_id,
            "email": "test@example.com",
            "display_name": "Old Er",
            "avatar": "petaloo",
            "desired_levels": ["entry-level"],
            "is_lgbtq_friendly_only": False,
        },
    )
    monkeypatch.setattr(
        auth_service,
        "get_supabase_service_client",
        lambda: service_client,
    )

    payload = UpdateProfileRequest(
        display_name="Updated Er",
        desired_levels=["junior"],
        is_lgbtq_friendly_only=True,
    )

    result = auth_service.update_profile_for_user_id(
        user_id="user-123",
        user_email="test@example.com",
        payload=payload,
    )

    assert result["display_name"] == "Updated Er"
    assert service_client.upsert_calls == [
        {
            "payload": {
                "user_id": "user-123",
                "email": "test@example.com",
                "display_name": "Updated Er",
                "avatar": "petaloo",
                "desired_levels": ["junior"],
                "is_lgbtq_friendly_only": True,
            },
            "on_conflict": "user_id",
        }
    ]


def test_update_profile_for_user_id_uses_defaults_when_existing_missing(monkeypatch):
    service_client = FakeServiceClient(upsert_result=[])

    monkeypatch.setattr(auth_service, "fetch_profile_for_user_id", lambda user_id: None)
    monkeypatch.setattr(
        auth_service,
        "get_supabase_service_client",
        lambda: service_client,
    )

    payload = UpdateProfileRequest()

    result = auth_service.update_profile_for_user_id(
        user_id="user-123",
        user_email="test@example.com",
        payload=payload,
    )

    assert result == {
        "user_id": "user-123",
        "email": "test@example.com",
        "display_name": None,
        "avatar": "petaloo",
        "desired_levels": ["entry-level", "junior"],
        "is_lgbtq_friendly_only": False,
    }


def test_sign_up_user_returns_authenticated_response_when_session_exists(monkeypatch):
    user = make_user()
    session = SimpleNamespace(access_token="a", refresh_token="r", expires_in=3600)
    public_auth = FakePublicAuth(
        sign_up_response=SimpleNamespace(user=user, session=session)
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )
    monkeypatch.setattr(
        auth_service,
        "ensure_profile_for_user",
        lambda **kwargs: None,
    )

    response, returned_session = auth_service.sign_up_user(make_sign_up_request())

    assert returned_session is session
    assert response.authenticated is True
    assert response.requires_email_verification is False
    assert response.user is not None
    assert response.user.id == "user-123"
    assert response.profile is None

    assert public_auth.sign_up_calls == [
        {
            "email": "test@example.com",
            "password": "Supersecret123!",
            "options": {
                "data": {
                    "display_name": "Er",
                    "avatar": "petaloo",
                }
            },
        }
    ]


def test_sign_up_user_returns_verification_required_when_session_missing(monkeypatch):
    user = make_user()
    public_auth = FakePublicAuth(
        sign_up_response=SimpleNamespace(user=user, session=None)
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )
    monkeypatch.setattr(
        auth_service,
        "ensure_profile_for_user",
        lambda **kwargs: None,
    )

    response, returned_session = auth_service.sign_up_user(make_sign_up_request())

    assert returned_session is None
    assert response.authenticated is False
    assert response.requires_email_verification is True


def test_sign_up_user_raises_bad_request_when_supabase_sign_up_fails(monkeypatch):
    public_auth = FakePublicAuth(sign_up_exc=RuntimeError("signup failed"))

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.sign_up_user(make_sign_up_request())

    assert exc.value.status_code == 400
    assert exc.value.detail == "signup failed"


def test_sign_up_user_raises_when_user_missing_after_signup(monkeypatch):
    public_auth = FakePublicAuth(
        sign_up_response=SimpleNamespace(user=None, session=None)
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.sign_up_user(make_sign_up_request())

    assert exc.value.status_code == 400
    assert exc.value.detail == "Unable to create the account."


def test_sign_in_user_returns_session_and_profile(monkeypatch):
    user = make_user()
    session = SimpleNamespace(access_token="a", refresh_token="r")
    public_auth = FakePublicAuth(
        sign_in_response=SimpleNamespace(user=user, session=session)
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )
    monkeypatch.setattr(
        auth_service,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "user_id": user_id,
            "email": "test@example.com",
            "display_name": "Er",
            "avatar": "petaloo",
            "desired_levels": ["entry-level", "junior"],
            "is_lgbtq_friendly_only": False,
            "created_at": None,
            "updated_at": None,
        },
    )

    response, returned_session = auth_service.sign_in_user(make_sign_in_request())

    assert returned_session is session
    assert response.authenticated is True
    assert response.requires_email_verification is False
    assert response.user is not None
    assert response.profile is not None
    assert response.profile.user_id == "user-123"

    assert public_auth.sign_in_calls == [
        {
            "email": "test@example.com",
            "password": "supersecret123",
        }
    ]


def test_sign_in_user_raises_unauthorized_when_sign_in_fails(monkeypatch):
    public_auth = FakePublicAuth(sign_in_exc=RuntimeError("bad creds"))

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.sign_in_user(make_sign_in_request())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid email or password."


def test_sign_in_user_raises_when_user_or_session_missing(monkeypatch):
    public_auth = FakePublicAuth(
        sign_in_response=SimpleNamespace(user=None, session=None)
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.sign_in_user(make_sign_in_request())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Unable to establish a session."


def test_verify_or_refresh_session_returns_current_context_for_valid_access_token(
    monkeypatch,
):
    user = make_user()
    public_auth = FakePublicAuth(get_user_response=SimpleNamespace(user=user))

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    result = auth_service.verify_or_refresh_session(
        access_token="access-123",
        refresh_token="refresh-123",
    )

    assert result.access_token == "access-123"
    assert result.refresh_token == "refresh-123"
    assert result.user is user
    assert result.session is None
    assert result.refreshed is False


def test_verify_or_refresh_session_raises_when_no_tokens(monkeypatch):
    public_auth = FakePublicAuth(get_user_exc=RuntimeError("bad access"))

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_or_refresh_session(access_token=None, refresh_token=None)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated."


def test_verify_or_refresh_session_refreshes_when_access_token_invalid(monkeypatch):
    user = make_user()
    refreshed_session = SimpleNamespace(
        access_token="new-access",
        refresh_token="new-refresh",
    )
    public_auth = FakePublicAuth(
        get_user_exc=RuntimeError("expired"),
        refresh_response=SimpleNamespace(user=user, session=refreshed_session),
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    result = auth_service.verify_or_refresh_session(
        access_token="old-access",
        refresh_token="refresh-123",
    )

    assert result.access_token == "new-access"
    assert result.refresh_token == "new-refresh"
    assert result.user is user
    assert result.session is refreshed_session
    assert result.refreshed is True
    assert public_auth.refresh_calls == ["refresh-123"]


def test_verify_or_refresh_session_raises_when_refresh_fails(monkeypatch):
    public_auth = FakePublicAuth(refresh_exc=RuntimeError("refresh failed"))

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_or_refresh_session(
            access_token=None,
            refresh_token="refresh-123",
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Your session has expired. Please sign in again."


def test_verify_or_refresh_session_uses_refreshed_object_as_session_when_needed(
    monkeypatch,
):
    user = make_user()
    refreshed = SimpleNamespace(
        user=user,
        access_token="new-access",
        refresh_token="new-refresh",
    )
    public_auth = FakePublicAuth(
        refresh_response=refreshed,
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    result = auth_service.verify_or_refresh_session(
        access_token=None,
        refresh_token="refresh-123",
    )

    assert result.access_token == "new-access"
    assert result.refresh_token == "new-refresh"
    assert result.user is user
    assert result.session is refreshed
    assert result.refreshed is True


def test_verify_or_refresh_session_fetches_user_after_refresh_when_missing(monkeypatch):
    refreshed_session = SimpleNamespace(
        access_token="new-access",
        refresh_token="new-refresh",
    )
    user = make_user()
    public_auth = FakePublicAuth(
        refresh_response=SimpleNamespace(session=refreshed_session, user=None),
        get_user_response=SimpleNamespace(user=user),
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    result = auth_service.verify_or_refresh_session(
        access_token=None,
        refresh_token="refresh-123",
    )

    assert result.user is user
    assert public_auth.get_user_calls == ["new-access"]


def test_verify_or_refresh_session_raises_when_user_cannot_be_resolved_after_refresh(
    monkeypatch,
):
    refreshed_session = SimpleNamespace(
        access_token="new-access",
        refresh_token="new-refresh",
    )
    public_auth = FakePublicAuth(
        refresh_response=SimpleNamespace(session=refreshed_session, user=None),
        get_user_exc=RuntimeError("still broken"),
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_or_refresh_session(
            access_token=None,
            refresh_token="refresh-123",
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Unable to refresh the session."


def test_verify_or_refresh_session_raises_when_no_user_after_refresh(monkeypatch):
    refreshed_session = SimpleNamespace(
        access_token="new-access",
        refresh_token="new-refresh",
    )
    public_auth = FakePublicAuth(
        refresh_response=SimpleNamespace(session=refreshed_session, user=None),
        get_user_response=SimpleNamespace(user=None),
    )

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: FakePublicClient(public_auth),
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_or_refresh_session(
            access_token=None,
            refresh_token="refresh-123",
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Unable to refresh the session."


def test_sign_out_session_returns_early_when_tokens_missing(monkeypatch):
    public_auth = FakePublicAuth()
    public_client = FakePublicClient(public_auth)

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: public_client,
    )

    auth_service.sign_out_session(access_token=None, refresh_token="refresh")
    auth_service.sign_out_session(access_token="access", refresh_token=None)

    assert public_auth.set_session_calls == []
    assert public_auth.sign_out_calls == 0


def test_sign_out_session_sets_session_and_signs_out(monkeypatch):
    public_auth = FakePublicAuth()
    public_client = FakePublicClient(public_auth)

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: public_client,
    )

    auth_service.sign_out_session(access_token="access", refresh_token="refresh")

    assert public_auth.set_session_calls == [("access", "refresh")]
    assert public_auth.sign_out_calls == 1


def test_sign_out_session_swallows_exceptions(monkeypatch):
    public_auth = FakePublicAuth(set_session_exc=RuntimeError("boom"))
    public_client = FakePublicClient(public_auth)

    monkeypatch.setattr(
        auth_service,
        "get_supabase_public_client",
        lambda: public_client,
    )

    auth_service.sign_out_session(access_token="access", refresh_token="refresh")