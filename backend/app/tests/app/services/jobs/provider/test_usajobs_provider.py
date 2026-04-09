from __future__ import annotations

import pytest

from app.services.jobs.providers.usajobs import USAJOBSProvider


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class DummyAsyncClient:
    def __init__(self, responses: list[dict], *args, **kwargs):
        self._responses = responses
        self.calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None, params=None):
        self.calls.append(
            {
                "url": url,
                "headers": headers or {},
                "params": params or {},
            }
        )
        if not self._responses:
            return DummyResponse({"SearchResult": {"SearchResultItems": []}})
        return DummyResponse(self._responses.pop(0))


def make_provider(**overrides) -> USAJOBSProvider:
    return USAJOBSProvider(
        api_key=overrides.pop("api_key", "test-api-key"),
        user_agent=overrides.pop("user_agent", "test@example.com"),
        timeout_seconds=overrides.pop("timeout_seconds", 1.0),
        max_jobs=overrides.pop("max_jobs", 10),
        results_per_page=overrides.pop("results_per_page", 5),
        job_category_code=overrides.pop("job_category_code", "2210"),
        position_offer_type_code=overrides.pop("position_offer_type_code", None),
        **overrides,
    )


def sample_usajobs_item(
    *,
    title: str = "IT Specialist (SYSANALYSIS)",
    location_city: str = "Atlanta",
    location_region: str = "GA",
    job_id: str = "12345",
    url: str = "https://www.usajobs.gov/job/12345",
) -> dict:
    return {
        "MatchedObjectDescriptor": {
            "PositionTitle": title,
            "PositionURI": url,
            "PositionID": job_id,
            "OrganizationName": "Department of Example",
            "PositionLocation": [
                {
                    "CityName": location_city,
                    "CountrySubDivision": location_region,
                }
            ],
            "PositionLocationDisplay": f"{location_city}, {location_region}",
            "QualificationSummary": "Experience with systems analysis and troubleshooting.",
            "PositionSchedule": [{"Name": "Full-time"}],
            "PositionRemuneration": [
                {
                    "MinimumRange": "70000",
                    "MaximumRange": "90000",
                }
            ],
            "JobCategory": [{"Name": "Information Technology Management"}],
            "UserArea": {
                "Details": {
                    "JobSummary": "Support mission systems used by federal teams.",
                    "MajorDuties": [
                        "Analyze system requirements.",
                        "Support production systems.",
                    ],
                    "Education": "Bachelor's degree preferred.",
                    "Evaluations": "You will be evaluated based on your experience.",
                    "HowToApply": "Apply online.",
                    "HiringPath": [{"Name": "Public"}],
                }
            },
        }
    }


@pytest.mark.asyncio
async def test_fetch_jobs_builds_headers_and_params(monkeypatch):
    payload = {
        "SearchResult": {
            "SearchResultItems": [sample_usajobs_item()],
        }
    }
    client = DummyAsyncClient([payload])

    monkeypatch.setattr(
        "app.services.jobs.providers.usajobs.httpx.AsyncClient",
        lambda *args, **kwargs: client,
    )

    provider = make_provider(max_jobs=5, results_per_page=5, job_category_code="2210")
    jobs = await provider.fetch_jobs()

    assert len(jobs) == 1
    assert client.calls[0]["headers"]["Host"] == "data.usajobs.gov"
    assert client.calls[0]["headers"]["User-Agent"] == "test@example.com"
    assert client.calls[0]["headers"]["Authorization-Key"] == "test-api-key"
    assert client.calls[0]["params"]["ResultsPerPage"] == 5
    assert client.calls[0]["params"]["Page"] == 1
    assert client.calls[0]["params"]["JobCategoryCode"] == "2210"


@pytest.mark.asyncio
async def test_fetch_jobs_respects_max_jobs(monkeypatch):
    payload = {
        "SearchResult": {
            "SearchResultItems": [
                sample_usajobs_item(job_id="1", url="https://www.usajobs.gov/job/1"),
                sample_usajobs_item(job_id="2", url="https://www.usajobs.gov/job/2"),
                sample_usajobs_item(job_id="3", url="https://www.usajobs.gov/job/3"),
            ],
        }
    }
    client = DummyAsyncClient([payload])

    monkeypatch.setattr(
        "app.services.jobs.providers.usajobs.httpx.AsyncClient",
        lambda *args, **kwargs: client,
    )

    provider = make_provider(max_jobs=2, results_per_page=10)
    jobs = await provider.fetch_jobs()

    assert len(jobs) == 2


