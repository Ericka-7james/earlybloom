from __future__ import annotations

from unittest.mock import Mock, patch

import requests

from app.services.providers.remoteok import (
    fetch_remoteok_jobs,
    get_remoteok_jobs,
    normalize_remoteok_job,
)


def test_fetch_remoteok_jobs_returns_jobs_and_skips_metadata_row() -> None:
    mock_response = Mock()
    mock_response.json.return_value = [
        {"legal": "metadata row"},
        {
            "id": 123,
            "position": "Frontend Engineer",
            "company": "Bloom Labs",
        },
        {
            "id": 456,
            "position": "Backend Engineer",
            "company": "Acme",
        },
    ]
    mock_response.raise_for_status.return_value = None

    with patch(
        "app.services.providers.remoteok.requests.get",
        return_value=mock_response,
    ) as mock_get:
        jobs = fetch_remoteok_jobs()

    assert len(jobs) == 2
    assert jobs[0]["id"] == 123
    assert jobs[1]["id"] == 456

    mock_get.assert_called_once_with(
        "https://remoteok.com/api",
        headers={"User-Agent": "EarlyBloom/1.0"},
        timeout=10,
    )


def test_fetch_remoteok_jobs_returns_empty_list_when_response_is_not_expected_shape() -> None:
    mock_response = Mock()
    mock_response.json.return_value = {"unexpected": "object"}
    mock_response.raise_for_status.return_value = None

    with patch(
        "app.services.providers.remoteok.requests.get",
        return_value=mock_response,
    ):
        jobs = fetch_remoteok_jobs()

    assert jobs == []


def test_fetch_remoteok_jobs_returns_empty_list_on_request_failure() -> None:
    with patch(
        "app.services.providers.remoteok.requests.get",
        side_effect=requests.RequestException("boom"),
    ):
        jobs = fetch_remoteok_jobs()

    assert jobs == []


def test_normalize_remoteok_job_returns_expected_shape() -> None:
    raw_job = {
        "id": 999,
        "position": "Full Stack Engineer",
        "company": "EarlyBloom",
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/999",
        "salary_min": 90000,
        "salary_max": 130000,
        "description": "Build product features across frontend and backend.",
        "date": "2026-03-29T12:00:00+00:00",
        "tags": ["React", "Python", "SQL"],
    }

    normalized = normalize_remoteok_job(raw_job)

    assert normalized == {
        "source": "remoteok",
        "external_id": 999,
        "title": "Full Stack Engineer",
        "company": "EarlyBloom",
        "location": "Worldwide",
        "remote_type": "remote",
        "url": "https://remoteok.com/remote-jobs/999",
        "salary_min": 90000,
        "salary_max": 130000,
        "currency": "USD",
        "description": "Build product features across frontend and backend.",
        "posted_at": "2026-03-29T12:00:00+00:00",
        "employment_type": None,
        "seniority_hint": None,
        "tags": ["React", "Python", "SQL"],
    }


def test_normalize_remoteok_job_handles_missing_or_invalid_salary() -> None:
    raw_job = {
        "id": 1000,
        "position": "Software Engineer",
        "company": "No Salary Inc",
        "location": "Remote",
        "url": "https://remoteok.com/remote-jobs/1000",
        "salary_min": "not-a-number",
        "salary_max": None,
        "description": "No salary provided.",
        "date": "2026-03-29T12:00:00+00:00",
        "tags": [],
    }

    normalized = normalize_remoteok_job(raw_job)

    assert normalized["salary_min"] is None
    assert normalized["salary_max"] is None
    assert normalized["currency"] is None
    assert normalized["remote_type"] == "remote"


def test_get_remoteok_jobs_fetches_and_normalizes_jobs() -> None:
    raw_jobs = [
        {
            "id": 1,
            "position": "Frontend Engineer",
            "company": "Alpha",
            "location": "Remote",
            "url": "https://remoteok.com/remote-jobs/1",
            "salary_min": 80000,
            "salary_max": 100000,
            "description": "Build UI",
            "date": "2026-03-29T12:00:00+00:00",
            "tags": ["React"],
        },
        {
            "id": 2,
            "position": "Backend Engineer",
            "company": "Beta",
            "location": "Anywhere",
            "url": "https://remoteok.com/remote-jobs/2",
            "salary_min": None,
            "salary_max": None,
            "description": "Build APIs",
            "date": "2026-03-29T13:00:00+00:00",
            "tags": ["Python"],
        },
    ]

    with patch(
        "app.services.providers.remoteok.fetch_remoteok_jobs",
        return_value=raw_jobs,
    ) as mock_fetch:
        jobs = get_remoteok_jobs()

    assert len(jobs) == 2
    assert jobs[0]["source"] == "remoteok"
    assert jobs[0]["external_id"] == 1
    assert jobs[1]["source"] == "remoteok"
    assert jobs[1]["external_id"] == 2

    mock_fetch.assert_called_once_with()