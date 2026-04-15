from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.routes.resume as resume_routes


class FakeRepository:
    """Repository double that records calls and returns configurable values."""

    def __init__(self):
        self.calls = []
        now = datetime.now(UTC)

        self.resume_record = {
            "id": "resume-123",
            "user_id": "user-123",
            "original_filename": "resume.pdf",
            "file_size_bytes": 2048,
            "file_type": "application/pdf",
            "upload_source": "manual",
            "storage_path": "resumes/user-123/resume-123.pdf",
            "parse_status": "uploaded",
            "raw_text": None,
            "parsed_json": None,
            "ats_tags": [],
            "parse_warnings": [],
            "created_at": now,
            "updated_at": now,
        }

        self.logs = [
            {
                "id": "log-1",
                "resume_id": "resume-123",
                "user_id": "user-123",
                "event_type": "parse_started",
                "event_status": "info",
                "message": "Resume parse started.",
                "metadata": {"file_type": "pdf"},
                "created_at": now,
            },
            {
                "id": "log-2",
                "resume_id": "resume-123",
                "user_id": "user-123",
                "event_type": "parse_completed",
                "event_status": "success",
                "message": "Resume parsed successfully.",
                "metadata": {"warning_count": 1},
                "created_at": now,
            },
        ]

        self.updated_record = {
            "id": "resume-123",
            "user_id": "user-123",
            "original_filename": "resume.pdf",
            "file_size_bytes": 2048,
            "file_type": "application/pdf",
            "upload_source": "manual",
            "storage_path": "resumes/user-123/resume-123.pdf",
            "parse_status": "parsed",
            "raw_text": "Updated raw text",
            "parsed_json": {"meta": {"confidence": 0.92}},
            "ats_tags": ["react", "python"],
            "parse_warnings": ["minor warning"],
            "created_at": now,
            "updated_at": now,
        }

        self.client = FakeSupabaseClient(self)

    def get_latest_resume_for_user(self, *, user_id: str):
        self.calls.append(("get_latest_resume_for_user", {"user_id": user_id}))
        return self.resume_record

    def get_resume_for_user(self, *, resume_id: str, user_id: str):
        self.calls.append(
            ("get_resume_for_user", {"resume_id": resume_id, "user_id": user_id})
        )
        return self.resume_record

    def list_resume_logs(self, *, resume_id: str, user_id: str):
        self.calls.append(
            ("list_resume_logs", {"resume_id": resume_id, "user_id": user_id})
        )
        return self.logs

    def create_resume_log(
        self,
        *,
        resume_id: str,
        user_id: str,
        event_type: str,
        event_status: str,
        message: str,
        metadata: dict,
    ):
        self.calls.append(
            (
                "create_resume_log",
                {
                    "resume_id": resume_id,
                    "user_id": user_id,
                    "event_type": event_type,
                    "event_status": event_status,
                    "message": message,
                    "metadata": metadata,
                },
            )
        )

    def update_resume_parse_result(
        self,
        *,
        resume_id: str,
        user_id: str,
        parse_status: str,
        raw_text: str,
        parsed_json: dict,
        parse_warnings: list[str],
        ats_tags: list[str],
    ):
        self.calls.append(
            (
                "update_resume_parse_result",
                {
                    "resume_id": resume_id,
                    "user_id": user_id,
                    "parse_status": parse_status,
                    "raw_text": raw_text,
                    "parsed_json": parsed_json,
                    "parse_warnings": parse_warnings,
                    "ats_tags": ats_tags,
                },
            )
        )
        return self.updated_record


class FakeSupabaseResult:
    def __init__(self, data):
        self.data = data


class FakeTableQuery:
    def __init__(self, repository: FakeRepository):
        self.repository = repository

    def upsert(self, row, on_conflict: str):
        self.repository.calls.append(
            (
                "client.table.upsert",
                {
                    "table": "resumes",
                    "row": row,
                    "on_conflict": on_conflict,
                },
            )
        )
        return self

    def execute(self):
        return FakeSupabaseResult([self.repository.resume_record])


class FakeSupabaseClient:
    def __init__(self, repository: FakeRepository):
        self.repository = repository

    def table(self, name: str):
        assert name == "resumes"
        return FakeTableQuery(self.repository)


@pytest.fixture
def fake_repo():
    return FakeRepository()


@pytest.fixture
def current_context():
    return SimpleNamespace(
        refreshed=False,
        session=None,
        user=SimpleNamespace(id="user-123", email="test@example.com"),
    )