def test_normalize_job_maps_core_fields():
    provider = make_provider()
    item = sample_usajobs_item()

    job = provider._normalize_job(item)

    assert job is not None
    assert job.title == "IT Specialist (SYSANALYSIS)"
    assert job.company == "Department of Example"
    assert job.location == "Atlanta, GA"
    assert job.url == "https://www.usajobs.gov/job/12345"
    assert job.source == "usajobs"
    assert job.employment_type == "Full-time"
    assert job.salary_min == 70000
    assert job.salary_max == 90000
    assert job.salary_currency == "USD"


def test_normalize_job_extracts_sections():
    provider = make_provider()
    item = sample_usajobs_item()

    job = provider._normalize_job(item)

    assert job is not None
    assert len(job.responsibilities) > 0
    assert len(job.qualifications) > 0
    assert len(job.preferred_skills) > 0


def test_normalize_job_drops_obviously_senior_title():
    provider = make_provider()
    item = sample_usajobs_item(title="Senior IT Specialist")

    job = provider._normalize_job(item)

    assert job is None


def test_extract_location_uses_structured_locations():
    provider = make_provider()
    descriptor = sample_usajobs_item()["MatchedObjectDescriptor"]

    location = provider._extract_location(descriptor)

    assert location == "Atlanta, GA"


def test_extract_location_falls_back_to_display():
    provider = make_provider()
    descriptor = sample_usajobs_item()["MatchedObjectDescriptor"]
    descriptor["PositionLocation"] = []
    descriptor["PositionLocationDisplay"] = "Washington, DC"

    location = provider._extract_location(descriptor)

    assert location == "Washington, DC"


def test_build_description_contains_expected_sections():
    provider = make_provider()
    descriptor = sample_usajobs_item()["MatchedObjectDescriptor"]

    description = provider._build_description(descriptor)

    assert "Job Summary:" in description
    assert "Qualifications:" in description
    assert "Responsibilities:" in description
    assert "Education:" in description


def test_extract_salary_fields_handle_missing_values():
    provider = make_provider()
    descriptor = sample_usajobs_item()["MatchedObjectDescriptor"]
    descriptor["PositionRemuneration"] = []

    assert provider._extract_salary_min(descriptor) is None
    assert provider._extract_salary_max(descriptor) is None


def test_from_env_returns_none_when_disabled(monkeypatch):
    class DummySettings:
        JOB_PROVIDER_USAJOBS_ENABLED = False
        USAJOBS_API_KEY = "x"
        USAJOBS_USER_AGENT = "test@example.com"

    monkeypatch.setattr(
        "app.services.jobs.providers.usajobs.get_settings",
        lambda: DummySettings(),
    )

    provider = USAJOBSProvider.from_env()

    assert provider is None


def test_from_env_returns_none_when_missing_credentials(monkeypatch):
    class DummySettings:
        JOB_PROVIDER_USAJOBS_ENABLED = True
        USAJOBS_API_KEY = ""
        USAJOBS_USER_AGENT = ""
        JOB_PROVIDER_TIMEOUT_SECONDS = 6.0
        JOB_PROVIDER_MAX_JOBS_PER_SOURCE = 100
        USAJOBS_RESULTS_PER_PAGE = 50
        USAJOBS_JOB_CATEGORY_CODE = "2210"
        USAJOBS_POSITION_OFFER_TYPE_CODE = None

    monkeypatch.setattr(
        "app.services.jobs.providers.usajobs.get_settings",
        lambda: DummySettings(),
    )

    provider = USAJOBSProvider.from_env()

    assert provider is None


def test_from_env_builds_provider_when_configured(monkeypatch):
    class DummySettings:
        JOB_PROVIDER_USAJOBS_ENABLED = True
        USAJOBS_API_KEY = "abc123"
        USAJOBS_USER_AGENT = "test@example.com"
        JOB_PROVIDER_TIMEOUT_SECONDS = 6.0
        JOB_PROVIDER_MAX_JOBS_PER_SOURCE = 100
        USAJOBS_RESULTS_PER_PAGE = 50
        USAJOBS_JOB_CATEGORY_CODE = "2210"
        USAJOBS_POSITION_OFFER_TYPE_CODE = None

    monkeypatch.setattr(
        "app.services.jobs.providers.usajobs.get_settings",
        lambda: DummySettings(),
    )

    provider = USAJOBSProvider.from_env()

    assert provider is not None
    assert provider.api_key == "abc123"
    assert provider.user_agent == "test@example.com"
    assert provider.job_category_code == "2210"