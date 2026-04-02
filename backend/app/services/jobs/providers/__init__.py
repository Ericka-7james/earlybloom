from __future__ import annotations

import logging

from app.services.jobs.providers.arbeitnow import ArbeitNowProvider
from app.services.jobs.providers.base import BaseJobProvider
from app.services.jobs.providers.jobicy import JobicyProvider
from app.services.jobs.providers.jsearch import JSearchProvider
from app.services.jobs.providers.remotive import RemotiveProvider
from app.services.jobs.providers.usajobs import USAJOBSProvider

logger = logging.getLogger(__name__)


def get_configured_providers() -> dict[str, BaseJobProvider]:
    """Return configured Layer 1 job providers.

    This registry is intentionally limited to trusted or relatively stable
    free-tier sources. Providers are instantiated behind env/settings toggles
    and omitted when they are disabled or not configured.

    Returns:
        Mapping of provider source names to provider instances.
    """
    providers: dict[str, BaseJobProvider] = {}

    for provider_cls in (
        USAJOBSProvider,
        RemotiveProvider,
        ArbeitNowProvider,
        JSearchProvider,
        JobicyProvider,
    ):
        try:
            provider = provider_cls.from_env()
        except Exception as exc:
            logger.exception(
                "Provider initialization failed for provider=%s",
                provider_cls.__name__,
                exc_info=exc,
            )
            continue

        if provider is None:
            continue

        providers[provider.source_name] = provider

    return providers


__all__ = [
    "ArbeitNowProvider",
    "BaseJobProvider",
    "JSearchProvider",
    "JobicyProvider",
    "RemotiveProvider",
    "USAJOBSProvider",
    "get_configured_providers",
]