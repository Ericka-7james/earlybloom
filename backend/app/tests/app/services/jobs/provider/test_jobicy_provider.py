from __future__ import annotations

import httpx
import pytest

from app.services.jobs.providers.jobicy import JobicyProvider


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
        "jobTitle": "Junior Python Developer",
        "url": "https://jobicy.com/jobs/123",
        "companyName": "Jobicy Corp",
        "jobGeo": "Remote US",
        "jobDescription": "<p>Build APIs with Python and FastAPI</p>",
    }


def test_from_env_returns_none_when_disabled(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_JOBICY_ENABLED = False

    monkeypatch.setattr(
        "app.services.jobs.providers.jobicy.get_settings",
        lambda: FakeSettings(),
    )

    assert JobicyProvider.from_env() is None


def test_from_env_builds_provider(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_JOBICY_ENABLED = True
        JOB_PROVIDER_TIMEOUT_SECONDS = 8
        JOB_PROVIDER_MAX_JOBS_PER_SOURCE = 25
        JOB_PROVIDER_JOBICY_PAGES = 4

    monkeypatch.setattr(
        "app.services.jobs.providers.jobicy.get_settings",
        lambda: FakeSettings(),
    )

    provider = JobicyProvider.from_env()

    assert provider is not None
    assert provider.timeout_seconds == 8
    assert provider.max_jobs == 25
    assert provider.pages == 4


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_on_http_error(monkeypatch):
    fake_client = FakeAsyncClient(
        error=httpx.ConnectError(
            "network down",
            request=httpx.Request("GET", "https://example.com"),
        )
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.jobicy.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = JobicyProvider()

    result = await provider.fetch_jobs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_jobs_stops_when_payload_empty(monkeypatch):
    fake_client = FakeAsyncClient(
        responses=[
            FakeResponse({"jobs": []}),
        ]
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.jobicy.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = JobicyProvider()

    result = await provider.fetch_jobs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_jobs_uses_jobs_key(monkeypatch):
    fake_client = FakeAsyncClient(
        responses=[
            FakeResponse({"jobs": [sample_job()]}),
            FakeResponse({"jobs": []}),
        ]
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.jobicy.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = JobicyProvider(pages=2)

    result = await provider.fetch_jobs()

    assert len(result) == 1
    assert result[0].title == "Junior Python Developer"
    assert fake_client.calls[0]["params"] == {"page": 1}
    assert fake_client.calls[1]["params"] == {"page": 2}


@pytest.mark.asyncio
async def test_fetch_jobs_uses_data_key(monkeypatch):
    fake_client = FakeAsyncClient(
        responses=[
            FakeResponse({"data": [sample_job()]}),
            FakeResponse({"data": []}),
        ]
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.jobicy.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = JobicyProvider(pages=2)

    result = await provider.fetch_jobs()

    assert len(result) == 1
    assert result[0].company == "Jobicy Corp"


@pytest.mark.asyncio
async def test_fetch_jobs_respects_max_jobs(monkeypatch):
    fake_client = FakeAsyncClient(
        responses=[
            FakeResponse({"jobs": [sample_job(), sample_job()]}),
        ]
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.jobicy.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = JobicyProvider(max_jobs=1, pages=1)

    result = await provider.fetch_jobs()

    assert len(result) == 1


def test_normalize_job_returns_none_when_required_fields_missing():
    provider = JobicyProvider()

    assert provider._normalize_job({}) is None
    assert provider._normalize_job({"jobTitle": "Engineer"}) is None
    assert provider._normalize_job({"url": "https://x.com"}) is None


def test_normalize_job_filters_senior_title():
    provider = JobicyProvider()

    job = sample_job()
    job["jobTitle"] = "Senior Staff Engineer"

    assert provider._normalize_job(job) is None


def test_normalize_job_maps_fields():
    provider = JobicyProvider()

    result = provider._normalize_job(sample_job())

    assert result is not None
    assert result.title == "Junior Python Developer"
    assert result.company == "Jobicy Corp"
    assert result.location == "Remote US"
    assert result.url == "https://jobicy.com/jobs/123"
    assert result.source == "jobicy"
    assert result.salary_currency == "USD"
    assert result.remote is True
    assert result.experience_level in {
        "entry-level",
        "junior",
        "mid-level",
        "senior",
        "unknown",
    }


def test_normalize_job_uses_fallback_values():
    provider = JobicyProvider()

    result = provider._normalize_job(
        {
            "title": "Junior Developer",
            "url": "https://x.com",
            "company": "",
            "location": "",
            "description": "Python work",
        }
    )

    assert result is not None
    assert result.company == "Unknown Company"
    assert result.location == "Remote"


def test_normalize_experience_level_maps_values():
    provider = JobicyProvider()

    assert provider._normalize_experience_level("entry") == "entry-level"
    assert provider._normalize_experience_level("entry-level") == "entry-level"
    assert provider._normalize_experience_level("junior") == "junior"
    assert provider._normalize_experience_level("mid") == "mid-level"
    assert provider._normalize_experience_level("midlevel") == "mid-level"
    assert provider._normalize_experience_level("senior") == "senior"
    assert provider._normalize_experience_level("weird") == "unknown"
    assert provider._normalize_experience_level(None) == "unknown"


def test_safe_str_returns_trimmed_or_empty():
    provider = JobicyProvider()

    assert provider._safe_str(" hello ") == "hello"
    assert provider._safe_str(123) == "123"
    assert provider._safe_str(None) == ""