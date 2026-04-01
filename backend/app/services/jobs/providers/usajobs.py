"""USAJOBS job provider.

This module fetches and lightly normalizes job listings from the USAJOBS Search
API before they enter the shared EarlyBloom normalization pipeline.

Current strategy:
- Use USAJOBS as the primary and only live source
- Support pagination so the feed is not limited to a single page
- Preserve a focused first-round search configuration
- Produce a clean provider-specific shape for the shared normalizer
- Build sectioned descriptions so downstream parsing can extract structure more reliably

USAJOBS requires Host, User-Agent, and Authorization-Key headers.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List

import requests

from app.core.config import get_settings


USAJOBS_BASE_URL = os.getenv(
    "USAJOBS_BASE_URL",
    "https://data.usajobs.gov/api/search",
)


def fetch_usajobs_jobs() -> List[Dict[str, Any]]:
    """Fetch raw jobs from the USAJOBS Search API.

    This implementation supports paging so the provider can collect more than
    one page of job announcements when desired.

    Returns:
        A list of raw USAJOBS SearchResultItems.
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

    requested_results_per_page = getattr(settings, "USAJOBS_RESULTS_PER_PAGE", 50) or 50
    results_per_page = max(1, min(int(requested_results_per_page), 500))

    max_total_jobs = settings.JOB_PROVIDER_MAX_JOBS_PER_SOURCE
    if max_total_jobs <= 0:
        return []

    pages_to_fetch = max(1, (max_total_jobs + results_per_page - 1) // results_per_page)

    collected_items: List[Dict[str, Any]] = []

    for page in range(1, pages_to_fetch + 1):
        params: dict[str, Any] = {
            "ResultsPerPage": results_per_page,
            "Page": page,
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
        except requests.RequestException as exc:
            print(f"[USAJOBS] fetch failed on page {page}: {exc}")
            break

        search_result = data.get("SearchResult", {})
        items = search_result.get("SearchResultItems", [])

        if not isinstance(items, list) or not items:
            break

        collected_items.extend(item for item in items if isinstance(item, dict))

        if len(items) < results_per_page:
            break

        if len(collected_items) >= max_total_jobs:
            break

    collected_items = collected_items[:max_total_jobs]
    print(f"[USAJOBS] raw jobs fetched: {len(collected_items)}")
    return collected_items


def normalize_usajobs_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single USAJOBS item into the internal provider schema.

    The returned structure is intentionally lightweight. The shared normalizer
    performs the deeper cleaning, extraction, and filtering steps.

    Args:
        job: A USAJOBS SearchResultItem.

    Returns:
        A dictionary in the internal provider schema expected by the shared
        normalizer.
    """
    descriptor = job.get("MatchedObjectDescriptor", {})

    organization = (descriptor.get("OrganizationName") or "USAJOBS").strip()
    title = (descriptor.get("PositionTitle") or "").strip()
    url = (descriptor.get("PositionURI") or "").strip()

    location = _extract_location(descriptor)
    description = _build_description(descriptor)

    return {
        "source": "usajobs",
        "external_id": str(descriptor.get("PositionID") or url or ""),
        "title": title,
        "company": organization,
        "location": location,
        "remote": _infer_remote_flag(descriptor, location, description),
        "remote_type": _infer_remote_type(descriptor, location, description),
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


def _extract_location(descriptor: Dict[str, Any]) -> str:
    """Build a readable location string from USAJOBS location objects.

    Args:
        descriptor: USAJOBS matched object descriptor.

    Returns:
        A comma-separated location string.
    """
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

    if not location_chunks:
        position_location_display = descriptor.get("PositionLocationDisplay")
        if position_location_display:
            return str(position_location_display).strip()

    return ", ".join(dict.fromkeys(location_chunks))


def _build_description(descriptor: Dict[str, Any]) -> str | None:
    """Build a structured description from available USAJOBS fields.

    The goal is to preserve useful provider structure so downstream parsing can
    identify summaries, responsibilities, qualifications, and related sections
    more reliably.

    Args:
        descriptor: USAJOBS matched object descriptor.

    Returns:
        A sectioned description string, or None if nothing useful exists.
    """
    details = descriptor.get("UserArea", {}).get("Details", {})

    sections: list[str] = []

    _append_section(
        sections,
        "Job Summary",
        details.get("JobSummary"),
    )
    _append_section(
        sections,
        "Qualifications",
        descriptor.get("QualificationSummary"),
    )
    _append_section(
        sections,
        "Responsibilities",
        details.get("MajorDuties"),
    )
    _append_section(
        sections,
        "Education",
        details.get("Education"),
    )
    _append_section(
        sections,
        "How You Will Be Evaluated",
        details.get("Evaluations"),
    )
    _append_section(
        sections,
        "How To Apply",
        details.get("HowToApply"),
    )

    if not sections:
        return None

    return "\n\n".join(sections).strip()


def _append_section(sections: list[str], heading: str, content: Any) -> None:
    """Append a formatted section if content is present.

    Args:
        sections: Mutable list of rendered section strings.
        heading: Section heading.
        content: Raw content from USAJOBS.
    """
    rendered_body = _render_section_body(content)
    if not rendered_body:
        return

    section_text = f"{heading}:\n{rendered_body}".strip()
    if section_text not in sections:
        sections.append(section_text)


def _render_section_body(content: Any) -> str:
    """Render arbitrary USAJOBS content into readable section text.

    Args:
        content: Raw field content from USAJOBS.

    Returns:
        Rendered section body text.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return _normalize_paragraph_text(content)

    if isinstance(content, list):
        return _render_list_content(content)

    if isinstance(content, dict):
        values = []
        for value in content.values():
            rendered = _render_section_body(value)
            if rendered:
                values.append(rendered)
        return "\n".join(values).strip()

    return _normalize_paragraph_text(str(content))


def _render_list_content(items: Iterable[Any]) -> str:
    """Render list-like content as bullet points or paragraphs.

    Args:
        items: Sequence of list items.

    Returns:
        A bullet-formatted or paragraph-formatted string.
    """
    rendered_items: list[str] = []

    for item in items:
        rendered = _render_section_body(item)
        if not rendered:
            continue

        if "\n" in rendered:
            rendered = rendered.strip()

        rendered_items.append(rendered)

    if not rendered_items:
        return ""

    # If the items are short-ish and separate, use bullets. Otherwise preserve paragraphs.
    if all("\n" not in item and len(item) <= 500 for item in rendered_items):
        return "\n".join(f"- {item}" for item in rendered_items)

    return "\n\n".join(rendered_items)


def _normalize_paragraph_text(text: str) -> str:
    """Normalize paragraph-style provider text.

    Args:
        text: Raw text.

    Returns:
        Cleaned paragraph text with readable spacing preserved.
    """
    normalized = text.replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    return normalized.strip()


def _infer_remote_flag(
    descriptor: Dict[str, Any],
    location: str,
    description: str | None,
) -> bool:
    """Infer whether a USAJOBS role should be treated as remote.

    Args:
        descriptor: USAJOBS matched object descriptor.
        location: Normalized location string.
        description: Combined description text.

    Returns:
        True if the role appears remote or telework-based, otherwise False.
    """
    combined = " ".join(
        str(value or "")
        for value in [
            location,
            descriptor.get("PositionTitle"),
            descriptor.get("QualificationSummary"),
            description,
            descriptor.get("PositionSchedule"),
            descriptor.get("UserArea", {}).get("Details", {}).get("JobSummary"),
        ]
    ).lower()

    return "remote" in combined or "telework" in combined


def _infer_remote_type(
    descriptor: Dict[str, Any],
    location: str,
    description: str | None,
) -> str:
    """Infer remote classification from USAJOBS fields.

    Args:
        descriptor: USAJOBS matched object descriptor.
        location: Normalized location string.
        description: Combined description text.

    Returns:
        One of the coarse remote type labels used by the shared schema.
    """
    combined = " ".join(
        str(value or "")
        for value in [
            location,
            descriptor.get("PositionTitle"),
            descriptor.get("QualificationSummary"),
            description,
            descriptor.get("PositionSchedule"),
            descriptor.get("UserArea", {}).get("Details", {}).get("JobSummary"),
        ]
    ).lower()

    if "hybrid" in combined:
        return "hybrid"

    if "remote" in combined or "telework" in combined:
        return "remote"

    return "unknown"


def _extract_salary_min(descriptor: Dict[str, Any]) -> int | None:
    """Extract minimum salary from USAJOBS remuneration data.

    Args:
        descriptor: USAJOBS matched object descriptor.

    Returns:
        The minimum salary if parseable, otherwise None.
    """
    remuneration = descriptor.get("PositionRemuneration", [])
    if not remuneration or not isinstance(remuneration, list):
        return None

    value = remuneration[0].get("MinimumRange")
    try:
        return int(float(value)) if value is not None else None
    except (ValueError, TypeError):
        return None


def _extract_salary_max(descriptor: Dict[str, Any]) -> int | None:
    """Extract maximum salary from USAJOBS remuneration data.

    Args:
        descriptor: USAJOBS matched object descriptor.

    Returns:
        The maximum salary if parseable, otherwise None.
    """
    remuneration = descriptor.get("PositionRemuneration", [])
    if not remuneration or not isinstance(remuneration, list):
        return None

    value = remuneration[0].get("MaximumRange")
    try:
        return int(float(value)) if value is not None else None
    except (ValueError, TypeError):
        return None


def _extract_currency(descriptor: Dict[str, Any]) -> str | None:
    """Extract compensation currency code.

    USAJOBS often exposes rate interval codes rather than a pure currency code.
    For now, keep compatibility with the existing internal shape and default
    to USD when remuneration exists.

    Args:
        descriptor: USAJOBS matched object descriptor.

    Returns:
        A currency string or None.
    """
    remuneration = descriptor.get("PositionRemuneration", [])
    if not remuneration or not isinstance(remuneration, list):
        return None

    return "USD"


def _extract_employment_type(descriptor: Dict[str, Any]) -> str | None:
    """Extract employment type from the position schedule.

    Args:
        descriptor: USAJOBS matched object descriptor.

    Returns:
        A human-readable schedule label if available.
    """
    schedules = descriptor.get("PositionSchedule", [])
    if isinstance(schedules, list) and schedules:
        first = schedules[0]
        if isinstance(first, dict):
            return first.get("Name")
        return str(first)

    return None


def _extract_tags(descriptor: Dict[str, Any]) -> List[str]:
    """Extract useful category tags from USAJOBS fields.

    Args:
        descriptor: USAJOBS matched object descriptor.

    Returns:
        A list of category labels for downstream display or parsing.
    """
    tags: List[str] = []

    series = descriptor.get("JobCategory", [])
    if isinstance(series, list):
        for item in series:
            if isinstance(item, dict) and item.get("Name"):
                tags.append(str(item["Name"]).strip())

    hiring_paths = descriptor.get("UserArea", {}).get("Details", {}).get("HiringPath", [])
    if isinstance(hiring_paths, list):
        for item in hiring_paths:
            if isinstance(item, dict) and item.get("Name"):
                tags.append(str(item["Name"]).strip())

    deduped: List[str] = []
    seen: set[str] = set()
    for tag in tags:
        lowered = tag.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(tag)

    return deduped


def get_usajobs_jobs() -> List[Dict[str, Any]]:
    """Fetch and normalize USAJOBS jobs.

    Returns:
        A list of provider-normalized USAJOBS jobs.
    """
    raw_jobs = fetch_usajobs_jobs()
    normalized_jobs: List[Dict[str, Any]] = []

    for job in raw_jobs:
        normalized_jobs.append(normalize_usajobs_job(job))

    print(f"[USAJOBS] normalized jobs: {len(normalized_jobs)}")
    return normalized_jobs