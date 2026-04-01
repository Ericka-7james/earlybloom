"""
Arbeitnow job provider.

Fetches and normalizes job listings from the Arbeitnow public API.
Docs: https://www.arbeitnow.com/blog/job-board-api
"""

from __future__ import annotations

import os
from typing import List, Dict, Any

import requests

from app.core.config import get_settings


ARBEITNOW_BASE_URL = os.getenv(
    "ARBEITNOW_BASE_URL",
    "https://www.arbeitnow.com/api/job-board-api",
)


def fetch_arbeitnow_jobs(
    page: int = 1,
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch raw jobs from Arbeitnow API.

    Args:
        page: Pagination page number.
        remote_only: Filter for remote jobs only.

    Returns:
        List of raw job objects.
    """
    settings = get_settings()
    params = {"page": page}

    if remote_only:
        params["remote"] = "true"

    try:
        response = requests.get(
            ARBEITNOW_BASE_URL,
            params=params,
            timeout=settings.JOB_PROVIDER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()
        jobs = data.get("data", [])
        return jobs if isinstance(jobs, list) else []

    except requests.RequestException as e:
        print(f"[Arbeitnow] fetch failed: {e}")
        return []


def normalize_arbeitnow_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single Arbeitnow job into the internal EarlyBloom ingestion schema.
    """
    return {
        "source": "arbeitnow",
        "external_id": job.get("slug") or str(job.get("id") or ""),
        "title": job.get("title"),
        "company": job.get("company_name"),
        "location": job.get("location") or "",
        "remote_type": _infer_remote_type(job),
        "url": job.get("url"),
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "description": job.get("description"),
        "posted_at": job.get("created_at"),
        "employment_type": None,
        "seniority_hint": None,
        "tags": job.get("tags", []),
    }


def _infer_remote_type(job: Dict[str, Any]) -> str:
    """
    Infer remote classification from Arbeitnow job fields.
    """
    location = (job.get("location") or "").lower()

    if "remote" in location:
        return "remote"

    return "unknown"


def get_arbeitnow_jobs(
    pages: int | None = None,
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch and normalize jobs across multiple pages.

    Args:
        pages: Number of pages to fetch.
        remote_only: Whether to filter remote jobs.

    Returns:
        List of normalized jobs.
    """
    settings = get_settings()
    effective_pages = pages or settings.JOB_PROVIDER_ARBEITNOW_PAGES
    all_jobs: List[Dict[str, Any]] = []

    for page in range(1, effective_pages + 1):
        raw_jobs = fetch_arbeitnow_jobs(
            page=page,
            remote_only=remote_only,
        )

        if not raw_jobs:
            continue

        for job in raw_jobs:
            normalized = normalize_arbeitnow_job(job)
            all_jobs.append(normalized)

            if len(all_jobs) >= settings.JOB_PROVIDER_MAX_JOBS_PER_SOURCE:
                return all_jobs[: settings.JOB_PROVIDER_MAX_JOBS_PER_SOURCE]

    return all_jobs