from __future__ import annotations

from types import SimpleNamespace

from fastapi import Response

from app.services import auth_cookies


def test_cookie_domain_returns_none_when_blank(monkeypatch):
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "auth_cookie_domain",
        "   ",
    )

    assert auth_cookies._cookie_domain() is None


def test_cookie_domain_returns_trimmed_domain(monkeypatch):
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "auth_cookie_domain",
        " .earlybloom.app ",
    )

    assert auth_cookies._cookie_domain() == ".earlybloom.app"


def test_set_auth_cookies_sets_both_access_and_refresh(monkeypatch):
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "access_cookie_name",
        "eb-access",
    )
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "refresh_cookie_name",
        "eb-refresh",
    )
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "auth_cookie_secure",
        True,
    )
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "auth_cookie_samesite",
        "lax",
    )
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "refresh_cookie_max_age_seconds",
        86400,
    )
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "auth_cookie_domain",
        ".example.com",
    )

    response = Response()
    session = SimpleNamespace(
        access_token="access-123",
        refresh_token="refresh-456",
        expires_in=1800,
    )

    auth_cookies.set_auth_cookies(response, session)

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2

    access_cookie = next(cookie for cookie in cookies if "eb-access=" in cookie)
    refresh_cookie = next(cookie for cookie in cookies if "eb-refresh=" in cookie)

    assert "eb-access=access-123" in access_cookie
    assert "HttpOnly" in access_cookie
    assert "Max-Age=1800" in access_cookie
    assert "Path=/" in access_cookie
    assert "SameSite=lax" in access_cookie
    assert "Secure" in access_cookie
    assert "Domain=.example.com" in access_cookie

    assert "eb-refresh=refresh-456" in refresh_cookie
    assert "HttpOnly" in refresh_cookie
    assert "Max-Age=86400" in refresh_cookie
    assert "Path=/" in refresh_cookie
    assert "SameSite=lax" in refresh_cookie
    assert "Secure" in refresh_cookie
    assert "Domain=.example.com" in refresh_cookie


def test_set_auth_cookies_sets_only_access_when_refresh_missing(monkeypatch):
    monkeypatch.setattr(auth_cookies.auth_settings, "access_cookie_name", "eb-access")
    monkeypatch.setattr(auth_cookies.auth_settings, "refresh_cookie_name", "eb-refresh")
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_secure", False)
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_samesite", "lax")
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "refresh_cookie_max_age_seconds",
        86400,
    )
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_domain", "")

    response = Response()
    session = SimpleNamespace(
        access_token="access-123",
        refresh_token=None,
        expires_in=900,
    )

    auth_cookies.set_auth_cookies(response, session)

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 1
    assert "eb-access=access-123" in cookies[0]
    assert "eb-refresh=" not in cookies[0]
    assert "Domain=" not in cookies[0]


def test_set_auth_cookies_sets_only_refresh_when_access_missing(monkeypatch):
    monkeypatch.setattr(auth_cookies.auth_settings, "access_cookie_name", "eb-access")
    monkeypatch.setattr(auth_cookies.auth_settings, "refresh_cookie_name", "eb-refresh")
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_secure", False)
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_samesite", "strict")
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "refresh_cookie_max_age_seconds",
        7200,
    )
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_domain", "")

    response = Response()
    session = SimpleNamespace(
        access_token=None,
        refresh_token="refresh-456",
        expires_in=1200,
    )

    auth_cookies.set_auth_cookies(response, session)

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 1
    assert "eb-refresh=refresh-456" in cookies[0]
    assert "Max-Age=7200" in cookies[0]
    assert "SameSite=strict" in cookies[0]


def test_set_auth_cookies_defaults_expires_in_to_3600_when_missing(monkeypatch):
    monkeypatch.setattr(auth_cookies.auth_settings, "access_cookie_name", "eb-access")
    monkeypatch.setattr(auth_cookies.auth_settings, "refresh_cookie_name", "eb-refresh")
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_secure", False)
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_samesite", "lax")
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "refresh_cookie_max_age_seconds",
        86400,
    )
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_domain", "")

    response = Response()
    session = SimpleNamespace(
        access_token="access-123",
        refresh_token=None,
    )

    auth_cookies.set_auth_cookies(response, session)

    cookie = response.headers.getlist("set-cookie")[0]
    assert "Max-Age=3600" in cookie


def test_set_auth_cookies_defaults_expires_in_to_3600_when_falsey(monkeypatch):
    monkeypatch.setattr(auth_cookies.auth_settings, "access_cookie_name", "eb-access")
    monkeypatch.setattr(auth_cookies.auth_settings, "refresh_cookie_name", "eb-refresh")
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_secure", False)
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_samesite", "lax")
    monkeypatch.setattr(
        auth_cookies.auth_settings,
        "refresh_cookie_max_age_seconds",
        86400,
    )
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_domain", "")

    response = Response()
    session = SimpleNamespace(
        access_token="access-123",
        refresh_token=None,
        expires_in=0,
    )

    auth_cookies.set_auth_cookies(response, session)

    cookie = response.headers.getlist("set-cookie")[0]
    assert "Max-Age=3600" in cookie


def test_clear_auth_cookies_deletes_both_cookies(monkeypatch):
    monkeypatch.setattr(auth_cookies.auth_settings, "access_cookie_name", "eb-access")
    monkeypatch.setattr(auth_cookies.auth_settings, "refresh_cookie_name", "eb-refresh")
    monkeypatch.setattr(auth_cookies.auth_settings, "auth_cookie_domain", ".example.com")

    response = Response()

    auth_cookies.clear_auth_cookies(response)

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2

    access_cookie = next(cookie for cookie in cookies if "eb-access=" in cookie)
    refresh_cookie = next(cookie for cookie in cookies if "eb-refresh=" in cookie)

    assert "Max-Age=0" in access_cookie
    assert "Path=/" in access_cookie
    assert "Domain=.example.com" in access_cookie

    assert "Max-Age=0" in refresh_cookie
    assert "Path=/" in refresh_cookie
    assert "Domain=.example.com" in refresh_cookie