from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

import app.api.routes.tracker as tracker_routes


class FakeResumeRepository:
    def __init__(self, latest_resume=None, error: Exception | None = None):
        self.latest_resume = latest_resume
        self.error = error
        self.calls = []

    def get_latest_resume_for_user(self, user_id: str):
        self.calls.append(("get_latest_resume_for_user", {"user_id": user_id}))
        if self.error:
            raise self.error
        return self.latest_resume


class FakeJobCacheRepository:
    def __init__(self, saved_jobs=None, hidden_jobs=None):
        self.saved_jobs = saved_jobs or []
        self.hidden_jobs = hidden_jobs or []
        self.calls = []

    def list_saved_jobs_for_user(self, *, user_id: str):
        self.calls.append(("list_saved_jobs_for_user", {"user_id": user_id}))
        return self.saved_jobs

    def list_hidden_jobs_for_user(self, *, user_id: str):
        self.calls.append(("list_hidden_jobs_for_user", {"user_id": user_id}))
        return self.hidden_jobs


class FakeAdminResult:
    def __init__(self, data):
        self.data = data


class FakeProfilesTable:
    def __init__(self, calls: list, result_data):
        self.calls = calls
        self.result_data = result_data

    def upsert(self, payload, on_conflict: str):
        self.calls.append(
            (
                "profiles.upsert",
                {"payload": payload, "on_conflict": on_conflict},
            )
        )
        return self

    def execute(self):
        self.calls.append(("profiles.execute", {}))
        return FakeAdminResult(self.result_data)


class FakeAdminClient:
    def __init__(self, result_data):
        self.calls = []
        self.result_data = result_data

    def table(self, name: str):
        self.calls.append(("table", {"name": name}))
        assert name == "profiles"
        return FakeProfilesTable(self.calls, self.result_data)


@pytest.fixture
def current_context():
    return SimpleNamespace(
        refreshed=False,
        session=None,
        user=SimpleNamespace(id="user-123", email="test@example.com"),
    )


@pytest.fixture
def build_client(current_context):
    def _build(
        *,
        resume_repository=None,
        job_repository=None,
    ):
        app = FastAPI()
        app.include_router(tracker_routes.router)

        app.dependency_overrides[tracker_routes.get_current_session_context] = (
            lambda: current_context
        )
        app.dependency_overrides[tracker_routes.get_resume_repository] = (
            lambda: resume_repository or FakeResumeRepository()
        )
        app.dependency_overrides[tracker_routes.get_job_cache_repository] = (
            lambda: job_repository or FakeJobCacheRepository()
        )

        return app

    return _build


def test_normalize_string_list_cleans_and_dedupes():
    result = tracker_routes._normalize_string_list(
        [" Remote ", "remote", "", None, "Hybrid", "hybrid"]
    )

    assert result == ["remote", "hybrid"]


def test_build_preferences_from_profile_uses_defaults_when_profile_missing(monkeypatch):
    monkeypatch.setattr(
        tracker_routes,
        "DEFAULT_RESOLVED_JOB_PROFILE",
        {"desiredLevels": ["entry-level", "junior"]},
    )

    result = tracker_routes._build_preferences_from_profile(None)

    assert result.desired_levels == ["entry-level", "junior"]
    assert result.preferred_role_types == []
    assert result.preferred_workplace_types == []
    assert result.preferred_locations == []
    assert result.is_lgbt_friendly_only is False


def test_build_preferences_from_profile_maps_profile_values(monkeypatch):
    monkeypatch.setattr(
        tracker_routes,
        "DEFAULT_RESOLVED_JOB_PROFILE",
        {"desiredLevels": ["entry-level", "junior"]},
    )

    result = tracker_routes._build_preferences_from_profile(
        {
            "desired_levels": [" Junior ", "junior", "Entry-Level"],
            "preferred_role_types": ["Software Engineer", " software engineer "],
            "preferred_workplace_types": ["Remote", "Hybrid", "remote"],
            "preferred_locations": ["Atlanta, GA", " atlanta, ga "],
            "is_lgbtq_friendly_only": True,
            "is_lgbt_friendly_only": True,
        }
    )

    assert result.desired_levels == ["junior", "entry-level"]
    assert result.preferred_role_types == ["software engineer"]
    assert result.preferred_workplace_types == ["remote", "hybrid"]
    assert result.preferred_locations == ["atlanta, ga"]
    assert result.is_lgbt_friendly_only is True


