from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import jobs as jobs_routes
from app.api.routes.jobs import (
    ViewerContext,
    get_job_cache_repository,
    get_job_ingestion_service,
    get_optional_viewer_context,
    router,
)

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"


def _public_job(
    *,
    job_id: str = "job-1",
    title: str = "Software Engineer I",
    company: str = "EarlyBloom",
    viewer_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": job_id,
        "title": title,
        "company": company,
        "location": "Atlanta, GA",
        "location_display": "Atlanta, GA",
        "remote": False,
        "remote_type": "onsite",
        "url": "https://example.com/jobs/job-1",
        "source": "greenhouse",
        "source_job_id": "source-job-1",
        "summary": "Junior-friendly role.",
        "description": "Build and maintain product features.",
        "responsibilities": ["Ship features"],
        "qualifications": ["1+ years or equivalent projects"],
        "required_skills": ["Python"],
        "preferred_skills": ["React"],
        "employment_type": "Full-time",
        "experience_level": "entry-level",
        "role_type": "software-engineering",
        "salary_min": 80000,
        "salary_max": 100000,
        "salary_currency": "USD",
        "stable_key": "stable-job-1",
        "provider_payload_hash": "hash-job-1",
        "viewer_state": viewer_state
        or {
            "is_saved": False,
            "is_hidden": False,
            "saved_at": None,
            "hidden_at": None,
        },
    }


class FakeIngestionService:
    def __init__(
        self,
        jobs: list[dict[str, Any]] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.jobs = jobs or []
        self.exc = exc
        self.calls = 0

    async def ingest_jobs(self) -> list[dict[str, Any]]:
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.jobs


class FakeJobCacheRepository:
    def __init__(self) -> None:
        self.saved_calls: list[tuple[str, str]] = []
        self.unsaved_calls: list[tuple[str, str]] = []
        self.hidden_calls: list[tuple[str, str]] = []
        self.unhidden_calls: list[tuple[str, str]] = []
        self.apply_calls: list[dict[str, Any]] = []
        self.saved_rows: list[dict[str, Any]] = []
        self.hidden_rows: list[dict[str, Any]] = []
        self.row_map: dict[str, dict[str, Any] | None] = {}
        self.raise_on: str | None = None

    def apply_viewer_state_to_jobs(
        self,
        *,
        user_id: str,
        jobs: list[dict[str, Any]],
        exclude_hidden: bool,
    ) -> list[dict[str, Any]]:
        self.apply_calls.append(
            {
                "user_id": user_id,
                "jobs": jobs,
                "exclude_hidden": exclude_hidden,
            }
        )

        if self.raise_on == "apply_viewer_state_to_jobs":
            raise RuntimeError("viewer state failed")

        updated: list[dict[str, Any]] = []
        for job in jobs:
            job_copy = dict(job)
            current_viewer_state = dict(job_copy.get("viewer_state") or {})
            if not current_viewer_state:
                current_viewer_state = {
                    "is_saved": False,
                    "is_hidden": False,
                    "saved_at": None,
                    "hidden_at": None,
                }

            if job_copy.get("id") in {"job-saved", "saved-1"}:
                current_viewer_state["is_saved"] = True
                current_viewer_state["saved_at"] = "2026-04-14T12:00:00Z"

            if job_copy.get("id") in {"job-hidden", "hidden-1"}:
                current_viewer_state["is_hidden"] = True
                current_viewer_state["hidden_at"] = "2026-04-14T13:00:00Z"

            job_copy["viewer_state"] = current_viewer_state
            updated.append(job_copy)

        if exclude_hidden:
            updated = [
                job
                for job in updated
                if not job["viewer_state"].get("is_hidden", False)
            ]

        return updated

    def save_job_for_user(self, *, user_id: str, public_job_id: str) -> None:
        if self.raise_on == "save_job_for_user":
            raise RuntimeError("save failed")
        self.saved_calls.append((user_id, public_job_id))

    def unsave_job_for_user(self, *, user_id: str, public_job_id: str) -> None:
        if self.raise_on == "unsave_job_for_user":
            raise RuntimeError("unsave failed")
        self.unsaved_calls.append((user_id, public_job_id))

    def hide_job_for_user(self, *, user_id: str, public_job_id: str) -> None:
        if self.raise_on == "hide_job_for_user":
            raise RuntimeError("hide failed")
        self.hidden_calls.append((user_id, public_job_id))

    def unhide_job_for_user(self, *, user_id: str, public_job_id: str) -> None:
        if self.raise_on == "unhide_job_for_user":
            raise RuntimeError("unhide failed")
        self.unhidden_calls.append((user_id, public_job_id))

    def list_saved_jobs_for_user(self, *, user_id: str) -> list[dict[str, Any]]:
        if self.raise_on == "list_saved_jobs_for_user":
            raise RuntimeError("saved list failed")
        return self.saved_rows

    def list_hidden_jobs_for_user(self, *, user_id: str) -> list[dict[str, Any]]:
        if self.raise_on == "list_hidden_jobs_for_user":
            raise RuntimeError("hidden list failed")
        return self.hidden_rows

    def row_to_normalized_job(self, row: dict[str, Any]) -> dict[str, Any] | None:
        row_id = row.get("id")
        return self.row_map.get(row_id)


@pytest.fixture
def repo() -> FakeJobCacheRepository:
    return FakeJobCacheRepository()


@pytest.fixture
def ingestion_service() -> FakeIngestionService:
    return FakeIngestionService(jobs=[_public_job()])


@pytest.fixture
def app(
    repo: FakeJobCacheRepository,
    ingestion_service: FakeIngestionService,
) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_job_cache_repository] = lambda: repo
    test_app.dependency_overrides[get_job_ingestion_service] = lambda: ingestion_service
    test_app.dependency_overrides[get_optional_viewer_context] = lambda: ViewerContext()
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def set_authenticated_viewer(app: FastAPI, user_id: str = TEST_USER_ID) -> None:
    app.dependency_overrides[get_optional_viewer_context] = (
        lambda: ViewerContext(user_id=user_id)
    )


