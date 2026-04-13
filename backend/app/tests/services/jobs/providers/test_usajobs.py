from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.services.jobs.providers.usajobs import USAJOBSProvider


def make_provider(**overrides: Any) -> USAJOBSProvider:
    params = {
        "api_key": "test-api-key",
        "user_agent": "test-user-agent@example.com",
        "timeout_seconds": 6.0,
        "max_jobs": 10,
        "results_per_page": 5,
        "job_category_code": "2210",
        "position_offer_type_code": None,
    }
    params.update(overrides)
    return USAJOBSProvider(**params)


def make_usajobs_item(
    *,
    title: str = "IT Specialist",
    url: str = "https://www.usajobs.gov/job/123",
    position_id: str = "123",
    company: str = "Department of Example",
    city: str = "Atlanta",
    region: str = "GA",
    location_display: str = "Atlanta, GA",
    qualification_summary: str = (
        "This is an entry-level role for recent graduates with strong IT interest."
    ),
    job_summary: str = (
        "Support information systems, documentation, and user support tasks."
    ),
    major_duties: list[str] | None = None,
    education: str = "Bachelor's degree in a related field preferred.",
    evaluations: str = "You will be evaluated based on your resume and responses.",
    how_to_apply: str = "Apply online.",
    minimum_range: str = "55000",
    maximum_range: str = "75000",
    schedule_name: str = "Full-time",
    categories: list[dict[str, str]] | None = None,
    hiring_paths: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if major_duties is None:
        major_duties = [
            "Provide technical support for internal systems.",
            "Document recurring issues and resolutions.",
        ]

    if categories is None:
        categories = [{"Name": "Information Technology Management"}]

    if hiring_paths is None:
        hiring_paths = [{"Name": "Recent graduates"}]

    return {
        "MatchedObjectDescriptor": {
            "PositionTitle": title,
            "PositionURI": url,
            "PositionID": position_id,
            "OrganizationName": company,
            "PositionLocation": [
                {
                    "CityName": city,
                    "CountrySubDivision": region,
                    "CountryCode": "US",
                }
            ],
            "PositionLocationDisplay": location_display,
            "QualificationSummary": qualification_summary,
            "JobCategory": categories,
            "PositionSchedule": [{"Name": schedule_name}],
            "PositionRemuneration": [
                {
                    "MinimumRange": minimum_range,
                    "MaximumRange": maximum_range,
                }
            ],
            "UserArea": {
                "Details": {
                    "JobSummary": job_summary,
                    "MajorDuties": major_duties,
                    "Education": education,
                    "Evaluations": evaluations,
                    "HowToApply": how_to_apply,
                    "HiringPath": hiring_paths,
                }
            },
        }
    }


def make_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "SearchResult": {
            "SearchResultItems": items,
        }
    }


def test_normalize_job_builds_expected_normalized_job() -> None:
    provider = make_provider()

    item = make_usajobs_item()
    job = provider._normalize_job(item)

    assert job is not None
    assert job.title == "IT Specialist"
    assert job.company == "Department of Example"
    assert job.location == "Atlanta, GA"
    assert job.source == "usajobs"
    assert job.url == "https://www.usajobs.gov/job/123"
    assert job.employment_type == "Full-time"
    assert job.salary_min == 55000
    assert job.salary_max == 75000
    assert job.salary_currency == "USD"
    assert isinstance(job.summary, str) and job.summary
    assert isinstance(job.description, str) and "Job Summary:" in job.description
    assert isinstance(job.required_skills, list)
    assert isinstance(job.qualifications, list)
    assert isinstance(job.responsibilities, list)
    assert job.id


def test_normalize_job_filters_obviously_senior_title() -> None:
    provider = make_provider()

    item = make_usajobs_item(title="Senior IT Architect")
    job = provider._normalize_job(item)

    assert job is None


def test_normalize_job_filters_titles_not_kept_for_earlybloom() -> None:
    provider = make_provider()

    item = make_usajobs_item(title="Chief of Staff")
    job = provider._normalize_job(item)

    assert job is None


def test_extract_location_uses_position_location_objects() -> None:
    provider = make_provider()

    descriptor = {
        "PositionLocation": [
            {"CityName": "Atlanta", "CountrySubDivision": "GA"},
            {"CityName": "Atlanta", "CountrySubDivision": "GA"},
            {"CityName": "Chicago", "CountrySubDivision": "IL"},
        ],
        "PositionLocationDisplay": "Fallback display",
    }

    location = provider._extract_location(descriptor)

    assert location == "Atlanta, GA, Chicago, IL"


def test_extract_location_falls_back_to_display() -> None:
    provider = make_provider()

    descriptor = {
        "PositionLocation": [],
        "PositionLocationDisplay": "Remote within the United States",
    }

    location = provider._extract_location(descriptor)

    assert location == "Remote within the United States"


def test_build_description_combines_expected_sections() -> None:
    provider = make_provider()

    descriptor = make_usajobs_item()["MatchedObjectDescriptor"]
    description = provider._build_description(descriptor)

    assert "Job Summary:" in description
    assert "Qualifications:" in description
    assert "Responsibilities:" in description
    assert "Education:" in description
    assert "How You Will Be Evaluated:" in description
    assert "How To Apply:" in description


