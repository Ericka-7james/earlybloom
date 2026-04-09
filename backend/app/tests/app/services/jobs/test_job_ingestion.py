import pytest

from app.schemas.jobs import NormalizedJob
from app.services.jobs.job_cache import clear_all_cache
from app.services.jobs.job_ingestion import JobIngestionService, get_jobs


@pytest.fixture(autouse=True)
def clear_job_cache():
    """Reset in-memory job cache between tests."""
    clear_all_cache()


# -------------------------
# Fake Provider (controlled input)
# -------------------------


class FakeProvider:
    source_name = "fake"

    async def fetch_jobs(self):
        return [
            # ✅ Good entry-level US job
            NormalizedJob(
                id="1",
                title="Junior Software Engineer",
                company="TestCo",
                location="Atlanta, GA",
                remote=False,
                remote_type="onsite",
                url="https://example.com/1",
                source="fake",
                summary="",
                description="0-2 years experience. Entry level role.",
                experience_level="entry-level",
            ),
            # ❌ Should be removed (senior)
            NormalizedJob(
                id="2",
                title="Senior Backend Engineer",
                company="TestCo",
                location="Atlanta, GA",
                remote=False,
                remote_type="onsite",
                url="https://example.com/2",
                source="fake",
                summary="",
                description="10+ years experience",
                experience_level="senior",
            ),
            # ❌ Should be removed (non-US)
            NormalizedJob(
                id="3",
                title="Software Engineer",
                company="TestCo",
                location="Berlin, Germany",
                remote=False,
                remote_type="onsite",
                url="https://example.com/3",
                source="fake",
                summary="",
                description="",
                experience_level="junior",
            ),
            # ✅ Unknown but valid (should stay)
            NormalizedJob(
                id="4",
                title="IT Support Specialist",
                company="TestCo",
                location="New York, NY",
                remote=False,
                remote_type="onsite",
                url="https://example.com/4",
                source="fake",
                summary="",
                description="Help desk support role",
                experience_level="unknown",
            ),
            # ✅ Remote US-eligible
            NormalizedJob(
                id="5",
                title="Software Engineer I",
                company="TestCo",
                location="Remote, United States",
                remote=True,
                remote_type="remote",
                url="https://example.com/5",
                source="fake",
                summary="",
                description="Must be authorized to work in the US",
                experience_level="mid-level",
            ),
        ]


# -------------------------
# Tests
# -------------------------


@pytest.mark.asyncio
async def test_ingestion_pipeline_filters_correctly():
    """Ensure pipeline keeps only valid EarlyBloom jobs."""
    providers = {"fake": FakeProvider()}

    jobs = await get_jobs(
        remote_only=False,
        levels=None,
        role_types=None,
        providers=providers,
    )

    titles = [job["title"] for job in jobs]

    # ✅ kept
    assert "Junior Software Engineer" in titles
    assert "IT Support Specialist" in titles
    assert "Software Engineer I" in titles

    # ❌ removed
    assert "Senior Backend Engineer" not in titles
    assert "Software Engineer" not in titles  # Berlin job


@pytest.mark.asyncio
async def test_entry_junior_filter_does_not_zero_out():
    """Ensure entry/junior filters still return jobs."""
    providers = {"fake": FakeProvider()}

    jobs = await get_jobs(
        levels=["entry-level", "junior"],
        providers=providers,
    )

    assert len(jobs) > 0

    titles = [job["title"] for job in jobs]

    # Should still include plausible roles
    assert "Junior Software Engineer" in titles
    assert "IT Support Specialist" in titles
    assert "Software Engineer I" in titles

    # Should still exclude obvious senior roles
    assert "Senior Backend Engineer" not in titles


@pytest.mark.asyncio
async def test_remote_only_filter():
    """Ensure remote_only flag works correctly."""
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
async def test_deduplication():
    """Ensure duplicate jobs are removed."""

    class DuplicateProvider(FakeProvider):
        async def fetch_jobs(self):
            jobs = await super().fetch_jobs()
            return jobs + [jobs[0]]  # duplicate first job

    providers = {"fake": DuplicateProvider()}

    jobs = await get_jobs(providers=providers)

    ids = [job["id"] for job in jobs]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_empty_provider_safe():
    """Ensure system does not crash with empty providers."""
    providers = {"fake": FakeProvider()}

    async def empty_fetch_jobs():
        return []

    providers["fake"].fetch_jobs = empty_fetch_jobs

    jobs = await get_jobs(providers=providers)

    assert jobs == []


@pytest.mark.asyncio
async def test_service_wrapper_uses_injected_providers():
    """Ensure the service wrapper delegates to injected providers."""
    service = JobIngestionService(providers={"fake": FakeProvider()})

    jobs = await service.ingest_jobs()

    titles = [job["title"] for job in jobs]
    assert "Junior Software Engineer" in titles
    assert "Senior Backend Engineer" not in titles