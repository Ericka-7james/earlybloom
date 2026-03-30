# backend/app/services/providers/arbeitnow.py

"""
Arbeitnow job provider.

Fetches and normalizes job listings from the Arbeitnow public API.
Docs: https://www.arbeitnow.com/blog/job-board-api
"""

from __future__ import annotations

import os
import requests
from typing import List, Dict, Any, Optional


ARBEITNOW_BASE_URL = os.getenv(
    "ARBEITNOW_BASE_URL",
    "https://www.arbeitnow.com/api/job-board-api"
)


def fetch_arbeitnow_jobs(
    page: int = 1,
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch raw jobs from Arbeitnow API.

    Args:
        page: Pagination page number
        remote_only: Filter for remote jobs only

    Returns:
        List of raw job objects
    """
    params = {"page": page}

    if remote_only:
        params["remote"] = "true"

    try:
        response = requests.get(
            ARBEITNOW_BASE_URL,
            params=params,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("data", [])

    except requests.RequestException as e:
        # Fail gracefully, don’t crash ingestion
        print(f"[Arbeitnow] fetch failed: {e}")
        return []


def normalize_arbeitnow_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single Arbeitnow job into EarlyBloom schema.
    """

    return {
        "source": "arbeitnow",
        "external_id": job.get("slug"),

        "title": job.get("title"),
        "company": job.get("company_name"),
        "location": job.get("location"),

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
    Infer remote classification.
    """
    location = (job.get("location") or "").lower()

    if "remote" in location:
        return "remote"

    return "unknown"


def get_arbeitnow_jobs(
    pages: int = 1,
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch + normalize jobs across multiple pages.

    Args:
        pages: Number of pages to fetch
        remote_only: Whether to filter remote jobs

    Returns:
        List of normalized jobs
    """
    all_jobs: List[Dict[str, Any]] = []

    for page in range(1, pages + 1):
        raw_jobs = fetch_arbeitnow_jobs(
            page=page,
            remote_only=remote_only,
        )

        for job in raw_jobs:
            normalized = normalize_arbeitnow_job(job)
            all_jobs.append(normalized)

    return all_jobs