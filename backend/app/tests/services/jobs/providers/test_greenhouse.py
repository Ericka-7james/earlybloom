from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.core.config import get_settings
from app.services.jobs.providers.greenhouse import GreenhouseJobBoardProvider


def make_provider(**overrides: Any) -> GreenhouseJobBoardProvider:
    params = {
        "board_tokens": ["stripe"],
        "timeout_seconds": 6.0,
        "max_jobs_per_board": 10,
        "include_departments": None,
        "exclude_departments": None,
        "include_offices": None,
        "exclude_offices": None,
    }
    params.update(overrides)
    return GreenhouseJobBoardProvider(**params)


def make_greenhouse_job(
    *,
    job_id: int = 123,
    title: str = "Software Engineer I",
    absolute_url: str = "https://example.com/job/123",
    content: str = (
        "<p>Build APIs and UI.</p>"
        "<p>Responsibilities:</p><ul><li>Build features</li><li>Write tests</li></ul>"
        "<p>Qualifications:</p><ul><li>Python</li><li>React</li></ul>"
        "<p>Nice to have:</p><ul><li>AWS</li></ul>"
        "<p>Salary range: $85k-$110k</p>"
    ),
    location_name: str = "United States",
    metadata: list[dict[str, Any]] | None = None,
    offices: list[dict[str, Any]] | None = None,
    departments: list[dict[str, Any]] | None = None,
    updated_at: str = "2026-04-01T12:00:00Z",
    requisition_id: str = "REQ-123",
    internal_job_id: int = 456,
) -> dict[str, Any]:
    if metadata is None:
        metadata = [
            {"name": "Company", "value": "Stripe"},
            {"name": "Employment Type", "value": "Full-time"},
            {"name": "Salary Range", "value": "$85k-$110k"},
        ]

    if offices is None:
        offices = [{"name": "Remote", "location": "United States"}]

    if departments is None:
        departments = [{"name": "Engineering", "parent_id": 1}]

    return {
        "id": job_id,
        "title": title,
        "absolute_url": absolute_url,
        "content": content,
        "location": {"name": location_name},
        "metadata": metadata,
        "offices": offices,
        "departments": departments,
        "updated_at": updated_at,
        "requisition_id": requisition_id,
        "internal_job_id": internal_job_id,
    }


def test_normalize_job_returns_normalized_job() -> None:
    provider = make_provider()

    job = provider._normalize_job(make_greenhouse_job(), board_token="stripe")

    assert job is not None
    assert job.title == "Software Engineer I"
    assert job.company == "Stripe"
    assert job.location == "United States"
    assert job.source == "greenhouse"
    assert job.url == "https://example.com/job/123"
    assert job.employment_type == "Full-time"
    assert job.salary_min == 85000
    assert job.salary_max == 110000
    assert job.salary_currency == "USD"
    assert isinstance(job.required_skills, list)
    assert isinstance(job.qualifications, list)
    assert isinstance(job.preferred_skills, list)
    assert job.experience_level in {"entry-level", "junior", "mid-level", "unknown", "senior"}


def test_normalize_job_filters_senior_titles() -> None:
    provider = make_provider()

    job = provider._normalize_job(
        make_greenhouse_job(title="Senior Staff Engineer"),
        board_token="stripe",
    )

    assert job is None


def test_normalize_job_filters_titles_not_kept_for_earlybloom() -> None:
    provider = make_provider()

    job = provider._normalize_job(
        make_greenhouse_job(title="Chief Technology Officer"),
        board_token="stripe",
    )

    assert job is None


def test_normalize_job_filters_missing_required_fields() -> None:
    provider = make_provider()

    missing_title = provider._normalize_job(
        make_greenhouse_job(title=""),
        board_token="stripe",
    )
    missing_url = provider._normalize_job(
        make_greenhouse_job(absolute_url=""),
        board_token="stripe",
    )

    assert missing_title is None
    assert missing_url is None


