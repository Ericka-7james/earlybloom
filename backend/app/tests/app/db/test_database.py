from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.db.database import (
    JobCacheRepository,
    ResumeRepository,
    _coerce_int,
    _coerce_string_list,
    _fallback_stable_key,
    _parse_timestamptz,
    get_user_id_from_bearer_token,
)
from app.schemas.jobs import NormalizedJob


class FakeExecuteResult:
    def __init__(self, data=None):
        self.data = data


class FakeQuery:
    def __init__(self, table_name: str, client):
        self.table_name = table_name
        self.client = client
        self.filters = []
        self.limit_value = None
        self.payload = None
        self.on_conflict = None
        self.operation = "select"

    def select(self, _columns):
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def gte(self, key, value):
        self.filters.append(("gte", key, value))
        return self

    def lte(self, key, value):
        self.filters.append(("lte", key, value))
        return self

    def in_(self, key, value):
        self.filters.append(("in", key, list(value)))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def maybe_single(self):
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self.operation = "upsert"
        self.payload = payload
        self.on_conflict = on_conflict
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def execute(self):
        self.client.last_query = self
        data = self.client.responses.get(self.table_name, [])
        return FakeExecuteResult(data)


class FakeAuth:
    def __init__(self, user_id="user-123", raise_exc=False):
        self.user_id = user_id
        self.raise_exc = raise_exc

    def get_user(self, _token):
        if self.raise_exc:
            raise RuntimeError("boom")
        user = None if self.user_id is None else SimpleNamespace(id=self.user_id)
        return SimpleNamespace(user=user)


class FakeClient:
    def __init__(self, responses=None, auth=None):
        self.responses = responses or {}
        self.auth = auth or FakeAuth()
        self.last_query = None

    def table(self, name):
        return FakeQuery(name, self)


def make_job(**overrides):
    payload = {
        "id": "job-1",
        "title": "Software Engineer I",
        "company": "EarlyBloom",
        "location": "Atlanta, GA",
        "location_display": "Atlanta, GA",
        "remote": True,
        "remote_type": "remote",
        "url": "https://example.com/job-1",
        "source": "greenhouse",
        "source_job_id": "gh-1",
        "summary": "summary",
        "description": "desc",
        "responsibilities": ["ship"],
        "qualifications": ["degree"],
        "required_skills": ["python"],
        "preferred_skills": ["react"],
        "employment_type": "full-time",
        "experience_level": "entry-level",
        "role_type": "software-engineering",
        "salary_min": 80000,
        "salary_max": 100000,
        "salary_currency": "USD",
        "stable_key": "stable-job-1",
        "provider_payload_hash": "hash-1",
    }
    payload.update(overrides)
    return NormalizedJob(**payload)


def test_get_user_id_from_bearer_token_success(monkeypatch):
    client = FakeClient(auth=FakeAuth(user_id="abc-123"))
    monkeypatch.setattr("app.db.database.get_supabase_admin", lambda: client)

    assert get_user_id_from_bearer_token("Bearer token") == "abc-123"


def test_get_user_id_from_bearer_token_missing_header():
    with pytest.raises(HTTPException):
        get_user_id_from_bearer_token(None)


def test_get_user_id_from_bearer_token_invalid_prefix():
    with pytest.raises(HTTPException):
        get_user_id_from_bearer_token("Token abc")


def test_get_user_id_from_bearer_token_missing_user(monkeypatch):
    client = FakeClient(auth=FakeAuth(user_id=None))
    monkeypatch.setattr("app.db.database.get_supabase_admin", lambda: client)

    with pytest.raises(HTTPException):
        get_user_id_from_bearer_token("Bearer token")


def test_list_active_jobs_filters_expired_rows():
    now = datetime.now(timezone.utc)

    client = FakeClient(
        responses={
            "jobs_cache": [
                {
                    "id": "1",
                    "expires_at": (now + timedelta(days=1)).isoformat(),
                },
                {
                    "id": "2",
                    "expires_at": (now - timedelta(days=1)).isoformat(),
                },
            ]
        }
    )

    repo = JobCacheRepository(client=client)
    rows = repo.list_active_jobs()

    assert len(rows) == 1
    assert rows[0]["id"] == "1"


def test_list_active_jobs_by_public_ids_returns_empty_when_blank():
    repo = JobCacheRepository(client=FakeClient())

    assert repo.list_active_jobs_by_public_ids(["", "   "]) == []


def test_get_active_job_by_public_id_raises_when_missing():
    repo = JobCacheRepository(client=FakeClient())

    with pytest.raises(HTTPException):
        repo.get_active_job_by_public_id("job-x")


def test_upsert_jobs_returns_empty_for_no_jobs():
    repo = JobCacheRepository(client=FakeClient())

    assert repo.upsert_jobs([]) == []


def test_upsert_jobs_builds_payload():
    client = FakeClient(responses={"jobs_cache": [{"id": "row-1"}]})
    repo = JobCacheRepository(client=client)

    result = repo.upsert_jobs([make_job()])

    assert result == [{"id": "row-1"}]
    assert client.last_query.operation == "upsert"
    assert client.last_query.on_conflict == "stable_key"