def test_list_jobs_returns_jobs_for_guest(
    client: TestClient,
    repo: FakeJobCacheRepository,
    ingestion_service: FakeIngestionService,
) -> None:
    ingestion_service.jobs = [_public_job(job_id="job-guest")]

    response = client.get("/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["jobs"][0]["id"] == "job-guest"
    assert payload["jobs"][0]["viewer_state"]["is_saved"] is False
    assert repo.apply_calls == []


def test_list_jobs_applies_viewer_state_for_authenticated_user(
    app: FastAPI,
    repo: FakeJobCacheRepository,
    ingestion_service: FakeIngestionService,
) -> None:
    ingestion_service.jobs = [
        _public_job(job_id="job-saved"),
        _public_job(job_id="job-hidden"),
    ]
    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.get("/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["jobs"][0]["id"] == "job-saved"
    assert payload["jobs"][0]["viewer_state"]["is_saved"] is True
    assert repo.apply_calls[0]["user_id"] == TEST_USER_ID
    assert repo.apply_calls[0]["exclude_hidden"] is True


def test_list_jobs_returns_500_when_ingestion_fails(
    client: TestClient,
    ingestion_service: FakeIngestionService,
) -> None:
    ingestion_service.exc = RuntimeError("boom")

    response = client.get("/jobs")

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to load jobs at this time."}


def test_get_jobs_profile_returns_default_profile_for_guest(
    client: TestClient,
) -> None:
    response = client.get("/jobs/profile")

    assert response.status_code == 200
    assert response.json() == jobs_routes.DEFAULT_RESOLVED_JOB_PROFILE


def test_get_jobs_profile_returns_resolved_profile_for_authenticated_user(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_profile = {
        "desiredLevels": ["entry-level", "junior"],
        "preferredRoleTypes": ["backend"],
        "preferredWorkplaceTypes": ["remote"],
        "preferredLocations": ["Atlanta, GA"],
        "skills": ["Python", "FastAPI"],
        "isLgbtFriendlyOnly": True,
    }

    set_authenticated_viewer(app)

    monkeypatch.setattr(
        jobs_routes,
        "resolve_job_profile_for_user_id",
        lambda user_id: expected_profile,
    )

    client = TestClient(app)
    response = client.get("/jobs/profile")

    assert response.status_code == 200
    assert response.json() == expected_profile


def test_get_jobs_profile_returns_500_when_profile_resolution_fails(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_authenticated_viewer(app)

    def _raise(_: str) -> dict[str, Any]:
        raise RuntimeError("profile failed")

    monkeypatch.setattr(jobs_routes, "resolve_job_profile_for_user_id", _raise)

    client = TestClient(app)
    response = client.get("/jobs/profile")

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to load job profile at this time."}


def test_save_job_requires_authentication(client: TestClient) -> None:
    response = client.post("/jobs/saved", json={"job_id": "job-1"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Sign in is required for this action."}


def test_save_job_returns_tracker_mutation_response_for_authenticated_user(
    app: FastAPI,
    repo: FakeJobCacheRepository,
) -> None:
    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.post("/jobs/saved", json={"job_id": "job-saved"})

    assert response.status_code == 201
    assert repo.saved_calls == [(TEST_USER_ID, "job-saved")]
    assert response.json() == {
        "job_id": "job-saved",
        "viewer_state": {
            "is_saved": True,
            "is_hidden": False,
            "saved_at": "2026-04-14T12:00:00Z",
            "hidden_at": None,
        },
    }


def test_save_job_returns_500_when_repository_save_fails(
    app: FastAPI,
    repo: FakeJobCacheRepository,
) -> None:
    repo.raise_on = "save_job_for_user"
    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.post("/jobs/saved", json={"job_id": "job-saved"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to save this job right now."}


def test_unsave_job_returns_tracker_mutation_response(
    app: FastAPI,
    repo: FakeJobCacheRepository,
) -> None:
    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.delete("/jobs/saved/job-1")

    assert response.status_code == 200
    assert repo.unsaved_calls == [(TEST_USER_ID, "job-1")]
    assert response.json()["job_id"] == "job-1"
    assert response.json()["viewer_state"]["is_saved"] is False


def test_hide_job_returns_tracker_mutation_response(
    app: FastAPI,
    repo: FakeJobCacheRepository,
) -> None:
    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.post("/jobs/hidden", json={"job_id": "job-hidden"})

    assert response.status_code == 201
    assert repo.hidden_calls == [(TEST_USER_ID, "job-hidden")]
    assert response.json() == {
        "job_id": "job-hidden",
        "viewer_state": {
            "is_saved": False,
            "is_hidden": True,
            "saved_at": None,
            "hidden_at": "2026-04-14T13:00:00Z",
        },
    }


def test_unhide_job_returns_tracker_mutation_response(
    app: FastAPI,
    repo: FakeJobCacheRepository,
) -> None:
    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.delete("/jobs/hidden/job-1")

    assert response.status_code == 200
    assert repo.unhidden_calls == [(TEST_USER_ID, "job-1")]
    assert response.json()["job_id"] == "job-1"
    assert response.json()["viewer_state"]["is_hidden"] is False


def test_list_saved_jobs_returns_related_jobs(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    repo: FakeJobCacheRepository,
) -> None:
    repo.saved_rows = [{"id": "saved-row-1"}]
    repo.row_map["saved-row-1"] = _public_job(job_id="saved-1")

    monkeypatch.setattr(
        jobs_routes,
        "map_normalized_job_to_response",
        lambda normalized: normalized,
    )

    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.get("/jobs/saved")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["jobs"][0]["id"] == "saved-1"
    assert payload["jobs"][0]["viewer_state"]["is_saved"] is True
    assert repo.apply_calls[0]["exclude_hidden"] is False


def test_list_hidden_jobs_returns_related_jobs(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    repo: FakeJobCacheRepository,
) -> None:
    repo.hidden_rows = [{"id": "hidden-row-1"}]
    repo.row_map["hidden-row-1"] = _public_job(job_id="hidden-1")

    monkeypatch.setattr(
        jobs_routes,
        "map_normalized_job_to_response",
        lambda normalized: normalized,
    )

    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.get("/jobs/hidden")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["jobs"][0]["id"] == "hidden-1"
    assert payload["jobs"][0]["viewer_state"]["is_hidden"] is True
    assert repo.apply_calls[0]["exclude_hidden"] is False


def test_list_saved_jobs_skips_rows_that_do_not_normalize(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    repo: FakeJobCacheRepository,
) -> None:
    repo.saved_rows = [{"id": "bad-row"}, {"id": "good-row"}]
    repo.row_map["bad-row"] = None
    repo.row_map["good-row"] = _public_job(job_id="saved-1")

    monkeypatch.setattr(
        jobs_routes,
        "map_normalized_job_to_response",
        lambda normalized: normalized,
    )

    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.get("/jobs/saved")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["jobs"][0]["id"] == "saved-1"


def test_list_hidden_jobs_returns_500_when_repository_fails(
    app: FastAPI,
    repo: FakeJobCacheRepository,
) -> None:
    repo.raise_on = "list_hidden_jobs_for_user"
    set_authenticated_viewer(app)
    client = TestClient(app)

    response = client.get("/jobs/hidden")

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to load hidden jobs right now."}