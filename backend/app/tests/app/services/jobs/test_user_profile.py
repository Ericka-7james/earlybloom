from __future__ import annotations

from types import SimpleNamespace

import app.services.jobs.user_profile as user_profile


def test_resolve_job_profile_returns_defaults_in_mock_mode(monkeypatch):
    monkeypatch.setattr(
        user_profile,
        "get_settings",
        lambda: SimpleNamespace(JOB_DATA_MODE="mock"),
    )

    result = user_profile.resolve_job_profile_for_user_id("user-123")

    assert result == {
        "desiredLevels": ["entry-level", "junior"],
        "preferredRoleTypes": [],
        "preferredWorkplaceTypes": [],
        "preferredLocations": [],
        "skills": [],
        "isLgbtFriendlyOnly": False,
    }


def test_resolve_job_profile_merges_profile_and_resume_data(monkeypatch):
    monkeypatch.setattr(
        user_profile,
        "get_settings",
        lambda: SimpleNamespace(JOB_DATA_MODE="live"),
    )
    monkeypatch.setattr(
        user_profile,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "desired_levels": [" Junior ", "entry-level"],
            "preferred_role_types": ["Backend", "backend", "Data"],
            "preferred_workplace_types": ["Remote", "Hybrid"],
            "preferred_locations": ["Atlanta, GA", " atlanta, ga ", "New York, NY"],
            "is_lgbt_friendly_only": True,
        },
    )
    monkeypatch.setattr(
        user_profile,
        "_fetch_latest_resume_for_user_id",
        lambda user_id: {
            "parsed_json": {
                "skills": ["Python", "React"],
                "summary": {"top_skill_keywords": ["FastAPI", "python"]},
                "ats_tags": ["Docker"],
            }
        },
    )

    result = user_profile.resolve_job_profile_for_user_id("user-123")

    assert result == {
        "desiredLevels": ["junior", "entry-level"],
        "preferredRoleTypes": ["backend", "data"],
        "preferredWorkplaceTypes": ["remote", "hybrid"],
        "preferredLocations": ["atlanta, ga", "new york, ny"],
        "skills": ["python", "react", "fastapi", "docker"],
        "isLgbtFriendlyOnly": True,
    }


def test_resolve_job_profile_falls_back_to_default_levels_when_missing(monkeypatch):
    monkeypatch.setattr(
        user_profile,
        "get_settings",
        lambda: SimpleNamespace(JOB_DATA_MODE="live"),
    )
    monkeypatch.setattr(
        user_profile,
        "fetch_profile_for_user_id",
        lambda user_id: {
            "desired_levels": None,
            "preferred_role_types": [],
            "preferred_workplace_types": [],
            "preferred_locations": [],
            "is_lgbt_friendly_only": False,
        },
    )
    monkeypatch.setattr(
        user_profile,
        "_fetch_latest_resume_for_user_id",
        lambda user_id: None,
    )

    result = user_profile.resolve_job_profile_for_user_id("user-123")

    assert result["desiredLevels"] == ["entry-level", "junior"]
    assert result["skills"] == []
    assert result["isLgbtFriendlyOnly"] is False


def test_resolve_job_profile_handles_missing_profile_row(monkeypatch):
    monkeypatch.setattr(
        user_profile,
        "get_settings",
        lambda: SimpleNamespace(JOB_DATA_MODE="live"),
    )
    monkeypatch.setattr(user_profile, "fetch_profile_for_user_id", lambda user_id: None)
    monkeypatch.setattr(
        user_profile,
        "_fetch_latest_resume_for_user_id",
        lambda user_id: {"parsed_json": {"skills": ["Python"]}},
    )

    result = user_profile.resolve_job_profile_for_user_id("user-123")

    assert result == {
        "desiredLevels": ["entry-level", "junior"],
        "preferredRoleTypes": [],
        "preferredWorkplaceTypes": [],
        "preferredLocations": [],
        "skills": ["python"],
        "isLgbtFriendlyOnly": False,
    }


