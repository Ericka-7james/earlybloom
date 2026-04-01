"""
Jobicy job provider.

Fetches and normalizes job listings from the Jobicy public remote jobs API.
"""

from __future__ import annotations

import os
from typing import List, Dict, Any

import requests

from app.core.config import get_settings


JOBICY_BASE_URL = os.getenv(
    "JOBICY_BASE_URL",
    "https://jobicy.com/api/v2/remote-jobs",
)


def fetch_jobicy_jobs(
    page: int = 1,
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch raw jobs from the Jobicy API.

    Args:
        page: Pagination page number.
        remote_only: Included for interface consistency. Jobicy is remote-focused.

    Returns:
        List of raw job objects.
    """
    settings = get_settings()
    params = {"page": page}

    try:
        response = requests.get(
            JOBICY_BASE_URL,
            params=params,
            timeout=settings.JOB_PROVIDER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"[Jobicy] fetch failed: {e}")
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        jobs = (
            data.get("jobs")
            or data.get("posts")
            or data.get("data")
            or []
        )
        return jobs if isinstance(jobs, list) else []

    return []


def normalize_jobicy_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single Jobicy job into the internal EarlyBloom ingestion schema.
    """
    title = job.get("jobTitle") or job.get("title") or job.get("name")
    company = job.get("companyName")

    company_obj = job.get("company")
    if not company and isinstance(company_obj, dict):
        company = company_obj.get("name")
    elif not company and isinstance(company_obj, str):
        company = company_obj

    location = (
        job.get("jobGeo")
        or job.get("location")
        or job.get("candidate_required_location")
        or "Remote"
    )

    description = (
        job.get("jobDescription")
        or job.get("description")
        or job.get("content")
    )

    url = job.get("url") or job.get("jobUrl") or job.get("link")

    return {
        "source": "jobicy",
        "external_id": str(job.get("id") or job.get("slug") or url or ""),
        "title": title,
        "company": company,
        "location": location,
        "remote_type": "remote",
        "url": url,
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "description": description,
        "posted_at": job.get("pubDate") or job.get("date") or job.get("published"),
        "employment_type": job.get("jobType") or None,
        "seniority_hint": None,
        "tags": job.get("jobTags", []) or job.get("tags", []),
    }


def get_jobicy_jobs(
    pages: int | None = None,
    remote_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch and normalize Jobicy jobs across multiple pages.

    Args:
        pages: Number of pages to fetch.
        remote_only: Included for interface consistency.

    Returns:
        List of normalized jobs.
    """
    settings = get_settings()
    effective_pages = pages or settings.JOB_PROVIDER_JOBICY_PAGES
    all_jobs: List[Dict[str, Any]] = []

    for page in range(1, effective_pages + 1):
        raw_jobs = fetch_jobicy_jobs(
            page=page,
            remote_only=remote_only,
        )

        if not raw_jobs:
            continue

        for job in raw_jobs:
            normalized = normalize_jobicy_job(job)
            all_jobs.append(normalized)

            if len(all_jobs) >= settings.JOB_PROVIDER_MAX_JOBS_PER_SOURCE:
                return all_jobs[: settings.JOB_PROVIDER_MAX_JOBS_PER_SOURCE]

    return all_jobs