def test_extract_company_name_prefers_metadata() -> None:
    provider = make_provider()

    item = make_greenhouse_job(
        metadata=[{"name": "Company", "value": "Figma"}],
        absolute_url="https://boards.greenhouse.io/figma/jobs/123",
    )

    company = provider._extract_company_name(item, board_token="stripe")

    assert company == "Figma"


def test_extract_company_name_falls_back_to_url_token() -> None:
    provider = make_provider()

    item = make_greenhouse_job(
        metadata=[],
        absolute_url="https://boards.greenhouse.io/figma/jobs/123",
    )

    company = provider._extract_company_name(item, board_token="stripe")

    assert company == "Figma"


def test_extract_company_name_falls_back_to_board_token() -> None:
    provider = make_provider()

    item = make_greenhouse_job(
        metadata=[],
        absolute_url="",
    )

    company = provider._extract_company_name(item, board_token="acme-labs")

    assert company == "Acme Labs"


def test_passes_board_filters_include_office() -> None:
    provider = make_provider(include_offices=["united states"])

    assert provider._passes_board_filters(
        make_greenhouse_job(location_name="United States")
    )


def test_passes_board_filters_exclude_office() -> None:
    provider = make_provider(exclude_offices=["canada"])

    assert not provider._passes_board_filters(
        make_greenhouse_job(location_name="Canada")
    )


def test_passes_board_filters_include_department() -> None:
    provider = make_provider(include_departments=["engineering"])

    assert provider._passes_board_filters(
        make_greenhouse_job(departments=[{"name": "Engineering", "parent_id": 1}])
    )


def test_passes_board_filters_exclude_department() -> None:
    provider = make_provider(exclude_departments=["marketing"])

    assert not provider._passes_board_filters(
        make_greenhouse_job(departments=[{"name": "Marketing", "parent_id": 1}])
    )


def test_extract_salary_fields_parses_range() -> None:
    provider = make_provider()

    salary_min, salary_max, currency = provider._extract_salary_fields(
        metadata=[{"name": "Salary Range", "value": "$90k-$120k"}],
        description="",
    )

    assert salary_min == 90000
    assert salary_max == 120000
    assert currency == "USD"


def test_extract_salary_fields_returns_none_when_missing() -> None:
    provider = make_provider()

    salary_min, salary_max, currency = provider._extract_salary_fields(
        metadata=[],
        description="No compensation listed here.",
    )

    assert salary_min is None
    assert salary_max is None
    assert currency is None


def test_extract_section_bullets_returns_expected_items() -> None:
    provider = make_provider()

    text = (
        "Responsibilities:\n"
        "- Build APIs\n"
        "- Write tests\n"
        "Qualifications:\n"
        "- Python\n"
    )

    bullets = provider._extract_section_bullets(
        text,
        section_names=("responsibilities",),
    )

    assert bullets
    assert "Build APIs" in bullets[0]


def test_find_metadata_value_matches_case_insensitively() -> None:
    provider = make_provider()

    metadata = [{"name": "Employment Type", "value": "Full-time"}]

    assert provider._find_metadata_value(metadata, "employment type") == "Full-time"


def test_metadata_values_dedupes_entries() -> None:
    provider = make_provider()

    metadata = [
        {"name": "Company", "value": "Stripe"},
        {"name": "Company", "value": "Stripe"},
        {"name": "Employment Type", "value": "Full-time"},
    ]

    values = provider._metadata_values(metadata)

    assert values == ["Company: Stripe", "Employment Type: Full-time"]


def test_extract_office_names_dedupes_location_sources() -> None:
    provider = make_provider()

    item = make_greenhouse_job(
        location_name="United States",
        offices=[
            {"name": "Remote", "location": "United States"},
            {"name": "Remote", "location": "United States"},
        ],
    )

    names = provider._extract_office_names(item)

    assert "Remote" in names
    assert "United States" in names
    assert len(names) == 2


