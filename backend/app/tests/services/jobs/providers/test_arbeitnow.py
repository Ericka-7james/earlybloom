from __future__ import annotations

import httpx
import pytest

from app.services.jobs.providers.arbeitnow import ArbeitNowProvider


class MockResponse:
    def __init__(self, payload, should_raise: bool = False) -> None:
        self._payload = payload
        self._should_raise = should_raise

    def raise_for_status(self) -> None:
        if self._should_raise:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://www.arbeitnow.com/api/job-board-api"),
                response=httpx.Response(500),
            )

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_fetch_jobs_returns_data_on_success(monkeypatch) -> None:
    payload = {
        "data": [
            {
                "slug": "job-1",
                "title": "Frontend Engineer",
                "company_name": "Bloom Labs",
                "location": "Remote",
                "url": "https://example.com/job-1",
                "description": "<p>Build UI</p>",
                "tags": ["React", "TypeScript"],
            },
            {
                "slug": "job-2",
                "title": "Backend Engineer",
                "company_name": "Acme",
                "location": "Berlin",
                "url": "https://example.com/job-2",
                "description": "<p>Build APIs</p>",
                "tags": ["Python"],
            },
        ]
    }

    async def mock_get(self, url, params=None):
        assert url == "https://www.arbeitnow.com/api/job-board-api"
        assert params == {"page": 1}
        return MockResponse(payload)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = ArbeitNowProvider(timeout_seconds=6.0, max_jobs=100, pages=1)
    jobs = await provider.fetch_jobs()

    assert len(jobs) == 2
    assert jobs[0].title == "Frontend Engineer"
    assert jobs[0].company == "Bloom Labs"
    assert jobs[0].source == "arbeitnow"
    assert jobs[0].remote is True
    assert jobs[0].remote_type == "remote"

    assert jobs[1].title == "Backend Engineer"
    assert jobs[1].company == "Acme"
    assert jobs[1].source == "arbeitnow"


