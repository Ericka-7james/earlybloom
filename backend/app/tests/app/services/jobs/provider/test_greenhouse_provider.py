from __future__ import annotations

import httpx
import pytest

from app.services.jobs.providers.greenhouse import GreenhouseJobBoardProvider


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
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append({"url": url, "params": params})
        return self.responses[url]


def sample_job():
    return {
        "id": 123,
        "internal_job_id": 999,
        "title": "Junior Software Engineer",
        "absolute_url": "https://boards.greenhouse.io/demo/jobs/123",
        "updated_at": "2026-04-15",
        "requisition_id": "REQ-1",
        "content": """
Responsibilities:
- Build APIs
- Ship features

Qualifications:
- Python
- SQL

Nice to Have:
- React
- AWS

Salary Range: $80k - $100k
""",
        "location": {"name": "Atlanta, GA"},
        "offices": [{"name": "Atlanta", "location": "Atlanta, GA"}],
        "departments": [{"name": "Engineering"}],
        "metadata": [
            {"name": "Employment Type", "value": "Full-Time"},
            {"name": "Company", "value": "Demo Corp"},
        ],
    }


def test_from_env_returns_none_when_disabled(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_GREENHOUSE_ENABLED = False

    monkeypatch.setattr(
        "app.services.jobs.providers.greenhouse.get_settings",
        lambda: FakeSettings(),
    )

    assert GreenhouseJobBoardProvider.from_env() is None


def test_from_env_returns_none_when_enabled_without_tokens(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_GREENHOUSE_ENABLED = True
        JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS = ""

    monkeypatch.setattr(
        "app.services.jobs.providers.greenhouse.get_settings",
        lambda: FakeSettings(),
    )

    assert GreenhouseJobBoardProvider.from_env() is None


def test_from_env_builds_provider(monkeypatch):
    class FakeSettings:
        JOB_PROVIDER_GREENHOUSE_ENABLED = True
        JOB_PROVIDER_GREENHOUSE_BOARD_TOKENS = "demo,second"
        JOB_PROVIDER_TIMEOUT_SECONDS = 8
        JOB_PROVIDER_MAX_JOBS_PER_SOURCE = 22
        JOB_PROVIDER_GREENHOUSE_INCLUDE_DEPARTMENTS = "engineering,data"
        JOB_PROVIDER_GREENHOUSE_EXCLUDE_DEPARTMENTS = "legal"
        JOB_PROVIDER_GREENHOUSE_INCLUDE_OFFICES = "atlanta,remote"
        JOB_PROVIDER_GREENHOUSE_EXCLUDE_OFFICES = "london"

    monkeypatch.setattr(
        "app.services.jobs.providers.greenhouse.get_settings",
        lambda: FakeSettings(),
    )

    provider = GreenhouseJobBoardProvider.from_env()

    assert provider is not None
    assert provider.board_tokens == ["demo", "second"]
    assert provider.timeout_seconds == 8
    assert provider.max_jobs_per_board == 22
    assert provider.include_departments == ["engineering", "data"]
    assert provider.exclude_departments == ["legal"]


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_when_no_tokens():
    provider = GreenhouseJobBoardProvider(board_tokens=[])

    result = await provider.fetch_jobs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_board_jobs_returns_empty_on_404():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])
    client = FakeAsyncClient(
        {
            f"{provider.base_url}/demo/jobs": FakeResponse({}, status_code=404),
        }
    )

    result = await provider._fetch_board_jobs(client, "demo")

    assert result == []


@pytest.mark.asyncio
async def test_fetch_board_jobs_normalizes_jobs():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])
    client = FakeAsyncClient(
        {
            f"{provider.base_url}/demo/jobs": FakeResponse(
                {"jobs": [sample_job()], "meta": {"total": 1}}
            ),
        }
    )

    result = await provider._fetch_board_jobs(client, "demo")

    assert len(result) == 1
    assert result[0].title == "Junior Software Engineer"
    assert result[0].company == "Demo Corp"


def test_normalize_job_returns_none_when_missing_required_fields():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])

    assert provider._normalize_job({}, board_token="demo") is None


def test_normalize_job_filters_senior_title():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])

    job = sample_job()
    job["title"] = "Senior Staff Engineer"

    assert provider._normalize_job(job, board_token="demo") is None


def test_normalize_job_maps_fields():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])

    result = provider._normalize_job(sample_job(), board_token="demo")

    assert result is not None
    assert result.title == "Junior Software Engineer"
    assert result.company == "Demo Corp"
    assert result.location == "Atlanta, GA"
    assert result.source == "greenhouse"
    assert result.remote in {True, False}
    assert result.employment_type == "Full-Time"
    assert result.salary_min == 80000
    assert result.salary_max == 100000
    assert result.salary_currency == "USD"


def test_passes_board_filters_include_office():
    provider = GreenhouseJobBoardProvider(
        board_tokens=["demo"],
        include_offices=["atlanta"],
    )

    assert provider._passes_board_filters(sample_job()) is True


def test_passes_board_filters_exclude_office():
    provider = GreenhouseJobBoardProvider(
        board_tokens=["demo"],
        exclude_offices=["atlanta"],
    )

    assert provider._passes_board_filters(sample_job()) is False


def test_passes_board_filters_include_department():
    provider = GreenhouseJobBoardProvider(
        board_tokens=["demo"],
        include_departments=["engineering"],
    )

    assert provider._passes_board_filters(sample_job()) is True


def test_extract_salary_fields_parses_k_ranges():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])

    salary_min, salary_max, currency = provider._extract_salary_fields(
        metadata=[],
        description="Compensation is $90k - $120k depending on level.",
    )

    assert salary_min == 90000
    assert salary_max == 120000
    assert currency == "USD"


def test_extract_company_name_falls_back_to_token():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])

    result = provider._extract_company_name({}, board_token="cool-startup")

    assert result == "Cool Startup"


def test_split_csv_and_humanize_helpers():
    assert GreenhouseJobBoardProvider._split_csv("a,b,c") == ["a", "b", "c"]
    assert GreenhouseJobBoardProvider._humanize_token("cool-startup_inc") == "Cool Startup Inc"


def test_dedupe_strings_preserves_order():
    result = GreenhouseJobBoardProvider._dedupe_strings(
        ["Atlanta", "atlanta", "Remote", "remote", ""]
    )

    assert result == ["Atlanta", "Remote"]


def test_safe_str_returns_trimmed_or_empty():
    provider = GreenhouseJobBoardProvider(board_tokens=["demo"])

    assert provider._safe_str(" hello ") == "hello"
    assert provider._safe_str(123) == "123"
    assert provider._safe_str(None) == ""