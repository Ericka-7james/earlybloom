"""
USAJOBS job provider.

Fetches and normalizes job listings from the USAJOBS Search API.
USAJOBS requires Host, User-Agent, and Authorization-Key headers.
"""

from __future__ import annotations

import os
from typing import List, Dict, Any

import requests

from app.core.config import get_settings


USAJOBS_BASE_URL = os.getenv(
    "USAJOBS_BASE_URL",
    "https://data.usajobs.gov/api/search",
)


def fetch_usajobs_jobs() -> List[Dict[str, Any]]:
    """
    Fetch raw jobs from the USAJOBS API.

    Returns:
        List of USAJOBS SearchResultItems.
    """
    settings = get_settings()

    if not settings.USAJOBS_API_KEY or not settings.USAJOBS_USER_AGENT:
        print("[USAJOBS] missing API key or user agent")
        return []

    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": settings.USAJOBS_USER_AGENT,
        "Authorization-Key": settings.USAJOBS_API_KEY,
    }

    params = {
        "ResultsPerPage": settings.USAJOBS_RESULTS_PER_PAGE,
        "Page": 1,
    }

    if settings.USAJOBS_JOB_CATEGORY_CODE:
        params["JobCategoryCode"] = settings.USAJOBS_JOB_CATEGORY_CODE

    if settings.USAJOBS_POSITION_OFFER_TYPE_CODE:
        params["PositionOfferTypeCode"] = settings.USAJOBS_POSITION_OFFER_TYPE_CODE

    try:
        response = requests.get(
            USAJOBS_BASE_URL,
            headers=headers,
            params=params,
            timeout=settings.JOB_PROVIDER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"[USAJOBS] fetch failed: {e}")
        return []

    search_result = data.get("SearchResult", {})
    items = search_result.get("SearchResultItems", [])

    if not isinstance(items, list):
        return []

    return items[: settings.JOB_PROVIDER_MAX_JOBS_PER_SOURCE]


def normalize_usajobs_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single USAJOBS job into the internal EarlyBloom ingestion schema.
    """
    descriptor = job.get("MatchedObjectDescriptor", {})

    organization = descriptor.get("OrganizationName") or "USAJOBS"
    title = descriptor.get("PositionTitle")
    url = descriptor.get("PositionURI")

    locations = descriptor.get("PositionLocation", [])
    location_chunks: List[str] = []

    if isinstance(locations, list):
        for loc in locations:
            if not isinstance(loc, dict):
                continue

            city = loc.get("CityName")
            region = loc.get("CountrySubDivision") or loc.get("CountryCode")
            chunk = ", ".join(part for part in [city, region] if part)
            if chunk:
                location_chunks.append(chunk)

    location = ", ".join(dict.fromkeys(location_chunks))

    qualification_summary = descriptor.get("QualificationSummary")
    job_summary = descriptor.get("UserArea", {}).get("Details", {}).get("JobSummary")

    description_parts = [part for part in [job_summary, qualification_summary] if part]
    description = "\n\n".join(description_parts) if description_parts else None

    return {
        "source": "usajobs",
        "external_id": str(descriptor.get("PositionID") or url or ""),
        "title": title,
        "company": organization,
        "location": location,
        "remote_type": _infer_remote_type(descriptor, location),
        "url": url,
        "salary_min": _extract_salary_min(descriptor),
        "salary_max": _extract_salary_max(descriptor),
        "currency": _extract_currency(descriptor),
        "description": description,
        "posted_at": descriptor.get("PublicationStartDate"),
        "employment_type": _extract_employment_type(descriptor),
        "seniority_hint": None,
        "tags": _extract_tags(descriptor),
    }


def _infer_remote_type(descriptor: Dict[str, Any], location: str) -> str:
    """
    Infer remote classification from USAJOBS fields.
    """
    combined = " ".join(
        str(value or "")
        for value in [
            location,
            descriptor.get("PositionTitle"),
            descriptor.get("QualificationSummary"),
            descriptor.get("PositionSchedule"),
        ]
    ).lower()

    if "remote" in combined or "telework" in combined:
        return "remote"

    return "unknown"


def _extract_salary_min(descriptor: Dict[str, Any]) -> int | None:
    remuneration = descriptor.get("PositionRemuneration", [])
    if not remuneration or not isinstance(remuneration, list):
        return None

    value = remuneration[0].get("MinimumRange")
    try:
        return int(float(value)) if value is not None else None
    except (ValueError, TypeError):
        return None


def _extract_salary_max(descriptor: Dict[str, Any]) -> int | None:
    remuneration = descriptor.get("PositionRemuneration", [])
    if not remuneration or not isinstance(remuneration, list):
        return None

    value = remuneration[0].get("MaximumRange")
    try:
        return int(float(value)) if value is not None else None
    except (ValueError, TypeError):
        return None


def _extract_currency(descriptor: Dict[str, Any]) -> str | None:
    remuneration = descriptor.get("PositionRemuneration", [])
    if not remuneration or not isinstance(remuneration, list):
        return None

    return remuneration[0].get("RateIntervalCode") or "USD"


def _extract_employment_type(descriptor: Dict[str, Any]) -> str | None:
    schedules = descriptor.get("PositionSchedule", [])
    if isinstance(schedules, list) and schedules:
        first = schedules[0]
        if isinstance(first, dict):
            return first.get("Name")
        return str(first)
    return None


def _extract_tags(descriptor: Dict[str, Any]) -> List[str]:
    tags: List[str] = []

    series = descriptor.get("JobCategory", [])
    if isinstance(series, list):
        for item in series:
            if isinstance(item, dict) and item.get("Name"):
                tags.append(item["Name"])

    return tags


def get_usajobs_jobs() -> List[Dict[str, Any]]:
    """
    Fetch and normalize USAJOBS jobs.

    Returns:
        List of normalized jobs.
    """
    raw_jobs = fetch_usajobs_jobs()
    normalized_jobs: List[Dict[str, Any]] = []

    for job in raw_jobs:
        normalized_jobs.append(normalize_usajobs_job(job))

    return normalized_jobs