@pytest.mark.asyncio
async def test_fetch_jobs_includes_remote_param_when_requested(monkeypatch) -> None:
    payload = {"data": []}

    async def mock_get(self, url, params=None):
        assert url == "https://www.arbeitnow.com/api/job-board-api"
        assert params == {"page": 1, "remote": "true"}
        return MockResponse(payload)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = ArbeitNowProvider(
        timeout_seconds=6.0,
        max_jobs=100,
        pages=1,
        remote_only=True,
    )
    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_http_error(monkeypatch) -> None:
    async def mock_get(self, url, params=None):
        raise httpx.ConnectError(
            "boom",
            request=httpx.Request("GET", "https://www.arbeitnow.com/api/job-board-api"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = ArbeitNowProvider()
    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_stops_when_payload_has_no_items(monkeypatch) -> None:
    payload = {"data": []}

    async def mock_get(self, url, params=None):
        return MockResponse(payload)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = ArbeitNowProvider(pages=2)
    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_fetches_multiple_pages_and_respects_max_jobs(monkeypatch) -> None:
    payloads = [
        {
            "data": [
                {
                    "slug": "job-1",
                    "title": "Frontend Engineer",
                    "company_name": "Alpha",
                    "location": "Remote",
                    "url": "https://example.com/job-1",
                    "description": "<p>Job one</p>",
                    "tags": ["React"],
                }
            ]
        },
        {
            "data": [
                {
                    "slug": "job-2",
                    "title": "Backend Engineer",
                    "company_name": "Beta",
                    "location": "Berlin",
                    "url": "https://example.com/job-2",
                    "description": "<p>Job two</p>",
                    "tags": ["Python"],
                }
            ]
        },
    ]
    calls = []

    async def mock_get(self, url, params=None):
        calls.append(params)
        return MockResponse(payloads[len(calls) - 1])

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = ArbeitNowProvider(
        timeout_seconds=6.0,
        max_jobs=1,
        pages=2,
    )
    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Frontend Engineer"
    assert calls == [{"page": 1}]


def test_normalize_job_returns_expected_shape() -> None:
    provider = ArbeitNowProvider()

    raw_job = {
        "slug": "frontend-engineer-berlin",
        "title": "Frontend Engineer",
        "company_name": "Bloom Labs",
        "location": "Berlin / Remote",
        "url": "https://example.com/jobs/frontend-engineer",
        "description": "<p>Build delightful UI experiences.</p>",
        "tags": ["React", "TypeScript", "CSS"],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is not None
    assert normalized.source == "arbeitnow"
    assert normalized.title == "Frontend Engineer"
    assert normalized.company == "Bloom Labs"
    assert normalized.location == "Berlin / Remote"
    assert normalized.url == "https://example.com/jobs/frontend-engineer"
    assert normalized.remote is True
    assert normalized.remote_type == "remote"
    assert normalized.salary_min is None
    assert normalized.salary_max is None
    assert normalized.salary_currency is None
    assert normalized.description == "Build delightful UI experiences."
    assert normalized.employment_type is None
    assert normalized.experience_level in {
        "entry-level",
        "junior",
        "mid-level",
        "senior",
        "unknown",
    }
    assert isinstance(normalized.required_skills, list)
    assert isinstance(normalized.preferred_skills, list)
    assert normalized.preferred_skills == ["React", "TypeScript", "CSS"]


def test_normalize_job_returns_none_for_missing_required_fields() -> None:
    provider = ArbeitNowProvider()

    raw_job = {
        "slug": "job-1",
        "title": "Frontend Engineer",
        "company_name": "Bloom Labs",
        "location": "Remote",
        # missing url
        "description": "<p>Build UI</p>",
        "tags": ["React"],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is None


def test_normalize_job_filters_obviously_senior_titles() -> None:
    provider = ArbeitNowProvider()

    raw_job = {
        "slug": "senior-frontend-engineer",
        "title": "Senior Frontend Engineer",
        "company_name": "Bloom Labs",
        "location": "Remote",
        "url": "https://example.com/jobs/senior-frontend-engineer",
        "description": "<p>Lead architecture and mentor engineers.</p>",
        "tags": ["React"],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is None


def test_normalize_job_handles_non_remote_location() -> None:
    provider = ArbeitNowProvider()

    raw_job = {
        "slug": "backend-engineer-berlin",
        "title": "Backend Engineer",
        "company_name": "Bloom Labs",
        "location": "Berlin, Germany",
        "url": "https://example.com/jobs/backend-engineer",
        "description": "<p>Build backend systems.</p>",
        "tags": ["Python"],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is not None
    assert normalized.remote_type == "unknown"


def test_normalize_experience_level_maps_values_to_schema_enum() -> None:
    provider = ArbeitNowProvider()

    assert provider._normalize_experience_level("entry") == "entry-level"
    assert provider._normalize_experience_level("entry-level") == "entry-level"
    assert provider._normalize_experience_level("junior") == "junior"
    assert provider._normalize_experience_level("mid") == "mid-level"
    assert provider._normalize_experience_level("mid-level") == "mid-level"
    assert provider._normalize_experience_level("midlevel") == "mid-level"
    assert provider._normalize_experience_level("senior") == "senior"
    assert provider._normalize_experience_level("something-else") == "unknown"


def test_coerce_string_list_dedupes_and_skips_empty_values() -> None:
    provider = ArbeitNowProvider()

    result = provider._coerce_string_list(
        ["React", "react", " TypeScript ", "", None, "CSS"]
    )

    assert result == ["React", "TypeScript", "CSS"]


def test_safe_str_returns_stripped_string_or_empty_string() -> None:
    provider = ArbeitNowProvider()

    assert provider._safe_str("  Bloom Labs  ") == "Bloom Labs"
    assert provider._safe_str(None) == ""