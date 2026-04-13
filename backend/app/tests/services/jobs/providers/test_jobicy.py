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
        "Salary is $80k-$100k with benefits and growth opportunities. "
        "You will work with Python, JavaScript, SQL, CI/CD, and cloud tools. "
        "Strong communication and teamwork required.</p>"
    ),
    tags: list[str] | None = None,
    job_type: str = "Full-time",
) -> dict[str, Any]:
    if tags is None:
        tags = ["Python", "React", "SQL"]

    return {
        "id": job_id,
        "jobTitle": title,
        "companyName": company,
        "jobGeo": location,
        "url": url,
        "jobDescription": description,
        "jobTags": tags,
        "jobType": job_type,
    }


def test_extract_items_handles_dict_payload() -> None:
    provider = make_provider()

    payload = {"jobs": [make_jobicy_item()]}

    items = provider._extract_items(payload)

    assert len(items) == 1
    assert items[0]["jobTitle"] == "Junior Software Engineer"


def test_extract_items_handles_list_payload() -> None:
    provider = make_provider()

    payload = [make_jobicy_item()]

    items = provider._extract_items(payload)

    assert len(items) == 1


def test_normalize_location_formats_regions() -> None:
    provider = make_provider()

    assert provider._normalize_location("United States") == "Remote (U.S.)"
    assert provider._normalize_location("worldwide") == "Remote (Global)"
    assert provider._normalize_location("Europe") == "Remote (Europe)"
    assert provider._normalize_location("LATAM") == "Remote (LATAM)"
    assert provider._normalize_location("Canada") == "Remote (Canada)"


def test_extract_salary_from_text_range() -> None:
    provider = make_provider()

    salary_min, salary_max = provider._extract_salary_from_text(
        "Compensation is $85k-$110k depending on experience."
    )

    assert salary_min == 85000
    assert salary_max == 110000


def test_extract_salary_from_text_single_value() -> None:
    provider = make_provider()

    salary_min, salary_max = provider._extract_salary_from_text(
        "Salary starts at $90k plus bonus."
    )

    assert salary_min == 90000
    assert salary_max is None


def test_low_quality_filters_crypto() -> None:
    provider = make_provider()

    assert provider._is_low_quality_job(
        "Engineer",
        "Build crypto token systems with blockchain tools." * 20,
        [],
    )


def test_low_quality_filters_short_description() -> None:
    provider = make_provider()

    assert provider._is_low_quality_job(
        "Engineer",
        "Too short",
        [],
    )


def test_normalize_job_returns_normalized_job() -> None:
    provider = make_provider()

    job = provider._normalize_job(make_jobicy_item())

    assert job is not None
    assert job.title == "Junior Software Engineer"
    assert job.company == "Bloom Labs"
    assert job.location == "Remote (U.S.)"
    assert job.source == "jobicy"
    assert job.url == "https://jobicy.com/jobs/123"
    assert job.salary_min == 80000
    assert job.salary_max == 100000
    assert job.salary_currency == "USD"
    assert job.employment_type == "Full-time"
    assert job.experience_level in {"entry-level", "junior", "mid-level", "unknown"}
    assert isinstance(job.required_skills, list)


def test_normalize_job_filters_senior_titles() -> None:
    provider = make_provider()

    item = make_jobicy_item(title="Senior Staff Engineer")

    job = provider._normalize_job(item)

    assert job is None


def test_normalize_job_filters_missing_required_fields() -> None:
    provider = make_provider()

    item = make_jobicy_item(url="")

    job = provider._normalize_job(item)

    assert job is None


@pytest.mark.asyncio
async def test_fetch_jobs_returns_normalized_jobs(
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