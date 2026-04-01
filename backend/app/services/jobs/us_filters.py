"""U.S.-focused relevance helpers for job listings."""

from __future__ import annotations

from app.services.jobs.constants import (
    NON_US_LOCATION_KEYWORDS,
    REMOTE_KEYWORDS,
    US_STATE_CODES,
    US_STATE_NAMES,
)


def _safe_lower(value: str | None) -> str:
    return (value or "").strip().lower()


def looks_us_location(location: str | None) -> bool:
    """Return True when a location looks U.S.-based."""
    loc = _safe_lower(location)
    if not loc:
        return False

    if "united states" in loc or "u.s." in loc or "usa" in loc:
        return True

    for state in US_STATE_NAMES:
        if state in loc:
            return True

    parts = [part.strip(" ,") for part in loc.replace("/", " ").split()]
    for part in parts:
        if part.upper() in US_STATE_CODES:
            return True

    return False


def looks_non_us_location(location: str | None) -> bool:
    """Return True when a location clearly looks non-U.S."""
    loc = _safe_lower(location)
    if not loc:
        return False

    return any(keyword in loc for keyword in NON_US_LOCATION_KEYWORDS)


def is_us_remote_role(location: str | None, description: str | None, remote_flag: bool | None) -> bool:
    """Return True for likely U.S. remote roles."""
    loc = _safe_lower(location)
    desc = _safe_lower(description)

    remote_signals = any(keyword in loc or keyword in desc for keyword in REMOTE_KEYWORDS)
    us_signals = (
        "remote us" in loc
        or "remote - us" in loc
        or "remote, us" in loc
        or "united states" in loc
        or "u.s." in loc
        or "usa" in loc
        or "us only" in desc
        or "united states only" in desc
        or "must be based in the us" in desc
        or "must be authorized to work in the united states" in desc
    )

    return bool(remote_flag or remote_signals) and us_signals


def should_keep_us_focused_job(
    location: str | None,
    description: str | None,
    remote_flag: bool | None,
) -> bool:
    """Keep clearly U.S. jobs and U.S. remote roles, drop clearly non-U.S. jobs."""
    if looks_non_us_location(location) and not looks_us_location(location):
        return False

    if looks_us_location(location):
        return True

    if is_us_remote_role(location, description, remote_flag):
        return True

    loc = _safe_lower(location)
    if "remote" in loc and not looks_non_us_location(location):
        # Conservative keep for remote roles when location is vague but not clearly non-U.S.
        return True

    return False