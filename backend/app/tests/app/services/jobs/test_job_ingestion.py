from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.jobs import NormalizedJob
from app.services.jobs.job_cache import clear_all_cache
from app.services.jobs.job_ingestion import (
    JobIngestionService,
    _build_public_job_id,
    _canonical_url,
    _coerce_to_normalized_job,
    _fetch_provider_jobs,
    _is_remote_job,
    _normalize_text,
    get_jobs,
)


@pytest.fixture(autouse=True)
def clear_job_cache():
    """Reset in-memory job cache between tests."""
    clear_all_cache()


@pytest.fixture
def fake_settings():
    return SimpleNamespace(
        JOB_DATA_MODE="live",
        JOBS_MAX_DB_SCAN_ROWS=300,
        JOBS_SHARED_CACHE_MIN_RESULTS=2,
        JOBS_DB_ONLY_READS=False,
        JOBS_QUERY_CACHE_TTL_SECONDS=300,
        JOBS_SHARED_CACHE_TTL_DAYS=7,
        JOBS_INGESTION_RUNNING_TTL_SECONDS=60,
        JOBS_PROVIDER_REFRESH_COOLDOWN_SECONDS=60,
    )


@pytest.fixture
def patch_settings(monkeypatch, fake_settings):
    monkeypatch.setattr(
        "app.services.jobs.job_ingestion.get_settings",
        lambda: fake_settings,
    )
    return fake_settings


class FakeRepository:
    def __init__(self):
        self.query_cache = {}
        self.query_rows_by_ids = {}
        self.active_rows = []
        self.ingestion_runs = []
        self.upserted_query_cache = []
        self.upserted_jobs = []
        self.running_ingestions = set()
        self.cooldown_ingestions = set()

    def build_query_cache_key(self, *, remote_only=False, levels=None, role_types=None):
        return f"remote={remote_only}|levels={levels or []}|roles={role_types or []}"

    def get_query_cache(self, cache_key: str):
        return self.query_cache.get(cache_key)

    def list_active_jobs_by_ids(self, job_ids: list[str]):
        return [
            self.query_rows_by_ids[job_id]
            for job_id in job_ids
            if job_id in self.query_rows_by_ids
        ]

    def cleanup_expired_jobs(self, grace_hours=48):
        return {"marked_inactive": 0, "deleted": 0}

    def list_active_jobs(self, limit=300):
        return self.active_rows[:limit]

    def row_to_normalized_job(self, row):
        return row

    def upsert_query_cache(
        self,
        *,
        cache_key: str,
        query_params: dict,
        job_ids: list[str],
        viewer_scope: str,
        ttl_seconds: int,
    ):
        self.upserted_query_cache.append(
            {
                "cache_key": cache_key,
                "query_params": query_params,
                "job_ids": job_ids,
                "viewer_scope": viewer_scope,
                "ttl_seconds": ttl_seconds,
            }
        )
        self.query_cache[cache_key] = {"job_ids": job_ids}

    def upsert_jobs(self, jobs, ttl_days: int, ingestion_run_id: str | None = None):
        self.upserted_jobs.append(
            {
                "jobs": jobs,
                "ttl_days": ttl_days,
                "ingestion_run_id": ingestion_run_id,
            }
        )

    def has_running_ingestion(self, *, provider: str, query_key: str, within_seconds: int):
        return (provider, query_key) in self.running_ingestions

    def has_recent_successful_run(
        self, *, provider: str, query_key: str, within_seconds: int
    ):
        return (provider, query_key) in self.cooldown_ingestions

    def create_ingestion_run(
        self, *, provider: str, query_key: str, status_value: str, metadata: dict
    ):
        run = {
            "id": f"run-{len(self.ingestion_runs) + 1}",
            "provider": provider,
            "query_key": query_key,
            "status": status_value,
            "metadata": metadata,
        }
        self.ingestion_runs.append(run)
        return run

    def complete_ingestion_run(
        self,
        *,
        run_id: str,
        status_value: str,
        raw_count: int,
        normalized_count: int,
        deduped_count: int,
        error_message: str | None = None,
        metadata: dict | None = None,
    ):
        self.ingestion_runs.append(
            {
                "id": run_id,
                "status": status_value,
                "raw_count": raw_count,
                "normalized_count": normalized_count,
                "deduped_count": deduped_count,
                "error_message": error_message,
                "metadata": metadata or {},
            }
        )