def test_fetch_latest_resume_for_user_id_returns_resume(monkeypatch):
    class FakeResumeRepository:
        def __init__(self, client):
            self.client = client

        def get_latest_resume_for_user(self, user_id):
            assert user_id == "user-123"
            return {"id": "resume-123"}

    monkeypatch.setattr(user_profile, "get_supabase_admin", lambda: object())
    monkeypatch.setattr(user_profile, "ResumeRepository", FakeResumeRepository)

    result = user_profile._fetch_latest_resume_for_user_id("user-123")

    assert result == {"id": "resume-123"}


def test_fetch_latest_resume_for_user_id_returns_none_on_error(monkeypatch):
    class FakeResumeRepository:
        def __init__(self, client):
            self.client = client

        def get_latest_resume_for_user(self, user_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(user_profile, "get_supabase_admin", lambda: object())
    monkeypatch.setattr(user_profile, "ResumeRepository", FakeResumeRepository)

    result = user_profile._fetch_latest_resume_for_user_id("user-123")

    assert result is None


def test_extract_resume_skills_returns_empty_for_non_dict():
    assert user_profile._extract_resume_skills(None) == []
    assert user_profile._extract_resume_skills("python,react") == []


def test_extract_resume_skills_collects_from_all_supported_sections():
    parsed_json = {
        "skills": {
            "normalized": ["Python", "React"],
            "raw": ["FastAPI", "React"],
        },
        "technical_skills": ["Docker", "Kubernetes"],
        "technologies": "AWS, Terraform",
        "tools": [{"name": "Git"}, {"label": "Postman"}],
        "keywords": ["CI/CD"],
        "top_skills": [{"value": "Linux"}],
        "summary": {"top_skill_keywords": ["APIs", "python"]},
        "sections": [
            {"title": "Skills", "items": ["SQL", "Python"]},
            {"title": "Technologies", "items": [{"skill": "Redis"}]},
            {"title": "Projects", "items": ["Ignored"]},
        ],
        "experience": [
            {
                "technologies": ["Pandas", "NumPy"],
                "skills": [{"technology": "Airflow"}],
                "normalized_skills": ["ETL", "sql"],
            }
        ],
        "ats_tags": ["Communication", "docker"],
    }

    result = user_profile._extract_resume_skills(parsed_json)

    expected_skills = {
        "python",
        "react",
        "fastapi",
        "docker",
        "kubernetes",
        "aws",
        "terraform",
        "git",
        "postman",
        "ci/cd",
        "linux",
        "apis",
        "sql",
        "pandas",
        "numpy",
        "airflow",
        "etl",
        "communication",
    }

    assert set(result) == expected_skills
    assert len(result) == len(expected_skills)
    assert result.count("python") == 1
    assert result.count("react") == 1
    assert result.count("docker") == 1
    assert "redis" not in result
    assert "ignored" not in result

def test_coerce_strings_handles_none_string_list_and_dicts():
    assert user_profile._coerce_strings(None) == []
    assert user_profile._coerce_strings("Python, React , FastAPI") == [
        "Python",
        "React",
        "FastAPI",
    ]
    assert user_profile._coerce_strings(
        ["Docker", "  Git  ", "", {"name": "Postman"}, {"label": "Linux"}]
    ) == ["Docker", "Git", "Postman", "Linux"]


def test_coerce_strings_uses_first_supported_dict_key():
    result = user_profile._coerce_strings(
        [
            {"value": "Terraform"},
            {"skill": "Redis"},
            {"technology": "Kubernetes"},
            {"name": "AWS", "label": "ignored"},
            {"unknown": "ignored"},
        ]
    )

    assert result == ["Terraform", "Redis", "Kubernetes", "AWS"]


def test_normalize_string_list_returns_empty_for_non_list():
    assert user_profile._normalize_string_list(None) == []
    assert user_profile._normalize_string_list("junior") == []


def test_normalize_string_list_cleans_and_dedupes():
    result = user_profile._normalize_string_list(
        [" Junior ", "entry-level", "junior", "", 123, " Mid-Level "]
    )

    assert result == ["junior", "entry-level", "mid-level"]


def test_dedupe_normalized_strings_cleans_and_preserves_order():
    result = user_profile._dedupe_normalized_strings(
        [" Python ", "python", "  FastAPI  ", "", "PYTHON", "react"]
    )

    assert result == ["python", "fastapi", "react"]