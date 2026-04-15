from __future__ import annotations

import httpx
import pytest

from app.services.jobs.providers.remotive import RemotiveProvider


class FakeResponse:
    def __init__(self, payload, *, should_raise: bool = False):
        self._payload = payload
        self._should_raise = should_raise

    def raise_for_status(self):
        if self._should_raise:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(500),
            )

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append({"url": url, "params": params})
        if self.error:
            raise self.error
        return self.response


def test_from_env_returns_none_when_disabled(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_REMOTIVE_ENABLED = False

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.get_settings",
        lambda: FakeSettings(),
    )

    result = RemotiveProvider.from_env()

    assert result is None


def test_from_env_builds_provider_from_settings(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_REMOTIVE_ENABLED = True
        JOB_PROVIDER_TIMEOUT_SECONDS = 9.5
        JOB_PROVIDER_MAX_JOBS_PER_SOURCE = 42
        JOB_PROVIDER_REMOTIVE_CATEGORY = "software-dev"
        JOB_PROVIDER_REMOTIVE_SEARCH = "python"

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.get_settings",
        lambda: FakeSettings(),
    )

    result = RemotiveProvider.from_env()

    assert isinstance(result, RemotiveProvider)
    assert result.timeout_seconds == 9.5
    assert result.max_jobs == 42
    assert result.category == "software-dev"
    assert result.search == "python"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_http_error(monkeypatch):
    fake_client = FakeAsyncClient(
        error=httpx.ConnectError(
            "network down",
            request=httpx.Request("GET", "https://example.com"),
        )
    )

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = RemotiveProvider()

    result = await provider.fetch_jobs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_payload_jobs_not_list(monkeypatch):
    fake_client = FakeAsyncClient(response=FakeResponse({"jobs": "not-a-list"}))

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = RemotiveProvider()

    result = await provider.fetch_jobs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_jobs_passes_category_and_search_params(monkeypatch):
    payload = {
        "jobs": [
            {
                "id": 123,
                "title": "Junior Python Developer",
                "company_name": "Remotive Co",
                "candidate_required_location": "Remote - US",
                "url": "https://example.com/job/123",
                "description": "<p>Build APIs with Python and FastAPI</p>",
                "category": "Software Development",
                "job_type": "Full-Time",
                "tags": ["Python", "FastAPI", "Remote"],
            }
        ]
    }
    fake_client = FakeAsyncClient(response=FakeResponse(payload))

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = RemotiveProvider(
        timeout_seconds=3.0,
        max_jobs=10,
        category="software-dev",
        search="python",
    )

    result = await provider.fetch_jobs()

    assert len(result) == 1
    assert fake_client.calls == [
        {
            "url": provider.base_url,
            "params": {"category": "software-dev", "search": "python"},
        }
    ]


@pytest.mark.asyncio
async def test_fetch_jobs_skips_non_dict_items_and_respects_max_jobs(monkeypatch):
    payload = {
        "jobs": [
            "not-a-dict",
            {
                "id": 1,
                "title": "Junior Backend Engineer",
                "company_name": "A Co",
                "candidate_required_location": "Remote",
                "url": "https://example.com/job/1",
                "description": "<p>Python SQL APIs</p>",
                "category": "Engineering",
                "job_type": "Full-Time",
                "tags": ["Python"],
            },
            {
                "id": 2,
                "title": "Junior Frontend Engineer",
                "company_name": "B Co",
                "candidate_required_location": "Remote",
                "url": "https://example.com/job/2",
                "description": "<p>React UI work</p>",
                "category": "Engineering",
                "job_type": "Full-Time",
                "tags": ["React"],
            },
        ]
    }
    fake_client = FakeAsyncClient(response=FakeResponse(payload))

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.httpx.AsyncClient",
        lambda timeout: fake_client,
    )

    provider = RemotiveProvider(max_jobs=2)

    result = await provider.fetch_jobs()

    assert len(result) == 1
    assert result[0].title == "Junior Backend Engineer"