@pytest.fixture
def fake_repository(monkeypatch):
    repo = FakeRepository()
    monkeypatch.setattr(
        "app.services.jobs.job_ingestion.JobCacheRepository",
        lambda: repo,
    )
    return repo


def make_job(
    *,
    job_id: str,
    title: str,
    location: str,
    remote: bool,
    remote_type: str,
    description: str,
    experience_level: str,
    role_type: str = "software-engineering",
    company: str = "TestCo",
    url: str | None = None,
    source: str = "fake",
) -> NormalizedJob:
    return NormalizedJob(
        id=job_id,
        title=title,
        company=company,
        location=location,
        remote=remote,
        remote_type=remote_type,
        url=url or f"https://example.com/{job_id}",
        source=source,
        summary="",
        description=description,
        responsibilities=[],
        qualifications=[],
        required_skills=[],
        preferred_skills=[],
        employment_type=None,
        experience_level=experience_level,
        role_type=role_type,
        salary_min=None,
        salary_max=None,
        salary_currency=None,
    )


class FakeProvider:
    source_name = "fake"

    async def fetch_jobs(self):
        return [
            make_job(
                job_id="1",
                title="Junior Software Engineer",
                location="Atlanta, GA",
                remote=False,
                remote_type="onsite",
                description="0-2 years experience. Entry level role.",
                experience_level="entry-level",
            ),
            make_job(
                job_id="2",
                title="Senior Backend Engineer",
                location="Atlanta, GA",
                remote=False,
                remote_type="onsite",
                description="10+ years experience",
                experience_level="senior",
            ),
            make_job(
                job_id="3",
                title="Software Engineer",
                location="Berlin, Germany",
                remote=False,
                remote_type="onsite",
                description="",
                experience_level="junior",
            ),
            make_job(
                job_id="4",
                title="IT Support Specialist",
                location="New York, NY",
                remote=False,
                remote_type="onsite",
                description="Help desk support role",
                experience_level="unknown",
                role_type="technical-support",
            ),
            make_job(
                job_id="5",
                title="Software Engineer I",
                location="Remote, United States",
                remote=True,
                remote_type="remote",
                description="Must be authorized to work in the US",
                experience_level="mid-level",
            ),
        ]


@pytest.mark.asyncio
async def test_ingestion_pipeline_filters_correctly(
    patch_settings,
    fake_repository,
):
    providers = {"fake": FakeProvider()}

    jobs = await get_jobs(
        remote_only=False,
        levels=None,
        role_types=None,
        providers=providers,
    )

    titles = [job["title"] for job in jobs]

    assert "Junior Software Engineer" in titles
    assert "IT Support Specialist" in titles
    assert "Software Engineer I" in titles

    assert "Senior Backend Engineer" not in titles
    assert "Software Engineer" not in titles


@pytest.mark.asyncio
async def test_entry_junior_filter_does_not_zero_out(
    patch_settings,
    fake_repository,
):
    providers = {"fake": FakeProvider()}

    jobs = await get_jobs(
        levels=["entry-level", "junior"],
        providers=providers,
    )

    assert len(jobs) > 0

    titles = [job["title"] for job in jobs]
    assert "Junior Software Engineer" in titles
    assert "IT Support Specialist" in titles

    assert "Senior Backend Engineer" not in titles


@pytest.mark.asyncio
async def test_remote_only_filter(
    patch_settings,
    fake_repository,
):
    providers = {"fake": FakeProvider()}

    jobs = await get_jobs(
        remote_only=True,
        providers=providers,
    )

    assert len(jobs) > 0
    assert all(job["remote"] for job in jobs)

    titles = [job["title"] for job in jobs]
    assert "Software Engineer I" in titles
    assert "Junior Software Engineer" not in titles


@pytest.mark.asyncio
async def test_deduplication(
    patch_settings,
    fake_repository,
):
    class DuplicateProvider(FakeProvider):
        async def fetch_jobs(self):
            jobs = await super().fetch_jobs()
            return jobs + [jobs[0]]

    providers = {"fake": DuplicateProvider()}

    jobs = await get_jobs(providers=providers)

    ids = [job["id"] for job in jobs]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_empty_provider_safe(
    patch_settings,
    fake_repository,
):
    class EmptyProvider:
        source_name = "fake"

        async def fetch_jobs(self):
            return []

    jobs = await get_jobs(providers={"fake": EmptyProvider()})

    assert jobs == []