def test_build_profile_summary_uses_defaults_when_profile_missing(monkeypatch):
    monkeypatch.setattr(
        tracker_routes,
        "DEFAULT_RESOLVED_JOB_PROFILE",
        {"desiredLevels": ["entry-level", "junior"]},
    )

    result = tracker_routes._build_profile_summary(
        user_id="user-123",
        user_email="test@example.com",
        profile_row=None,
    )

    assert result.display_name is None
    assert result.career_interests == []
    assert result.desired_levels == ["entry-level", "junior"]
    assert result.preferred_role_types == []
    assert result.preferred_workplace_types == []
    assert result.preferred_locations == []
    assert result.is_lgbt_friendly_only is False


def test_serialize_resume_returns_none_for_missing_record():
    assert tracker_routes._serialize_resume(None) is None


def test_serialize_resume_maps_resume_record():
    now = datetime.now(UTC).isoformat()

    result = tracker_routes._serialize_resume(
        {
            "id": "resume-123",
            "original_filename": "resume.pdf",
            "file_type": "application/pdf",
            "parse_status": "parsed",
            "updated_at": now,
            "ats_tags": ["python"],
            "parse_warnings": ["minor warning"],
            "parsed_json": {"summary": {"estimated_years_experience": 2}},
        }
    )

    assert result.id == "resume-123"
    assert result.original_filename == "resume.pdf"
    assert result.file_type == "application/pdf"
    assert result.parse_status == "parsed"
    assert result.updated_at == now
    assert result.ats_tags == ["python"]
    assert result.parse_warnings == ["minor warning"]
    assert result.parsed_json == {"summary": {"estimated_years_experience": 2}}


def test_get_tracker_returns_combined_tracker_payload(build_client, monkeypatch):
    now = datetime.now(UTC).isoformat()
    resume_repo = FakeResumeRepository(
        latest_resume={
            "id": "resume-123",
            "original_filename": "resume.pdf",
            "file_type": "application/pdf",
            "parse_status": "parsed",
            "updated_at": now,
            "ats_tags": ["python", "react"],
            "parse_warnings": [],
            "parsed_json": {"summary": {"estimated_years_experience": 2}},
        }
    )
    job_repo = FakeJobCacheRepository(
        saved_jobs=[{"id": "job-1"}, {"id": "job-2"}],
        hidden_jobs=[{"id": "job-3"}],
    )

    monkeypatch.setattr(
        tracker_routes,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "user_id": user_id,
            "email": "test@example.com",
            "display_name": "Ericka",
            "desired_levels": ["entry-level", "junior"],
            "preferred_role_types": ["software engineer"],
            "preferred_workplace_types": ["remote"],
            "preferred_locations": ["atlanta, ga"],
            "is_lgbtq_friendly_only": True,
            "is_lgbt_friendly_only": True,
            "created_at": None,
            "updated_at": None,
        },
    )

    app = build_client(resume_repository=resume_repo, job_repository=job_repo)

    with TestClient(app) as client:
        response = client.get("/tracker")

    assert response.status_code == 200
    body = response.json()

    assert body["profile"]["display_name"] == "Ericka"
    assert body["profile"]["career_interests"] == []
    assert body["profile"]["desired_levels"] == ["entry-level", "junior"]
    assert body["profile"]["preferred_role_types"] == ["software engineer"]
    assert body["profile"]["preferred_workplace_types"] == ["remote"]
    assert body["profile"]["preferred_locations"] == ["atlanta, ga"]
    assert body["profile"]["is_lgbt_friendly_only"] is True

    assert body["preferences"]["desired_levels"] == ["entry-level", "junior"]
    assert body["preferences"]["preferred_role_types"] == ["software engineer"]
    assert body["preferences"]["preferred_workplace_types"] == ["remote"]
    assert body["preferences"]["preferred_locations"] == ["atlanta, ga"]
    assert body["preferences"]["is_lgbt_friendly_only"] is True

    assert body["resume"]["id"] == "resume-123"
    assert body["resume"]["parse_status"] == "parsed"
    assert body["stats"]["saved_jobs_count"] == 2
    assert body["stats"]["hidden_jobs_count"] == 1

    assert resume_repo.calls == [
        ("get_latest_resume_for_user", {"user_id": "user-123"})
    ]
    assert job_repo.calls == [
        ("list_saved_jobs_for_user", {"user_id": "user-123"}),
        ("list_hidden_jobs_for_user", {"user_id": "user-123"}),
    ]