def test_normalize_job_returns_none_when_required_fields_missing():
    provider = RemotiveProvider()

    assert provider._normalize_job(
        {"title": "", "company_name": "X", "url": "https://x.com"}
    ) is None

    result = provider._normalize_job(
        {"title": "Engineer", "company_name": "", "url": "https://x.com"}
    )
    assert result is not None
    assert result.company == "Unknown Company"

    assert provider._normalize_job(
        {"title": "Engineer", "company_name": "X", "url": ""}
    ) is None


def test_normalize_job_filters_out_obviously_senior_titles():
    provider = RemotiveProvider()

    result = provider._normalize_job(
        {
            "id": 1,
            "title": "Senior Backend Engineer",
            "company_name": "Big Co",
            "candidate_required_location": "Remote",
            "url": "https://example.com/job/1",
            "description": "<p>Python APIs</p>",
            "category": "Software Development",
            "job_type": "Full-Time",
            "tags": ["Python"],
        }
    )

    assert result is None


def test_normalize_job_filters_out_titles_not_kept_for_earlybloom(monkeypatch):
    provider = RemotiveProvider()

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.should_keep_title_for_earlybloom",
        lambda title: False,
    )

    result = provider._normalize_job(
        {
            "id": 1,
            "title": "Software Engineer",
            "company_name": "Big Co",
            "candidate_required_location": "Remote",
            "url": "https://example.com/job/1",
            "description": "<p>Python APIs</p>",
            "category": "Software Development",
            "job_type": "Full-Time",
            "tags": ["Python"],
        }
    )

    assert result is None


def test_normalize_job_maps_fields_into_normalized_job(monkeypatch):
    provider = RemotiveProvider()

    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.extract_skill_hints",
        lambda text, role_type, limit: ["python", "fastapi"],
    )
    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.infer_role_type_from_text",
        lambda **kwargs: "software_engineering",
    )
    monkeypatch.setattr(
        "app.services.jobs.providers.remotive.infer_experience_level_from_text",
        lambda **kwargs: "junior",
    )

    result = provider._normalize_job(
        {
            "id": 123,
            "title": "Junior Python Developer",
            "company_name": "Remotive Co",
            "candidate_required_location": "Remote - US",
            "url": "https://example.com/job/123",
            "description": "<p>Build APIs with Python and FastAPI</p>",
            "category": "Software Development",
            "job_type": "Full-Time",
            "tags": ["Python", "FastAPI", "Remote"],
        }
    )

    assert result is not None
    assert result.title == "Junior Python Developer"
    assert result.company == "Remotive Co"
    assert result.location == "Remote - US"
    assert result.url == "https://example.com/job/123"
    assert result.source == "remotive"
    assert result.remote is True
    assert result.employment_type == "Full-Time"
    assert result.experience_level == "junior"
    assert result.required_skills == ["python", "fastapi"]
    assert result.preferred_skills == ["Python", "FastAPI", "Remote"]
    assert result.description == "Build APIs with Python and FastAPI"


def test_normalize_experience_level_maps_supported_values():
    provider = RemotiveProvider()

    assert provider._normalize_experience_level("entry") == "entry-level"
    assert provider._normalize_experience_level("entry-level") == "entry-level"
    assert provider._normalize_experience_level("junior") == "junior"
    assert provider._normalize_experience_level("mid") == "mid-level"
    assert provider._normalize_experience_level("mid-level") == "mid-level"
    assert provider._normalize_experience_level("midlevel") == "mid-level"
    assert provider._normalize_experience_level("senior") == "senior"
    assert provider._normalize_experience_level("weird") == "unknown"
    assert provider._normalize_experience_level(None) == "unknown"


def test_coerce_string_list_dedupes_and_ignores_non_strings():
    provider = RemotiveProvider()

    result = provider._coerce_string_list(["Python", "python", " React ", None, ""])

    assert result == ["Python", "React"]


def test_coerce_string_list_returns_empty_for_non_list():
    provider = RemotiveProvider()

    assert provider._coerce_string_list("python") == []
    assert provider._coerce_string_list(None) == []


def test_safe_str_returns_trimmed_string_or_empty():
    provider = RemotiveProvider()

    assert provider._safe_str("  hello  ") == "hello"
    assert provider._safe_str(123) == "123"
    assert provider._safe_str(None) == ""