@pytest.fixture
def client(fake_repo, current_context):
    app = FastAPI()
    app.include_router(resume_routes.router)

    app.dependency_overrides[resume_routes.get_resume_repository] = lambda: fake_repo
    app.dependency_overrides[resume_routes.get_current_session_context] = (
        lambda: current_context
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_current_resume_returns_latest_resume_record(client, fake_repo):
    response = client.get("/resume/current")

    assert response.status_code == 200
    body = response.json()

    assert body["id"] == "resume-123"
    assert body["user_id"] == "user-123"
    assert body["parse_status"] == "uploaded"

    assert fake_repo.calls == [
        ("get_latest_resume_for_user", {"user_id": "user-123"})
    ]


def test_create_or_update_current_resume_upserts_and_returns_record(client, fake_repo):
    response = client.post(
        "/resume/current",
        json={
            "original_filename": "resume.pdf",
            "file_size_bytes": 2048,
            "file_type": "application/pdf",
            "upload_source": "manual",
            "storage_path": "resumes/user-123/resume-123.pdf",
            "parse_status": "uploaded",
            "raw_text": None,
            "parsed_json": None,
            "ats_tags": [],
            "parse_warnings": [],
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["id"] == "resume-123"
    assert body["user_id"] == "user-123"
    assert body["original_filename"] == "resume.pdf"

    assert fake_repo.calls == [
        (
            "client.table.upsert",
            {
                "table": "resumes",
                "row": {
                    "user_id": "user-123",
                    "original_filename": "resume.pdf",
                    "file_size_bytes": 2048,
                    "file_type": "application/pdf",
                    "upload_source": "manual",
                    "storage_path": "resumes/user-123/resume-123.pdf",
                    "parse_status": "uploaded",
                    "raw_text": None,
                    "parsed_json": None,
                    "ats_tags": [],
                    "parse_warnings": [],
                },
                "on_conflict": "user_id",
            },
        )
    ]


def test_get_resume_returns_resume_record(client, fake_repo):
    response = client.get("/resume/resume-123")

    assert response.status_code == 200
    body = response.json()

    assert body["id"] == "resume-123"
    assert body["user_id"] == "user-123"
    assert body["parse_status"] == "uploaded"

    assert fake_repo.calls == [
        ("get_resume_for_user", {"resume_id": "resume-123", "user_id": "user-123"})
    ]


def test_get_resume_logs_validates_resume_then_returns_logs(client, fake_repo):
    response = client.get("/resume/resume-123/logs")

    assert response.status_code == 200
    body = response.json()

    assert len(body) == 2
    assert body[0]["id"] == "log-1"
    assert body[0]["event_type"] == "parse_started"
    assert body[0]["event_status"] == "info"
    assert body[1]["id"] == "log-2"
    assert body[1]["event_type"] == "parse_completed"
    assert body[1]["event_status"] == "success"

    assert fake_repo.calls == [
        ("get_resume_for_user", {"resume_id": "resume-123", "user_id": "user-123"}),
        ("list_resume_logs", {"resume_id": "resume-123", "user_id": "user-123"}),
    ]


def test_parse_resume_creates_logs_updates_record_and_returns_response(
    client,
    fake_repo,
    monkeypatch,
):
    parsed_json = {
        "basics": {"name": "Ericka James"},
        "meta": {"confidence": 0.92},
    }
    warnings = ["minor warning"]
    ats_tags = ["react", "python"]

    def fake_parse_resume_text(raw_text, *, file_type, extraction_method):
        assert raw_text == "A" * 400
        assert file_type == "pdf"
        assert extraction_method == "plaintext"
        return parsed_json, warnings

    def fake_extract_ats_tags(data):
        assert data == parsed_json
        return ats_tags

    monkeypatch.setattr(resume_routes, "parse_resume_text", fake_parse_resume_text)
    monkeypatch.setattr(resume_routes, "extract_ats_tags", fake_extract_ats_tags)

    response = client.post(
        "/resume/resume-123/parse",
        json={
            "raw_text": "A" * 400,
            "file_type": "pdf",
            "extraction_method": "plaintext",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["resume_id"] == "resume-123"
    assert body["parse_status"] == "parsed"
    assert body["warnings"] == warnings
    assert body["parsed_json"] == parsed_json
    assert body["raw_text_preview"] == "A" * 280
    assert body["ats_tags"] == ats_tags

    assert fake_repo.calls[0] == (
        "get_resume_for_user",
        {"resume_id": "resume-123", "user_id": "user-123"},
    )

    assert fake_repo.calls[1] == (
        "create_resume_log",
        {
            "resume_id": "resume-123",
            "user_id": "user-123",
            "event_type": "parse_started",
            "event_status": "info",
            "message": "Resume parse started.",
            "metadata": {
                "file_type": "pdf",
                "extraction_method": "plaintext",
            },
        },
    )

    assert fake_repo.calls[2] == (
        "update_resume_parse_result",
        {
            "resume_id": "resume-123",
            "user_id": "user-123",
            "parse_status": "parsed",
            "raw_text": "A" * 400,
            "parsed_json": parsed_json,
            "parse_warnings": warnings,
            "ats_tags": ats_tags,
        },
    )

    assert fake_repo.calls[3] == (
        "create_resume_log",
        {
            "resume_id": "resume-123",
            "user_id": "user-123",
            "event_type": "parse_completed",
            "event_status": "success",
            "message": "Resume parsed successfully.",
            "metadata": {
                "warning_count": 1,
                "confidence": 0.92,
                "ats_tag_count": 2,
            },
        },
    )