def test_render_section_body_handles_string_list_and_dict() -> None:
    provider = make_provider()

    assert provider._render_section_body("  Hello   world  ") == "Hello world"

    rendered_list = provider._render_section_body(["First item", "Second item"])
    assert "- First item" in rendered_list
    assert "- Second item" in rendered_list

    rendered_dict = provider._render_section_body({"a": "Alpha", "b": "Beta"})
    assert "Alpha" in rendered_dict
    assert "Beta" in rendered_dict


def test_extract_salary_min_and_max_handle_invalid_values() -> None:
    provider = make_provider()

    descriptor = {
        "PositionRemuneration": [
            {
                "MinimumRange": "not-a-number",
                "MaximumRange": None,
            }
        ]
    }

    assert provider._extract_salary_min(descriptor) is None
    assert provider._extract_salary_max(descriptor) is None


def test_extract_employment_type_from_schedule() -> None:
    provider = make_provider()

    descriptor = {
        "PositionSchedule": [{"Name": "Part-time"}],
    }

    assert provider._extract_employment_type(descriptor) == "Part-time"


def test_extract_tags_dedupes_categories_and_hiring_paths() -> None:
    provider = make_provider()

    descriptor = {
        "JobCategory": [
            {"Name": "Information Technology Management"},
            {"Name": "Information Technology Management"},
            {"Name": "Cybersecurity"},
        ],
        "UserArea": {
            "Details": {
                "HiringPath": [
                    {"Name": "Recent graduates"},
                    {"Name": "Recent graduates"},
                    {"Name": "Students"},
                ]
            }
        },
    }

    tags = provider._extract_tags(descriptor)

    assert tags == [
        "Information Technology Management",
        "Cybersecurity",
        "Recent graduates",
        "Students",
    ]


def test_extract_section_bullets_reads_named_section() -> None:
    provider = make_provider()

    text = (
        "Job Summary:\n"
        "Support the team.\n\n"
        "Responsibilities:\n"
        "- First duty\n"
        "- Second duty\n\n"
        "Education:\n"
        "Bachelor's degree preferred."
    )

    bullets = provider._extract_section_bullets(
        text,
        section_names=("responsibilities",),
    )

    assert bullets == ["First duty", "Second duty"]


def test_extract_section_bullets_returns_empty_when_section_missing() -> None:
    provider = make_provider()

    bullets = provider._extract_section_bullets(
        "Job Summary:\nNothing else here.",
        section_names=("responsibilities",),
    )

    assert bullets == []


def test_normalize_experience_level_maps_supported_values() -> None:
    provider = make_provider()

    assert provider._normalize_experience_level("entry") == "entry-level"
    assert provider._normalize_experience_level("entry-level") == "entry-level"
    assert provider._normalize_experience_level("junior") == "junior"
    assert provider._normalize_experience_level("mid") == "mid-level"
    assert provider._normalize_experience_level("mid-level") == "mid-level"
    assert provider._normalize_experience_level("senior") == "senior"
    assert provider._normalize_experience_level("staff") == "unknown"


@pytest.mark.asyncio
async def test_fetch_jobs_sends_expected_headers_and_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return make_payload([make_usajobs_item()])

    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            headers: dict[str, str],
            params: dict[str, Any],
        ) -> MockResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(
        timeout_seconds=7.5,
        results_per_page=5,
        max_jobs=5,
        job_category_code="2210",
        position_offer_type_code="15317",
    )

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert captured["timeout"] == 7.5
    assert captured["url"] == provider.base_url
    assert captured["headers"]["Host"] == "data.usajobs.gov"
    assert captured["headers"]["User-Agent"] == "test-user-agent@example.com"
    assert captured["headers"]["Authorization-Key"] == "test-api-key"
    assert captured["params"]["ResultsPerPage"] == 5
    assert captured["params"]["Page"] == 1
    assert captured["params"]["JobCategoryCode"] == "2210"
    assert captured["params"]["PositionOfferTypeCode"] == "15317"


@pytest.mark.asyncio
async def test_fetch_jobs_stops_when_page_returns_no_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    class MockResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

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
            headers: dict[str, str],
            params: dict[str, Any],
        ) -> MockResponse:
            page = params["Page"]
            calls.append(page)

            if page == 1:
                return MockResponse(
                    make_payload([make_usajobs_item(position_id="page-1")])
                )

            return MockResponse(make_payload([]))

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(results_per_page=1, max_jobs=3)

    jobs = await provider.fetch_jobs()

    assert calls == [1, 2]
    assert len(jobs) == 1
    assert jobs[0].title == "IT Specialist"


@pytest.mark.asyncio
async def test_fetch_jobs_respects_max_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return make_payload(
                [
                    make_usajobs_item(position_id="1", url="https://example.com/1"),
                    make_usajobs_item(position_id="2", url="https://example.com/2"),
                    make_usajobs_item(position_id="3", url="https://example.com/3"),
                ]
            )

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
            headers: dict[str, str],
            params: dict[str, Any],
        ) -> MockResponse:
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider(max_jobs=2, results_per_page=10)

    jobs = await provider.fetch_jobs()

    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_after_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            headers: dict[str, str],
            params: dict[str, Any],
        ):
            raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    provider = make_provider()

    jobs = await provider.fetch_jobs()

    assert jobs == []