def test_humanize_token_formats_tokens() -> None:
    assert GreenhouseJobBoardProvider._humanize_token("acme-labs_inc") == "Acme Labs Inc"


def test_split_csv_handles_empty_and_values() -> None:
    assert GreenhouseJobBoardProvider._split_csv(None) == []
    assert GreenhouseJobBoardProvider._split_csv("") == []
    assert GreenhouseJobBoardProvider._split_csv("stripe, figma , acme") == [
        "stripe",
        "figma",
        "acme",
    ]


def test_normalize_filters_and_matches_any() -> None:
    filters = GreenhouseJobBoardProvider._normalize_filters([" Engineering ", "Remote"])

    assert filters == ["engineering", "remote"]
    assert GreenhouseJobBoardProvider._matches_any(
        ["United States Remote", "Atlanta"],
        filters,
    )
    assert not GreenhouseJobBoardProvider._matches_any(
        ["Marketing", "Toronto"],
        filters,
    )


@pytest.mark.asyncio
async def test_fetch_jobs_success(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = {
        "jobs": [make_greenhouse_job()],
        "meta": {"total": 1},
    }

    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return mock_response

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]) -> MockResponse:
            assert params == {"content": "true"}
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(board_tokens=["stripe"])

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer I"
    assert jobs[0].company == "Stripe"


@pytest.mark.asyncio
async def test_fetch_jobs_handles_404(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]):
            request = httpx.Request("GET", url)
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("404", request=request, response=response)

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(board_tokens=["badtoken"])

    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_dedupes_across_boards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = make_greenhouse_job(
        job_id=123,
        absolute_url="https://example.com/job/shared",
    )

    class MockResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self.payload

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]) -> MockResponse:
            if "stripe" in url:
                return MockResponse({"jobs": [job], "meta": {"total": 1}})
            return MockResponse({"jobs": [job], "meta": {"total": 1}})

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(board_tokens=["stripe", "figma"])

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1


@pytest.mark.asyncio
async def test_fetch_jobs_respects_max_jobs_per_board(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "jobs": [
                    make_greenhouse_job(job_id=1, absolute_url="https://example.com/job/1"),
                    make_greenhouse_job(job_id=2, absolute_url="https://example.com/job/2"),
                    make_greenhouse_job(job_id=3, absolute_url="https://example.com/job/3"),
                ],
                "meta": {"total": 3},
            }

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]) -> MockResponse:
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(board_tokens=["stripe"], max_jobs_per_board=2)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_fetch_jobs_skips_invalid_payload_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"jobs": "not-a-list"}

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, params: dict[str, Any]) -> MockResponse:
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(board_tokens=["stripe"])

    jobs = await provider.fetch_jobs()

    assert jobs == []


def test_from_env_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_ENABLED", "false")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", "stripe")

    get_settings.cache_clear()
    provider = GreenhouseJobBoardProvider.from_env()

    assert provider is None


def test_from_env_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_ENABLED", "true")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS", "stripe,figma")
    monkeypatch.setenv("JOB_PROVIDER_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("JOB_PROVIDER_MAX_JOBS_PER_SOURCE", "25")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_INCLUDE_DEPARTMENTS", "engineering,data")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_EXCLUDE_DEPARTMENTS", "marketing")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_INCLUDE_OFFICES", "united states,remote")
    monkeypatch.setenv("JOB_PROVIDER_GREENHOUSE_EXCLUDE_OFFICES", "canada")

    get_settings.cache_clear()
    provider = GreenhouseJobBoardProvider.from_env()

    assert provider is not None
    assert provider.board_tokens == ["stripe", "figma"]
    assert provider.timeout_seconds == 7.0
    assert provider.max_jobs_per_board == 25
    assert provider.include_departments == ["engineering", "data"]
    assert provider.exclude_departments == ["marketing"]
    assert provider.include_offices == ["united states", "remote"]
    assert provider.exclude_offices == ["canada"]