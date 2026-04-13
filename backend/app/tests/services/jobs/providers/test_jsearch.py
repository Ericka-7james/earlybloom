from __future__ import annotations

import httpx
import pytest

from app.services.jobs.providers.jsearch import JSearchProvider


class MockResponse:
    def __init__(self, payload, should_raise: bool = False) -> None:
        self._payload = payload
        self._should_raise = should_raise

    def raise_for_status(self) -> None:
        if self._should_raise:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://jsearch.p.rapidapi.com/search"),
                response=httpx.Response(500),
            )

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_fetch_jobs_returns_data_on_success(monkeypatch) -> None:
    payload = {
        "data": [
            {
                "job_id": "job-1",
                "job_title": "Frontend Engineer",
                "employer_name": "Bloom Labs",
                "job_city": "Atlanta",
                "job_state": "GA",
                "job_country": "US",
                "job_apply_link": "https://example.com/job-1",
                "job_description": "<p>Build polished UI experiences.</p>",
                "job_employment_type": "FULLTIME",
                "job_min_salary": 85000,
                "job_max_salary": 105000,
                "job_salary_currency": "USD",
                "job_is_remote": True,
                "job_publisher": "LinkedIn",
            },
            {
                "job_id": "job-2",
                "job_title": "IT Support Specialist",
                "employer_name": "Acme",
                "job_location": "Remote",
                "job_apply_link": "https://example.com/job-2",
                "job_description": "<p>Help employees resolve technical issues.</p>",
                "job_employment_type": "CONTRACTOR",
                "job_is_remote": True,
                "job_publisher": "Indeed",
            },
        ]
    }

    async def mock_get(self, url, headers=None, params=None):
        assert url == "https://jsearch.p.rapidapi.com/search"
        assert headers == {
            "X-RapidAPI-Key": "test-key",
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        assert params == {
            "query": "software engineer OR software developer OR IT support",
            "page": 1,
            "num_pages": 1,
            "country": "us",
        }
        return MockResponse(payload)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = JSearchProvider(
        api_key="test-key",
        timeout_seconds=6.0,
        max_jobs=100,
        page=1,
        num_pages=1,
        country="us",
    )
    jobs = await provider.fetch_jobs()

    assert len(jobs) == 2
    assert jobs[0].title == "Frontend Engineer"
    assert jobs[0].company == "Bloom Labs"
    assert jobs[0].source == "jsearch"
    assert jobs[0].salary_min == 85000
    assert jobs[0].salary_max == 105000
    assert jobs[0].salary_currency == "USD"

    assert jobs[1].title == "IT Support Specialist"
    assert jobs[1].company == "Acme"
    assert jobs[1].source == "jsearch"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_http_error(monkeypatch) -> None:
    async def mock_get(self, url, headers=None, params=None):
        raise httpx.ConnectError(
            "boom",
            request=httpx.Request("GET", "https://jsearch.p.rapidapi.com/search"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = JSearchProvider(api_key="test-key")
    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_payload_has_no_items(monkeypatch) -> None:
    async def mock_get(self, url, headers=None, params=None):
        return MockResponse({"data": []})

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = JSearchProvider(api_key="test-key")
    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_fetches_multiple_pages_and_respects_max_jobs(monkeypatch) -> None:
    payloads = [
        {
            "data": [
                {
                    "job_id": "job-1",
                    "job_title": "Frontend Engineer",
                    "employer_name": "Alpha",
                    "job_location": "Remote",
                    "job_apply_link": "https://example.com/job-1",
                    "job_description": "Build UI",
                    "job_is_remote": True,
                }
            ]
        },
        {
            "data": [
                {
                    "job_id": "job-2",
                    "job_title": "IT Support Analyst",
                    "employer_name": "Beta",
                    "job_location": "Atlanta, GA",
                    "job_apply_link": "https://example.com/job-2",
                    "job_description": "Support users",
                    "job_is_remote": False,
                }
            ]
        },
    ]
    calls = []

    async def mock_get(self, url, headers=None, params=None):
        calls.append(params)
        return MockResponse(payloads[len(calls) - 1])

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = JSearchProvider(
        api_key="test-key",
        max_jobs=1,
        page=1,
        num_pages=2,
        country="us",
    )
    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Frontend Engineer"
    assert calls == [
        {
            "query": "software engineer OR software developer OR IT support",
            "page": 1,
            "num_pages": 1,
            "country": "us",
        }
    ]


def test_normalize_job_returns_expected_shape() -> None:
    provider = JSearchProvider(api_key="test-key")

    raw_job = {
        "job_id": "jsearch-123",
        "job_title": "Frontend Engineer",
        "employer_name": "EarlyBloom",
        "job_city": "Atlanta",
        "job_state": "GA",
        "job_country": "US",
        "job_apply_link": "https://example.com/jobs/frontend-engineer",
        "job_description": (
            "<p>Responsibilities:</p>"
            "<ul><li>Build UI</li><li>Collaborate with design</li></ul>"
            "<p>Requirements:</p>"
            "<ul><li>React</li><li>JavaScript</li></ul>"
        ),
        "job_employment_type": "FULLTIME",
        "job_min_salary": 90000,
        "job_max_salary": 120000,
        "job_salary_currency": "USD",
        "job_is_remote": True,
        "job_publisher": "LinkedIn",
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is not None
    assert normalized.source == "jsearch"
    assert normalized.title == "Frontend Engineer"
    assert normalized.company == "EarlyBloom"
    assert normalized.location == "Atlanta, GA, US"
    assert normalized.url == "https://example.com/jobs/frontend-engineer"
    assert normalized.remote is True
    assert normalized.remote_type == "remote"
    assert normalized.employment_type == "FULLTIME"
    assert normalized.salary_min == 90000
    assert normalized.salary_max == 120000
    assert normalized.salary_currency == "USD"
    assert normalized.description
    assert normalized.experience_level in {
        "entry-level",
        "junior",
        "mid-level",
        "senior",
        "unknown",
    }
    assert isinstance(normalized.required_skills, list)
    assert isinstance(normalized.preferred_skills, list)


def test_normalize_job_returns_none_for_missing_required_fields() -> None:
    provider = JSearchProvider(api_key="test-key")

    raw_job = {
        "job_id": "jsearch-456",
        "job_title": "Frontend Engineer",
        "employer_name": "Bloom Labs",
        "job_description": "Build polished UI.",
        # missing apply/google url
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is None


def test_normalize_job_filters_obviously_senior_titles() -> None:
    provider = JSearchProvider(api_key="test-key")

    raw_job = {
        "job_id": "jsearch-789",
        "job_title": "Senior Frontend Engineer",
        "employer_name": "Bloom Labs",
        "job_location": "Remote",
        "job_apply_link": "https://example.com/jobs/senior-frontend-engineer",
        "job_description": "Lead architecture and mentor the team.",
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is None


def test_build_location_prefers_city_state_country() -> None:
    provider = JSearchProvider(api_key="test-key")

    item = {
        "job_city": "Atlanta",
        "job_state": "GA",
        "job_country": "US",
        "job_location": "Some fallback location",
    }

    assert provider._build_location(item) == "Atlanta, GA, US"


def test_build_location_falls_back_to_job_location_then_remote() -> None:
    provider = JSearchProvider(api_key="test-key")

    assert provider._build_location({"job_location": "Remote - US"}) == "Remote - US"
    assert provider._build_location({"job_is_remote": True}) == "Remote"
    assert provider._build_location({}) == ""


def test_extract_salary_range_handles_multiple_field_names() -> None:
    provider = JSearchProvider(api_key="test-key")

    item = {
        "job_salary_min": "85000",
        "job_salary_max": "110000",
    }

    salary_min, salary_max = provider._extract_salary_range(item)

    assert salary_min == 85000
    assert salary_max == 110000


def test_extract_salary_currency_returns_none_when_missing() -> None:
    provider = JSearchProvider(api_key="test-key")

    assert provider._extract_salary_currency({"job_salary_currency": "USD"}) == "USD"
    assert provider._extract_salary_currency({"job_currency": "EUR"}) == "EUR"
    assert provider._extract_salary_currency({}) is None


def test_normalize_experience_level_maps_values_to_schema_enum() -> None:
    provider = JSearchProvider(api_key="test-key")

    assert provider._normalize_experience_level("entry") == "entry-level"
    assert provider._normalize_experience_level("entry-level") == "entry-level"
    assert provider._normalize_experience_level("junior") == "junior"
    assert provider._normalize_experience_level("mid") == "mid-level"
    assert provider._normalize_experience_level("mid-level") == "mid-level"
    assert provider._normalize_experience_level("midlevel") == "mid-level"
    assert provider._normalize_experience_level("senior") == "senior"
    assert provider._normalize_experience_level("something-else") == "unknown"


def test_coerce_string_list_dedupes_and_skips_empty_values() -> None:
    provider = JSearchProvider(api_key="test-key")

    result = provider._coerce_string_list(
        ["LinkedIn", "linkedin", " Atlanta ", "", None, "US"]
    )

    assert result == ["LinkedIn", "Atlanta", "US"]


def test_safe_str_returns_stripped_string_or_empty_string() -> None:
    provider = JSearchProvider(api_key="test-key")

    assert provider._safe_str("  Bloom Labs  ") == "Bloom Labs"
    assert provider._safe_str(None) == ""