def test_get_query_cache_returns_none_when_missing():
    repo = JobCacheRepository(client=FakeClient())

    assert repo.get_query_cache(cache_key="abc") is None


def test_get_query_cache_returns_none_when_expired():
    client = FakeClient(
        responses={
            "job_query_cache": [
                {
                    "cache_key": "abc",
                    "expires_at": (
                        datetime.now(timezone.utc) - timedelta(seconds=1)
                    ).isoformat(),
                }
            ]
        }
    )

    repo = JobCacheRepository(client=client)

    assert repo.get_query_cache(cache_key="abc") is None


def test_get_query_cache_returns_row_when_valid():
    row = {
        "cache_key": "abc",
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=5)
        ).isoformat(),
    }

    repo = JobCacheRepository(
        client=FakeClient(responses={"job_query_cache": [row]})
    )

    assert repo.get_query_cache(cache_key="abc") == row


def test_cleanup_expired_jobs_returns_counts(monkeypatch):
    repo = JobCacheRepository(client=FakeClient())

    monkeypatch.setattr(repo, "mark_expired_jobs_inactive", lambda: [{"id": "1"}])
    monkeypatch.setattr(repo, "delete_long_expired_jobs", lambda grace_hours=48: [{"id": "2"}])

    assert repo.cleanup_expired_jobs() == {
        "marked_inactive": 1,
        "deleted": 1,
    }


def test_row_to_normalized_job_returns_model():
    repo = JobCacheRepository(client=FakeClient())

    row = {
        "id": "row-1",
        "normalized_job_id": "job-1",
        "stable_key": "stable-job-1",
        "title": "Software Engineer I",
        "company": "EarlyBloom",
        "location": "Atlanta, GA",
        "location_display": "Atlanta, GA",
        "remote": True,
        "remote_type": "remote",
        "url": "https://example.com",
        "source": "greenhouse",
        "responsibilities": ["ship"],
        "qualifications": ["degree"],
        "required_skills": ["python"],
        "preferred_skills": ["react"],
        "experience_level": "entry-level",
        "role_type": "software-engineering",
    }

    job = repo.row_to_normalized_job(row)

    assert job is not None
    assert job.id == "job-1"


def test_build_query_cache_key_is_stable():
    repo = JobCacheRepository(client=FakeClient())

    key_a = repo.build_query_cache_key(
        remote_only=True,
        levels=["Junior", "entry-level"],
        role_types=["backend"],
    )

    key_b = repo.build_query_cache_key(
        remote_only=True,
        levels=["entry-level", "junior"],
        role_types=["backend"],
    )

    assert key_a == key_b


def test_resume_repository_get_resume_for_user_returns_row():
    row = {"id": "resume-1"}

    repo = ResumeRepository(
        client=FakeClient(responses={"resumes": [row]})
    )

    assert repo.get_resume_for_user("resume-1", "user-1") == row


def test_resume_repository_get_resume_for_user_raises_when_missing():
    repo = ResumeRepository(client=FakeClient())

    with pytest.raises(HTTPException):
        repo.get_resume_for_user("resume-1", "user-1")


def test_resume_repository_update_resume_parse_result_returns_row():
    row = {"id": "resume-1", "parse_status": "parsed"}

    repo = ResumeRepository(
        client=FakeClient(responses={"resumes": [row]})
    )

    result = repo.update_resume_parse_result(
        resume_id="resume-1",
        user_id="user-1",
        parse_status="parsed",
        raw_text="hello",
    )

    assert result["parse_status"] == "parsed"


def test_resume_repository_create_resume_log_returns_row():
    row = {"id": "log-1"}

    repo = ResumeRepository(
        client=FakeClient(responses={"resume_logs": [row]})
    )

    assert repo.create_resume_log(
        resume_id="resume-1",
        user_id="user-1",
        event_type="started",
    ) == row


def test_resume_repository_list_resume_logs_returns_rows():
    rows = [{"id": "1"}, {"id": "2"}]

    repo = ResumeRepository(
        client=FakeClient(responses={"resume_logs": rows})
    )

    assert repo.list_resume_logs(
        resume_id="resume-1",
        user_id="user-1",
    ) == rows


def test_fallback_stable_key_is_deterministic():
    job = make_job(id="")

    assert _fallback_stable_key(job) == _fallback_stable_key(job)


def test_coerce_string_list_filters_blank():
    assert _coerce_string_list([" Python ", "", "FastAPI"]) == [
        "Python",
        "FastAPI",
    ]


def test_coerce_int_handles_values():
    assert _coerce_int("10") == 10
    assert _coerce_int("10.9") == 10
    assert _coerce_int("") is None
    assert _coerce_int("abc") is None


def test_parse_timestamptz_handles_values():
    assert _parse_timestamptz("2026-04-15T12:00:00Z") is not None
    assert _parse_timestamptz("") is None
    assert _parse_timestamptz("bad-date") is None