@pytest.mark.asyncio
async def test_service_wrapper_uses_injected_providers(
    patch_settings,
    fake_repository,
):
    service = JobIngestionService(providers={"fake": FakeProvider()})

    jobs = await service.ingest_jobs()

    titles = [job["title"] for job in jobs]
    assert "Junior Software Engineer" in titles
    assert "Senior Backend Engineer" not in titles


@pytest.mark.asyncio
async def test_returns_query_cache_before_db_and_providers(
    patch_settings,
    fake_repository,
):
    query_key = fake_repository.build_query_cache_key(
        remote_only=False,
        levels=None,
        role_types=None,
    )
    cached_job = make_job(
        job_id="cached-1",
        title="Cached Analyst",
        location="Atlanta, GA",
        remote=False,
        remote_type="onsite",
        description="Entry level analyst role",
        experience_level="entry-level",
        role_type="data-analyst",
    )
    fake_repository.query_cache[query_key] = {"job_ids": ["cached-1"]}
    fake_repository.query_rows_by_ids["cached-1"] = cached_job

    class ExplodingProvider:
        source_name = "fake"

        async def fetch_jobs(self):
            raise AssertionError("Provider should not be called when query cache hits")

    jobs = await get_jobs(providers={"fake": ExplodingProvider()})

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Cached Analyst"


@pytest.mark.asyncio
async def test_returns_shared_db_cache_when_threshold_met(
    patch_settings,
    fake_repository,
):
    fake_repository.active_rows = [
        make_job(
            job_id="db-1",
            title="Junior Software Engineer",
            location="Atlanta, GA",
            remote=False,
            remote_type="onsite",
            description="Entry level",
            experience_level="entry-level",
        ),
        make_job(
            job_id="db-2",
            title="IT Support Specialist",
            location="New York, NY",
            remote=False,
            remote_type="onsite",
            description="Support role",
            experience_level="unknown",
            role_type="technical-support",
        ),
    ]

    class ExplodingProvider:
        source_name = "fake"

        async def fetch_jobs(self):
            raise AssertionError("Provider should not be called when DB cache is sufficient")

    jobs = await get_jobs(providers={"fake": ExplodingProvider()})

    assert len(jobs) == 2
    assert {job["title"] for job in jobs} == {
        "Junior Software Engineer",
        "IT Support Specialist",
    }
    assert fake_repository.upserted_query_cache


@pytest.mark.asyncio
async def test_db_only_reads_returns_shared_jobs_without_refresh(
    patch_settings,
    fake_repository,
):
    patch_settings.JOBS_DB_ONLY_READS = True
    patch_settings.JOBS_SHARED_CACHE_MIN_RESULTS = 5

    fake_repository.active_rows = [
        make_job(
            job_id="db-1",
            title="Junior Software Engineer",
            location="Atlanta, GA",
            remote=False,
            remote_type="onsite",
            description="Entry level",
            experience_level="entry-level",
        )
    ]

    class ExplodingProvider:
        source_name = "fake"

        async def fetch_jobs(self):
            raise AssertionError("Provider should not run in DB-only mode")

    jobs = await get_jobs(providers={"fake": ExplodingProvider()})

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Junior Software Engineer"


@pytest.mark.asyncio
async def test_running_ingestion_guard_skips_provider(
    patch_settings,
    fake_repository,
):
    query_key = fake_repository.build_query_cache_key(
        remote_only=False,
        levels=None,
        role_types=None,
    )
    fake_repository.running_ingestions.add(("fake", query_key))

    jobs = await get_jobs(providers={"fake": FakeProvider()})

    assert jobs == []
    assert fake_repository.upserted_jobs == []


@pytest.mark.asyncio
async def test_refresh_cooldown_skips_provider(
    patch_settings,
    fake_repository,
):
    query_key = fake_repository.build_query_cache_key(
        remote_only=False,
        levels=None,
        role_types=None,
    )
    fake_repository.cooldown_ingestions.add(("fake", query_key))

    jobs = await get_jobs(providers={"fake": FakeProvider()})

    assert jobs == []
    assert fake_repository.upserted_jobs == []


@pytest.mark.asyncio
async def test_failed_provider_run_is_recorded(
    patch_settings,
    fake_repository,
):
    class FailingProvider:
        source_name = "fake"

        async def fetch_jobs(self):
            raise RuntimeError("provider boom")

    jobs = await get_jobs(providers={"fake": FailingProvider()})

    assert jobs == []
    assert any(run.get("status") == "failed" for run in fake_repository.ingestion_runs)


