from __future__ import annotations

from unittest.mock import Mock, patch

import requests

from app.services.providers.arbeitnow import (
    _infer_remote_type,
    fetch_arbeitnow_jobs,
    get_arbeitnow_jobs,
    normalize_arbeitnow_job,
)


def test_fetch_arbeitnow_jobs_returns_data_on_success() -> None:
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {"slug": "job-1", "title": "Frontend Engineer"},
            {"slug": "job-2", "title": "Backend Engineer"},
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("app.services.providers.arbeitnow.requests.get", return_value=mock_response) as mock_get:
        jobs = fetch_arbeitnow_jobs(page=2, remote_only=False)

    assert len(jobs) == 2
    assert jobs[0]["slug"] == "job-1"
    assert jobs[1]["title"] == "Backend Engineer"

    mock_get.assert_called_once_with(
        "https://www.arbeitnow.com/api/job-board-api",
        params={"page": 2},
        timeout=10,
    )


def test_fetch_arbeitnow_jobs_includes_remote_param_when_requested() -> None:
    mock_response = Mock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status.return_value = None

    with patch("app.services.providers.arbeitnow.requests.get", return_value=mock_response) as mock_get:
        jobs = fetch_arbeitnow_jobs(page=1, remote_only=True)

    assert jobs == []

    mock_get.assert_called_once_with(
        "https://www.arbeitnow.com/api/job-board-api",
        params={"page": 1, "remote": "true"},
        timeout=10,
    )


def test_fetch_arbeitnow_jobs_returns_empty_list_on_request_failure() -> None:
    with patch(
        "app.services.providers.arbeitnow.requests.get",
        side_effect=requests.RequestException("boom"),
    ):
        jobs = fetch_arbeitnow_jobs()

    assert jobs == []


def test_normalize_arbeitnow_job_returns_expected_shape() -> None:
    raw_job = {
        "slug": "frontend-engineer-berlin",
        "title": "Frontend Engineer",
        "company_name": "Bloom Labs",
        "location": "Berlin / Remote",
        "url": "https://example.com/jobs/frontend-engineer",
        "description": "Build delightful UI experiences.",
        "created_at": 1712345678,
        "tags": ["React", "TypeScript", "CSS"],
    }

    normalized = normalize_arbeitnow_job(raw_job)

    assert normalized == {
        "source": "arbeitnow",
        "external_id": "frontend-engineer-berlin",
        "title": "Frontend Engineer",
        "company": "Bloom Labs",
        "location": "Berlin / Remote",
        "remote_type": "remote",
        "url": "https://example.com/jobs/frontend-engineer",
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "description": "Build delightful UI experiences.",
        "posted_at": 1712345678,
        "employment_type": None,
        "seniority_hint": None,
        "tags": ["React", "TypeScript", "CSS"],
    }


def test_infer_remote_type_returns_remote_when_location_mentions_remote() -> None:
    assert _infer_remote_type({"location": "Remote - Europe"}) == "remote"
    assert _infer_remote_type({"location": "Berlin / remote"}) == "remote"


def test_infer_remote_type_returns_unknown_when_not_remote() -> None:
    assert _infer_remote_type({"location": "Berlin, Germany"}) == "unknown"
    assert _infer_remote_type({"location": None}) == "unknown"
    assert _infer_remote_type({}) == "unknown"


def test_get_arbeitnow_jobs_fetches_and_normalizes_multiple_pages() -> None:
    page_1_jobs = [
        {
            "slug": "job-1",
            "title": "Frontend Engineer",
            "company_name": "Alpha",
            "location": "Remote",
            "url": "https://example.com/job-1",
            "description": "Job one",
            "created_at": 1710000001,
            "tags": ["React"],
        }
    ]
    page_2_jobs = [
        {
            "slug": "job-2",
            "title": "Backend Engineer",
            "company_name": "Beta",
            "location": "Berlin",
            "url": "https://example.com/job-2",
            "description": "Job two",
            "created_at": 1710000002,
            "tags": ["Python"],
        }
    ]

    with patch(
        "app.services.providers.arbeitnow.fetch_arbeitnow_jobs",
        side_effect=[page_1_jobs, page_2_jobs],
    ) as mock_fetch:
        jobs = get_arbeitnow_jobs(pages=2, remote_only=True)

    assert len(jobs) == 2
    assert jobs[0]["source"] == "arbeitnow"
    assert jobs[0]["external_id"] == "job-1"
    assert jobs[0]["remote_type"] == "remote"

    assert jobs[1]["source"] == "arbeitnow"
    assert jobs[1]["external_id"] == "job-2"
    assert jobs[1]["remote_type"] == "unknown"

    assert mock_fetch.call_count == 2
    mock_fetch.assert_any_call(page=1, remote_only=True)
    mock_fetch.assert_any_call(page=2, remote_only=True)