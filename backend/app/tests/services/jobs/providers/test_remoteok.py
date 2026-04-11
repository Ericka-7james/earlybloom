from __future__ import annotations

import httpx
import pytest

from app.services.jobs.providers.remoteok import RemoteOKProvider


class MockResponse:
    def __init__(self, payload, should_raise: bool = False) -> None:
        self._payload = payload
        self._should_raise = should_raise

    def raise_for_status(self) -> None:
        if self._should_raise:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://remoteok.com/api"),
                response=httpx.Response(500),
            )

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_fetch_jobs_returns_jobs_and_skips_metadata_rows(monkeypatch) -> None:
    payload = [
        {"legal": "metadata row"},
        {
            "id": 123,
            "position": "Frontend Engineer",
            "company": "Bloom Labs",
            "location": "Remote",
            "url": "https://remoteok.com/remote-jobs/123",
            "salary_min": 80000,
            "salary_max": 100000,
            "description": "Responsibilities:\n- Build UI\n\nRequirements:\n- React",
            "tags": ["React", "JavaScript"],
        },
        {
            "id": 456,
            "position": "Backend Engineer",
            "company": "Acme",
            "location": "Anywhere",
            "url": "https://remoteok.com/remote-jobs/456",
            "salary_min": None,
            "salary_max": None,
            "description": "Build APIs and services.",
            "tags": ["Python"],
        },
    ]

    async def mock_get(self, url, headers=None):
        assert url == "https://remoteok.com/api"
        assert headers == {"User-Agent": "EarlyBloom/1.0"}
        return MockResponse(payload)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = RemoteOKProvider(timeout_seconds=6.0, max_jobs=100)
    jobs = await provider.fetch_jobs()

    assert len(jobs) == 2
    assert jobs[0].title == "Frontend Engineer"
    assert jobs[0].company == "Bloom Labs"
    assert jobs[0].source == "remoteok"
    assert jobs[0].remote is True
    assert jobs[0].remote_type == "remote"

    assert jobs[1].title == "Backend Engineer"
    assert jobs[1].company == "Acme"
    assert jobs[1].source == "remoteok"


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_when_payload_is_not_a_list(monkeypatch) -> None:
    async def mock_get(self, url, headers=None):
        return MockResponse({"unexpected": "object"})

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = RemoteOKProvider()
    jobs = await provider.fetch_jobs()

    assert jobs == []


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_list_on_http_error(monkeypatch) -> None:
    async def mock_get(self, url, headers=None):
        raise httpx.ConnectError(
            "boom",
            request=httpx.Request("GET", "https://remoteok.com/api"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = RemoteOKProvider()
    jobs = await provider.fetch_jobs()

    assert jobs == []


def test_extract_items_skips_metadata_and_non_dict_rows() -> None:
    provider = RemoteOKProvider()

    payload = [
        {"legal": "metadata"},
        "not-a-dict",
        {
            "id": 1,
            "position": "Frontend Engineer",
            "company": "Bloom Labs",
            "url": "https://remoteok.com/remote-jobs/1",
        },
        {
            "id": 2,
            "position": "Backend Engineer",
            "company": "Acme",
            "url": "https://remoteok.com/remote-jobs/2",
        },
    ]

    items = provider._extract_items(payload)

    assert len(items) == 2
    assert items[0]["id"] == 1
    assert items[1]["id"] == 2


def test_normalize_job_returns_expected_shape() -> None:
    provider = RemoteOKProvider()

    raw_job = {
        "id": 999,
        "position": "Frontend Engineer",
        "company": "EarlyBloom",
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/999",
        "salary_min": 90000,
        "salary_max": 130000,
        "employment_type": "Full-time",
        "description": (
            "Responsibilities:\n"
            "- Build product features across frontend and backend.\n"
            "- Collaborate with design.\n\n"
            "Requirements:\n"
            "- React\n"
            "- Python"
        ),
        "tags": ["React", "Python", "SQL"],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is not None
    assert normalized.source == "remoteok"
    assert normalized.title == "Frontend Engineer"
    assert normalized.company == "EarlyBloom"
    assert normalized.location == "Worldwide"
    assert normalized.remote is True
    assert normalized.remote_type == "remote"
    assert normalized.url == "https://remoteok.com/remote-jobs/999"
    assert normalized.salary_min == 90000
    assert normalized.salary_max == 130000
    assert normalized.salary_currency == "USD"
    assert normalized.employment_type == "Full-time"
    assert normalized.experience_level in {
        "entry-level",
        "junior",
        "mid-level",
        "senior",
        "unknown",
    }
    assert normalized.description
    assert isinstance(normalized.required_skills, list)
    assert isinstance(normalized.preferred_skills, list)
    assert "React" in normalized.preferred_skills


def test_normalize_job_handles_missing_or_invalid_salary() -> None:
    provider = RemoteOKProvider()

    raw_job = {
        "id": 1000,
        "position": "Software Engineer",
        "company": "No Salary Inc",
        "location": "Remote",
        "url": "https://remoteok.com/remote-jobs/1000",
        "salary_min": "not-a-number",
        "salary_max": None,
        "description": "No salary provided.",
        "tags": [],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is not None
    assert normalized.salary_min is None
    assert normalized.salary_max is None
    assert normalized.salary_currency is None
    assert normalized.remote_type == "remote"


def test_normalize_job_returns_none_for_missing_required_fields() -> None:
    provider = RemoteOKProvider()

    raw_job = {
        "id": 2000,
        "position": "Frontend Engineer",
        "company": "Bloom Labs",
        "location": "Remote",
        # missing url
        "description": "Build UI.",
        "tags": ["React"],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is None


def test_normalize_job_filters_obviously_senior_titles() -> None:
    provider = RemoteOKProvider()

    raw_job = {
        "id": 3000,
        "position": "Senior Frontend Engineer",
        "company": "Bloom Labs",
        "location": "Remote",
        "url": "https://remoteok.com/remote-jobs/3000",
        "description": "Lead architecture and mentor the team.",
        "tags": ["React"],
    }

    normalized = provider._normalize_job(raw_job)

    assert normalized is None


def test_extract_employment_type_uses_first_supported_field() -> None:
    provider = RemoteOKProvider()

    item = {
        "type": "Contract",
        "job_type": "Full-time",
    }

    assert provider._extract_employment_type(item) == "Contract"


def test_extract_responsibilities_and_qualifications_from_named_sections() -> None:
    provider = RemoteOKProvider()

    text = (
        "Responsibilities:\n"
        "- Build APIs\n"
        "- Work with product\n\n"
        "Requirements:\n"
        "- Python\n"
        "- FastAPI"
    )

    responsibilities = provider._extract_responsibilities(text)
    qualifications = provider._extract_qualifications(text)

    assert responsibilities
    assert qualifications
    assert any("Build APIs" in item for item in responsibilities)
    assert any("Python" in item for item in qualifications)


def test_clean_remoteok_text_normalizes_common_encoding_junk() -> None:
    provider = RemoteOKProvider()

    cleaned = provider._clean_remoteok_text("RemoteÂ â role&nbsp;only")

    assert cleaned == "Remote ' role only"