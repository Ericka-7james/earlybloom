from __future__ import annotations

import httpx
import pytest

from app.services.jobs.providers.arbeitnow import ArbeitNowProvider


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses=None, error=None):
        self.responses = responses or []
        self.error = error
        self.calls = []
        self.index = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append({"url": url, "params": params})
        if self.error:
            raise self.error
        response = self.responses[self.index]
        self.index += 1
        return response


def sample_job():
    return {
        "id": 123,
        "slug": "junior-python-dev",
        "title": "Junior Python Developer",
        "company_name": "Arbeit Co",
        "location": "Berlin, Germany",
        "url": "https://arbeitnow.com/jobs/junior-python-dev",
        "description": "<p>Build APIs with Python and FastAPI</p>",
        "tags": ["Python", "FastAPI", "Remote"],
    }


def test_from_env_returns_none_when_disabled(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_ARBEITNOW_ENABLED = False

    monkeypatch.setattr(
        "app.services.jobs.providers.arbeitnow.get_settings",
        lambda: FakeSettings(),
    )

    assert ArbeitNowProvider.from_env() is None


def test_from_env_builds_provider(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_ARBEITNOW_ENABLED = True
        JOB_PROVIDER_TIMEOUT_SECONDS = 8
        JOB_PROVIDER_MAX_JOBS_PER_SOURCE = 25
        JOB_PROVIDER_ARBEITNOW_PAGES = 4
        JOB_PROVIDER_ARBEITNOW_REMOTE_ONLY = True

    monkeypatch.setattr(
        "app.services.jobs.providers.arbeitnow.get_settings",
        lambda: FakeSettings(),
    )

    provider = ArbeitNowProvider.from_env()

    assert provider is not None
    assert provider.timeout_seconds == 8
    assert provider.max_jobs == 25
    assert provider.pages == 4
    assert provider.remote_only is True


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_on_http_error(monkeypatch):
    fake_client = FakeAsyncClient(
        error=httpx.ConnectError(
            "network down",
            request=httpx.Request("GET", "https://example.com"),
        )
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.arbeitnow.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = ArbeitNowProvider()

    result = await provider.fetch_jobs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_jobs_stops_when_payload_empty(monkeypatch):
    fake_client = FakeAsyncClient(
        responses=[
            FakeResponse({"data": []}),
        ]
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.arbeitnow.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = ArbeitNowProvider()

    result = await provider.fetch_jobs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_jobs_passes_remote_param_when_remote_only(monkeypatch):
    fake_client = FakeAsyncClient(
        responses=[
            FakeResponse({"data": [sample_job()]}),
            FakeResponse({"data": []}),
        ]
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.arbeitnow.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = ArbeitNowProvider(remote_only=True, pages=2)

    result = await provider.fetch_jobs()

    assert len(result) == 1
    assert fake_client.calls[0]["params"] == {"page": 1, "remote": "true"}
    assert fake_client.calls[1]["params"] == {"page": 2, "remote": "true"}


@pytest.mark.asyncio
async def test_fetch_jobs_respects_max_jobs(monkeypatch):
    fake_client = FakeAsyncClient(
        responses=[
            FakeResponse({"data": [sample_job(), sample_job()]}),
        ]
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.arbeitnow.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = ArbeitNowProvider(max_jobs=1, pages=1)

    result = await provider.fetch_jobs()

    assert len(result) == 1


def test_normalize_job_returns_none_when_required_fields_missing():
    provider = ArbeitNowProvider()

    assert provider._normalize_job({}) is None
    assert provider._normalize_job({"title": "Engineer"}) is None
    assert provider._normalize_job({"url": "https://x.com"}) is None


def test_normalize_job_filters_senior_title():
    provider = ArbeitNowProvider()

    job = sample_job()
    job["title"] = "Senior Staff Engineer"

    assert provider._normalize_job(job) is None


def test_normalize_job_maps_fields():
    provider = ArbeitNowProvider()

    result = provider._normalize_job(sample_job())

    assert result is not None
    assert result.title == "Junior Python Developer"
    assert result.company == "Arbeit Co"
    assert result.location == "Berlin, Germany"
    assert result.url == "https://arbeitnow.com/jobs/junior-python-dev"
    assert result.source == "arbeitnow"
    assert result.remote in {True, False}
    assert result.experience_level in {
        "entry-level",
        "junior",
        "mid-level",
        "senior",
        "unknown",
    }
    assert result.preferred_skills == ["Python", "FastAPI", "Remote"]
    assert result.description == "Build APIs with Python and FastAPI"


def test_normalize_job_uses_fallback_values():
    provider = ArbeitNowProvider()

    result = provider._normalize_job(
        {
            "title": "Junior Developer",
            "company_name": "",
            "location": "",
            "url": "https://x.com",
            "description": "Python work",
            "tags": [],
        }
    )

    assert result is not None
    assert result.company == "Unknown Company"
    assert result.location == "Unknown"


def test_normalize_experience_level_maps_values():
    provider = ArbeitNowProvider()

    assert provider._normalize_experience_level("entry") == "entry-level"
    assert provider._normalize_experience_level("entry-level") == "entry-level"
    assert provider._normalize_experience_level("junior") == "junior"
    assert provider._normalize_experience_level("mid") == "mid-level"
    assert provider._normalize_experience_level("midlevel") == "mid-level"
    assert provider._normalize_experience_level("senior") == "senior"
    assert provider._normalize_experience_level("weird") == "unknown"
    assert provider._normalize_experience_level(None) == "unknown"


def test_coerce_string_list_dedupes_and_ignores_non_strings():
    provider = ArbeitNowProvider()

    result = provider._coerce_string_list(["Python", "python", " FastAPI ", None, ""])

    assert result == ["Python", "FastAPI"]


def test_coerce_string_list_returns_empty_for_non_list():
    provider = ArbeitNowProvider()

    assert provider._coerce_string_list("python") == []
    assert provider._coerce_string_list(None) == []


def test_safe_str_returns_trimmed_or_empty():
    provider = ArbeitNowProvider()

    assert provider._safe_str(" hello ") == "hello"
    assert provider._safe_str(123) == "123"
    assert provider._safe_str(None) == ""