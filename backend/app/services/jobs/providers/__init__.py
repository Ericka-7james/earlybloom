"""Provider registry for job ingestion."""

from __future__ import annotations

from typing import Any, Awaitable, Callable


ProviderFetcher = Callable[[], Awaitable[list[dict[str, Any]]]]


def get_configured_providers() -> dict[str, ProviderFetcher]:
    """Return configured provider fetchers.

    Replace these imports with the actual provider modules/functions in your project.
    Keeping registration here makes future providers easy to add.
    """
    providers: dict[str, ProviderFetcher] = {}

    try:
        from app.services.providers.remotive import fetch_jobs as remotive_fetch_jobs
        providers["remotive"] = remotive_fetch_jobs
    except Exception:
        pass

    try:
        from app.services.providers.adzuna import fetch_jobs as adzuna_fetch_jobs
        providers["adzuna"] = adzuna_fetch_jobs
    except Exception:
        pass

    try:
        from app.services.providers.jsearch import fetch_jobs as jsearch_fetch_jobs
        providers["jsearch"] = jsearch_fetch_jobs
    except Exception:
        pass

    return providers