from __future__ import annotations

from datetime import datetime, UTC
from types import SimpleNamespace

import pytest

import app.api.routes.resume as resume_routes


class FakeResponseModel:
    """Simple stand-in for pydantic response models used in route unit tests."""

    def __init__(self, **data):
        self.__dict__.update(data)

    def __eq__(self, other):
        return isinstance(other, FakeResponseModel) and self.__dict__ == other.__dict__


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
            "latest_error": None,
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
            "latest_error": None,
            "created_at": now,
            "updated_at": now,
        }

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
        latest_error,
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
                    "latest_error": latest_error,
                    "ats_tags": ats_tags,
                },
            )
        )
        return self.updated_record


@pytest.fixture
def fake_repo():
    return FakeRepository()


@pytest.fixture
def patch_response_models(monkeypatch):
    monkeypatch.setattr(resume_routes, "ResumeRecordResponse", FakeResponseModel)
    monkeypatch.setattr(resume_routes, "ResumeLogResponse", FakeResponseModel)
    monkeypatch.setattr(resume_routes, "ParseResumeResponse", FakeResponseModel)


def test_get_current_user_id_delegates_to_token_parser(monkeypatch):
    captured = {}

    def fake_get_user_id_from_bearer_token(authorization):
        captured["authorization"] = authorization
        return "user-xyz"

    monkeypatch.setattr(
        resume_routes,
        "get_user_id_from_bearer_token",
        fake_get_user_id_from_bearer_token,
    )

    result = resume_routes.get_current_user_id("Bearer abc123")

    assert result == "user-xyz"
    assert captured["authorization"] == "Bearer abc123"


def test_get_resume_returns_resume_record_response(fake_repo, patch_response_models):
    result = resume_routes.get_resume(
        resume_id="resume-123",
        user_id="user-123",
        repository=fake_repo,
    )

    assert isinstance(result, FakeResponseModel)
    assert result.id == "resume-123"
    assert result.user_id == "user-123"
    assert result.parse_status == "uploaded"

    assert fake_repo.calls == [
        ("get_resume_for_user", {"resume_id": "resume-123", "user_id": "user-123"})
    ]


def test_get_resume_logs_validates_resume_then_returns_log_models(
    fake_repo,
    patch_response_models,
):
    result = resume_routes.get_resume_logs(
        resume_id="resume-123",
        user_id="user-123",
        repository=fake_repo,
    )

    assert len(result) == 2
    assert all(isinstance(item, FakeResponseModel) for item in result)
    assert result[0].id == "log-1"
    assert result[0].event_type == "parse_started"
    assert result[0].event_status == "info"
    assert result[1].id == "log-2"
    assert result[1].event_type == "parse_completed"
    assert result[1].event_status == "success"

    assert fake_repo.calls == [
        ("get_resume_for_user", {"resume_id": "resume-123", "user_id": "user-123"}),
        ("list_resume_logs", {"resume_id": "resume-123", "user_id": "user-123"}),
    ]


def test_parse_resume_creates_logs_updates_record_and_returns_response(
    fake_repo,
    patch_response_models,
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

    payload = SimpleNamespace(
        raw_text="A" * 400,
        file_type="pdf",
        extraction_method="plaintext",
    )

    result = resume_routes.parse_resume(
        resume_id="resume-123",
        payload=payload,
        user_id="user-123",
        repository=fake_repo,
    )

    assert isinstance(result, FakeResponseModel)
    assert result.resume_id == "resume-123"
    assert result.parse_status == "parsed"
    assert result.warnings == warnings
    assert result.parsed_json == parsed_json
    assert result.raw_text_preview == "A" * 280
    assert result.ats_tags == ats_tags

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
            "latest_error": None,
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