"""
RemoteOK job provider.

Fetches and normalizes job listings from the RemoteOK public API.
Docs: https://remoteok.com/api

RemoteOk has been put on hold from production ingestion due to:
- Inconsistent data quality (e.g. missing salary info, messy descriptions).
- Frequent API changes that break our ingestion.
- Country-specific job listings that don't fit our US focus.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import requests

from app.core.config import get_settings


REMOTEOK_BASE_URL = os.getenv(
    "REMOTEOK_BASE_URL",
    "https://remoteok.com/api",
)


def fetch_remoteok_jobs() -> List[Dict[str, Any]]:
    """
    Fetch raw jobs from RemoteOK API.

    Returns:
        List of raw job objects.
    """
    settings = get_settings()

    try:
        response = requests.get(
            REMOTEOK_BASE_URL,
            headers={"User-Agent": "EarlyBloom/1.0"},
            timeout=settings.JOB_PROVIDER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()

        if isinstance(data, list) and len(data) > 1:
            # First row is commonly metadata.
            jobs = [item for item in data[1:] if isinstance(item, dict)]
            return jobs[: settings.JOB_PROVIDER_MAX_JOBS_PER_SOURCE]

        return []

    except requests.RequestException as e:
        print(f"[RemoteOK] fetch failed: {e}")
        return []


def normalize_remoteok_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single RemoteOK job into the internal EarlyBloom ingestion schema.
    """
    salary_min = _extract_salary_min(job)
    salary_max = _extract_salary_max(job)
    currency = "USD" if salary_min is not None or salary_max is not None else None

    raw_description = job.get("description")
    cleaned_description = _clean_remoteok_text(raw_description)

    location = _clean_remoteok_text(job.get("location")) or "Remote"
    title = _clean_remoteok_text(job.get("position"))
    company = _clean_remoteok_text(job.get("company"))

    tags = job.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    cleaned_tags = [
        _clean_remoteok_text(str(tag)).strip()
        for tag in tags
        if str(tag).strip()
    ]

    return {
        "source": "remoteok",
        "external_id": str(job.get("id") or ""),
        "title": title,
        "company": company,
        "location": location,
        "remote": True,
        "remote_type": "remote",
        "url": job.get("url"),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": currency,
        "description": cleaned_description,
        "posted_at": job.get("date"),
        "employment_type": None,
        "seniority_hint": None,
        "tags": cleaned_tags,
    }


def _extract_salary_min(job: Dict[str, Any]) -> int | None:
    try:
        return int(job.get("salary_min")) if job.get("salary_min") else None
    except (ValueError, TypeError):
        return None


def _extract_salary_max(job: Dict[str, Any]) -> int | None:
    try:
        return int(job.get("salary_max")) if job.get("salary_max") else None
    except (ValueError, TypeError):
        return None


def _clean_remoteok_text(value: Any) -> str:
    """
    Normalize RemoteOK text fields before they hit the shared cleaner.

    Handles common mojibake / encoding junk like:
    - Â
    - â
    - â¢
    - &nbsp;
    """
    text = str(value or "").strip()
    if not text:
        return ""

    replacements = {
        "\u00a0": " ",
        "&nbsp;": " ",
        "Â": "",
        "â": "'",
        "â": '"',
        "â": '"',
        "â": "-",
        "â": "-",
        "â¢": "•",
        "â¦": "...",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_remoteok_jobs() -> List[Dict[str, Any]]:
    """
    Fetch and normalize RemoteOK jobs.

    Returns:
        List of normalized jobs.
    """
    raw_jobs = fetch_remoteok_jobs()
    normalized_jobs: List[Dict[str, Any]] = []

    for job in raw_jobs:
        normalized_jobs.append(normalize_remoteok_job(job))

    return normalized_jobs