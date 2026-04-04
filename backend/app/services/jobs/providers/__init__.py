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

    Layer 1 priorities:
    - Prefer U.S.-aligned and relatively stable sources first
    - Omit providers that are disabled or not configured
    - Keep provider trust/order explicit for debugging and staging quality
    """
    providers: dict[str, BaseJobProvider] = {}

    provider_classes: tuple[type[BaseJobProvider], ...] = (
        USAJOBSProvider,
        JSearchProvider,
        RemotiveProvider,
        JobicyProvider,
        ArbeitNowProvider,
    )

    for provider_cls in provider_classes:
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
            logger.info(
                "Provider not configured or disabled. provider=%s",
                provider_cls.__name__,
            )
            continue

        providers[provider.source_name] = provider

    logger.info(
        "Configured job providers: %s",
        ", ".join(providers.keys()) if providers else "none",
    )

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