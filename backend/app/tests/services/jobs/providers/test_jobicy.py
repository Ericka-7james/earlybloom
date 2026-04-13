from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.services.jobs.providers.jobicy import JobicyProvider


def make_provider(**overrides: Any) -> JobicyProvider:
    params = {
        "timeout_seconds": 6.0,
        "max_jobs": 10,
        "pages": 2,
    }
    params.update(overrides)
    return JobicyProvider(**params)


def make_jobicy_item(
    *,
    title: str = "Junior Software Engineer",
    company: str = "Bloom Labs",
    location: str = "United States",
    url: str = "https://jobicy.com/jobs/123",
    job_id: str = "123",
    description: str = (
        "<p>We are hiring a junior engineer to build APIs, React UI, "
        "debug production issues, write tests, and support customers. "
        "You will work with Python, JavaScript, SQL, CI/CD, and cloud tools. "
        "Strong communication and teamwork required.</p>"
    ),
) -> dict[str, Any]:
    return {
        "id": job_id,
        "jobTitle": title,
        "companyName": company,
        "jobGeo": location,
        "url": url,
        "jobDescription": description,
    }


def test_normalize_job_returns_normalized_job() -> None:
    provider = make_provider()

    job = provider._normalize_job(make_jobicy_item())

    assert job is not None
    assert job.title == "Junior Software Engineer"
    assert job.company == "Bloom Labs"
    assert job.location == "United States"
    assert job.source == "jobicy"
    assert job.url == "https://jobicy.com/jobs/123"
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency == "USD"
    assert job.employment_type is None
    assert job.experience_level in {"entry-level", "junior", "mid-level", "unknown"}
    assert isinstance(job.required_skills, list)
    assert isinstance(job.description, str)
    assert "React UI" in job.description or "React" in job.description


def test_normalize_job_uses_fallback_fields() -> None:
    provider = make_provider()

    item = {
        "id": "fallback-1",
        "title": "Junior Data Analyst",
        "company": "Fallback Co",
        "location": "Remote - US",
        "url": "https://jobicy.com/jobs/fallback-1",
        "description": "<p>Use SQL, Python, and dashboards.</p>",
    }

    job = provider._normalize_job(item)

    assert job is not None
    assert job.title == "Junior Data Analyst"
    assert job.company == "Fallback Co"
    assert job.location == "Remote - US"
    assert job.url == "https://jobicy.com/jobs/fallback-1"


def test_normalize_job_filters_senior_titles() -> None:
    provider = make_provider()

    item = make_jobicy_item(title="Senior Staff Engineer")

    job = provider._normalize_job(item)

    assert job is None


def test_normalize_job_filters_titles_not_kept_for_earlybloom() -> None:
    provider = make_provider()

    item = make_jobicy_item(title="Chief Technology Officer")

    job = provider._normalize_job(item)

    assert job is None


def test_normalize_job_filters_missing_required_title() -> None:
    provider = make_provider()

    item = make_jobicy_item(title="")

    job = provider._normalize_job(item)

    assert job is None


def test_normalize_job_filters_missing_required_url() -> None:
    provider = make_provider()

    item = make_jobicy_item(url="")

    job = provider._normalize_job(item)

    assert job is None


def test_normalize_job_defaults_company_and_location_when_missing() -> None:
    provider = make_provider()

    item = {
        "id": "job-blank-company",
        "jobTitle": "Junior QA Analyst",
        "companyName": "",
        "jobGeo": "",
        "url": "https://jobicy.com/jobs/qa-1",
        "jobDescription": "<p>Testing APIs and documenting bugs.</p>",
    }

    job = provider._normalize_job(item)

    assert job is not None
    assert job.company == "Unknown Company"
    assert job.location == "Remote"


def test_normalize_experience_level_maps_supported_values() -> None:
    provider = make_provider()

    assert provider._normalize_experience_level("entry") == "entry-level"
    assert provider._normalize_experience_level("entry-level") == "entry-level"
    assert provider._normalize_experience_level("junior") == "junior"
    assert provider._normalize_experience_level("mid") == "mid-level"
    assert provider._normalize_experience_level("mid-level") == "mid-level"
    assert provider._normalize_experience_level("midlevel") == "mid-level"
    assert provider._normalize_experience_level("senior") == "senior"
    assert provider._normalize_experience_level("principal") == "unknown"
    assert provider._normalize_experience_level(None) == "unknown"


def test_safe_str_handles_none_and_whitespace() -> None:
    provider = make_provider()

    assert provider._safe_str(None) == ""
    assert provider._safe_str("  hello  ") == "hello"
    assert provider._safe_str(123) == "123"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_normalized_jobs_from_jobs_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"jobs": [make_jobicy_item()]}

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            params: dict[str, Any],
        ) -> MockResponse:
            assert params == {"page": 1}
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(max_jobs=5, pages=1)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Junior Software Engineer"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_normalized_jobs_from_data_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"data": [make_jobicy_item(job_id="data-1", url="https://jobicy.com/jobs/data-1")]}

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            params: dict[str, Any],
        ) -> MockResponse:
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(max_jobs=5, pages=1)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].url == "https://jobicy.com/jobs/data-1"


@pytest.mark.asyncio
async def test_fetch_jobs_stops_when_payload_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"jobs": []}

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            params: dict[str, Any],
        ) -> MockResponse:
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(max_jobs=5, pages=2)

    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_skips_non_dict_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "jobs": [
                    "bad-item",
                    123,
                    make_jobicy_item(job_id="good-1", url="https://jobicy.com/jobs/good-1"),
                ]
            }

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            params: dict[str, Any],
        ) -> MockResponse:
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(max_jobs=5, pages=1)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Junior Software Engineer"


@pytest.mark.asyncio
async def test_fetch_jobs_stops_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, *, params: dict[str, Any]):
            raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider()

    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_respects_max_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "jobs": [
                    make_jobicy_item(job_id="1", url="https://jobicy.com/1"),
                    make_jobicy_item(job_id="2", url="https://jobicy.com/2"),
                    make_jobicy_item(job_id="3", url="https://jobicy.com/3"),
                ]
            }

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            params: dict[str, Any],
        ) -> MockResponse:
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(max_jobs=2, pages=1)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_fetch_jobs_stops_after_empty_second_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.calls = 0

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            params: dict[str, Any],
        ) -> MockResponse:
            self.calls += 1
            if self.calls == 1:
                return MockResponse(
                    {"jobs": [make_jobicy_item(job_id="1", url="https://jobicy.com/1")]}
                )
            return MockResponse({"jobs": []})

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(max_jobs=5, pages=2)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].url == "https://jobicy.com/1"