@pytest.mark.asyncio
async def test_fetch_provider_jobs_accepts_sync_fetcher() -> None:
    class SyncProvider:
        def fetch_jobs(self):
            return [{"id": "1"}]

    jobs = await _fetch_provider_jobs("sync", SyncProvider())

    assert jobs == [{"id": "1"}]


@pytest.mark.asyncio
async def test_fetch_provider_jobs_returns_empty_for_non_list() -> None:
    class BadProvider:
        def fetch_jobs(self):
            return {"not": "a-list"}

    jobs = await _fetch_provider_jobs("bad", BadProvider())

    assert jobs == []


def test_coerce_to_normalized_job_accepts_model() -> None:
    job = make_job(
        job_id="1",
        title="Junior Software Engineer",
        location="Atlanta, GA",
        remote=False,
        remote_type="onsite",
        description="Entry level",
        experience_level="entry-level",
    )

    assert _coerce_to_normalized_job(job, "fake") == job


def test_coerce_to_normalized_job_accepts_valid_dict() -> None:
    job = _coerce_to_normalized_job(
        {
            "id": "dict-1",
            "title": "Junior Data Analyst",
            "company": "Bloom Labs",
            "location": "Atlanta, GA",
            "remote": False,
            "remote_type": "onsite",
            "url": "https://example.com/dict-1",
            "source": "fake",
            "summary": "",
            "description": "Entry level analyst role",
            "responsibilities": [],
            "qualifications": [],
            "required_skills": [],
            "preferred_skills": [],
            "employment_type": None,
            "experience_level": "entry-level",
            "role_type": "data-analyst",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": None,
        },
        "fake",
    )

    assert job is not None
    assert job.title == "Junior Data Analyst"


def test_coerce_to_normalized_job_rejects_invalid_payload() -> None:
    job = _coerce_to_normalized_job({"hello": "world"}, "fake")
    assert job is None


def test_is_remote_job_checks_flags_and_text() -> None:
    flagged = make_job(
        job_id="1",
        title="Remote Engineer",
        location="Atlanta, GA",
        remote=True,
        remote_type="onsite",
        description="",
        experience_level="entry-level",
    )
    remote_type = make_job(
        job_id="2",
        title="Engineer",
        location="Atlanta, GA",
        remote=False,
        remote_type="remote",
        description="",
        experience_level="entry-level",
    )
    location_text = make_job(
        job_id="3",
        title="Engineer",
        location="Remote, United States",
        remote=False,
        remote_type="unknown",
        description="",
        experience_level="entry-level",
    )
    description_text = make_job(
        job_id="4",
        title="Engineer",
        location="Atlanta, GA",
        remote=False,
        remote_type="unknown",
        description="Telework available",
        experience_level="entry-level",
    )

    assert _is_remote_job(flagged)
    assert _is_remote_job(remote_type)
    assert _is_remote_job(location_text)
    assert _is_remote_job(description_text)


def test_build_public_job_id_prefers_canonical_url() -> None:
    job = make_job(
        job_id="abc",
        title="Engineer",
        location="Atlanta, GA",
        remote=False,
        remote_type="onsite",
        description="",
        experience_level="entry-level",
        source="fake",
        url="HTTPS://Example.com/Jobs/123/?foo=bar",
    )

    public_id = _build_public_job_id(job)

    assert public_id == "fake:https://example.com/jobs/123"


def test_build_public_job_id_falls_back_when_url_invalid() -> None:
    job = make_job(
        job_id="abc",
        title="Engineer",
        location="Atlanta, GA",
        remote=False,
        remote_type="onsite",
        description="",
        experience_level="entry-level",
        source="fake",
        url="not-a-real-url",
    )

    public_id = _build_public_job_id(job)

    assert public_id == "fake:abc"


def test_canonical_url_normalizes_urls() -> None:
    assert _canonical_url("HTTPS://Example.com/Jobs/123/?foo=bar") == "https://example.com/jobs/123"
    assert _canonical_url("https://example.com/jobs/123/") == "https://example.com/jobs/123"
    assert _canonical_url("") == ""
    assert _canonical_url("not-a-real-url") == ""


def test_normalize_text_compacts_spacing() -> None:
    assert _normalize_text("  Remote   United   States  ") == "remote united states"