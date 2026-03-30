from __future__ import annotations

from typing import List, Dict, Any

from app.core.config import settings
from app.services.providers.arbeitnow import get_arbeitnow_jobs
from app.services.providers.remoteok import get_remoteok_jobs


def get_mock_jobs() -> List[Dict[str, Any]]:
    return [
        {
            "source": "mock",
            "external_id": "mock-1",
            "title": "Frontend Engineer",
            "company": "EarlyBloom",
            "location": "Atlanta, GA",
            "remote_type": "hybrid",
            "url": "https://example.com/jobs/mock-1",
            "salary_min": 85000,
            "salary_max": 105000,
            "currency": "USD",
            "description": "Mock frontend job for local development.",
            "posted_at": None,
            "employment_type": "full-time",
            "seniority_hint": "entry-level",
            "tags": ["React", "JavaScript"],
        }
    ]


def get_live_jobs() -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []

    jobs.extend(get_arbeitnow_jobs(pages=1))
    jobs.extend(get_remoteok_jobs())

    return jobs


def get_jobs() -> List[Dict[str, Any]]:
    if settings.JOB_DATA_MODE == "live":
        return get_live_jobs()

    return get_mock_jobs()