def test_get_tracker_allows_missing_resume_when_repository_returns_404(
    build_client, monkeypatch
):
    resume_repo = FakeResumeRepository(
        error=HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="missing")
    )
    job_repo = FakeJobCacheRepository(saved_jobs=[], hidden_jobs=[])

    monkeypatch.setattr(tracker_routes, "fetch_profile_for_user_id", lambda user_id: None)
    monkeypatch.setattr(
        tracker_routes,
        "DEFAULT_RESOLVED_JOB_PROFILE",
        {"desiredLevels": ["entry-level", "junior"]},
    )

    app = build_client(resume_repository=resume_repo, job_repository=job_repo)

    with TestClient(app) as client:
        response = client.get("/tracker")

    assert response.status_code == 200
    body = response.json()

    assert body["resume"] is None
    assert body["stats"]["saved_jobs_count"] == 0
    assert body["stats"]["hidden_jobs_count"] == 0
    assert body["preferences"]["desired_levels"] == ["entry-level", "junior"]


def test_get_tracker_returns_500_for_unexpected_error(build_client, monkeypatch):
    resume_repo = FakeResumeRepository()
    job_repo = FakeJobCacheRepository()

    def boom(_user_id):
        raise RuntimeError("database is on fire")

    monkeypatch.setattr(tracker_routes, "fetch_profile_for_user_id", boom)

    app = build_client(resume_repository=resume_repo, job_repository=job_repo)

    with TestClient(app) as client:
        response = client.get("/tracker")

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to load tracker right now."}


def test_update_tracker_preferences_persists_payload(build_client, monkeypatch):
    admin_client = FakeAdminClient(result_data=[{"user_id": "user-123"}])

    monkeypatch.setattr(tracker_routes, "get_supabase_admin", lambda: admin_client)
    monkeypatch.setattr(
        tracker_routes,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "desired_levels": ["entry-level"],
            "preferred_role_types": ["data analyst"],
            "preferred_workplace_types": ["hybrid"],
            "preferred_locations": ["new york, ny"],
            "is_lgbtq_friendly_only": False,
        },
    )

    app = build_client()

    with TestClient(app) as client:
        response = client.patch(
            "/tracker/preferences",
            json={
                "desired_levels": ["junior"],
                "preferred_role_types": ["software engineer"],
                "preferred_workplace_types": ["remote"],
                "preferred_locations": ["atlanta, ga"],
                "is_lgbt_friendly_only": True,
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert body["preferences"]["desired_levels"] == ["junior"]
    assert body["preferences"]["preferred_role_types"] == ["software engineer"]
    assert body["preferences"]["preferred_workplace_types"] == ["remote"]
    assert body["preferences"]["preferred_locations"] == ["atlanta, ga"]
    assert body["preferences"]["is_lgbt_friendly_only"] is True

    assert admin_client.calls == [
        ("table", {"name": "profiles"}),
        (
            "profiles.upsert",
            {
                "payload": {
                    "user_id": "user-123",
                    "desired_levels": ["junior"],
                    "preferred_role_types": ["software engineer"],
                    "preferred_workplace_types": ["remote"],
                    "preferred_locations": ["atlanta, ga"],
                    "is_lgbt_friendly_only": True,
                },
                "on_conflict": "user_id",
            },
        ),
        ("profiles.execute", {}),
    ]


def test_update_tracker_preferences_preserves_existing_values_when_fields_omitted(
    build_client, monkeypatch
):
    admin_client = FakeAdminClient(result_data=[{"user_id": "user-123"}])

    monkeypatch.setattr(tracker_routes, "get_supabase_admin", lambda: admin_client)
    monkeypatch.setattr(
        tracker_routes,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "desired_levels": ["entry-level"],
            "preferred_role_types": ["data analyst"],
            "preferred_workplace_types": ["hybrid"],
            "preferred_locations": ["new york, ny"],
            "is_lgbtq_friendly_only": True,
        },
    )

    app = build_client()

    with TestClient(app) as client:
        response = client.patch(
            "/tracker/preferences",
            json={
                "preferred_locations": ["atlanta, ga"],
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert body["preferences"]["desired_levels"] == ["entry-level"]
    assert body["preferences"]["preferred_role_types"] == ["data analyst"]
    assert body["preferences"]["preferred_workplace_types"] == ["hybrid"]
    assert body["preferences"]["preferred_locations"] == ["atlanta, ga"]
    assert body["preferences"]["is_lgbt_friendly_only"] is True


def test_update_tracker_preferences_returns_500_when_upsert_returns_no_data(
    build_client, monkeypatch
):
    admin_client = FakeAdminClient(result_data=None)

    monkeypatch.setattr(tracker_routes, "get_supabase_admin", lambda: admin_client)
    monkeypatch.setattr(tracker_routes, "fetch_profile_for_user_id", lambda user_id: {})

    app = build_client()

    with TestClient(app) as client:
        response = client.patch(
            "/tracker/preferences",
            json={"desired_levels": ["junior"]},
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to save tracker preferences right now."}