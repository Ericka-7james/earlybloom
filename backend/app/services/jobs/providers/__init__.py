from __future__ import annotations

import logging

from app.services.jobs.providers.base import BaseJobProvider

logger = logging.getLogger(__name__)


def get_configured_providers() -> dict[str, BaseJobProvider]:
    """Return configured Layer 1 job providers.

    Layer 1 priorities:
    - Prefer U.S.-aligned and relatively stable sources first
    - Omit providers that are disabled or not configured
    - Keep provider trust/order explicit for debugging and staging quality
    """
    providers: dict[str, BaseJobProvider] = {}

    provider_classes: list[type[BaseJobProvider]] = []

    try:
        from app.services.jobs.providers.usajobs import USAJOBSProvider

        provider_classes.append(USAJOBSProvider)
    except Exception as exc:
        logger.exception("Failed to import USAJOBSProvider", exc_info=exc)

    try:
        from app.services.jobs.providers.greenhouse import GreenhouseJobBoardProvider

        provider_classes.append(GreenhouseJobBoardProvider)
    except Exception as exc:
        logger.exception("Failed to import GreenhouseJobBoardProvider", exc_info=exc)

    try:
        from app.services.jobs.providers.jsearch import JSearchProvider

        provider_classes.append(JSearchProvider)
    except Exception as exc:
        logger.exception("Failed to import JSearchProvider", exc_info=exc)

    try:
        from app.services.jobs.providers.remotive import RemotiveProvider

        provider_classes.append(RemotiveProvider)
    except Exception as exc:
        logger.exception("Failed to import RemotiveProvider", exc_info=exc)

    try:
        from app.services.jobs.providers.jobicy import JobicyProvider

        provider_classes.append(JobicyProvider)
    except Exception as exc:
        logger.exception("Failed to import JobicyProvider", exc_info=exc)

    try:
        from app.services.jobs.providers.arbeitnow import ArbeitNowProvider

        provider_classes.append(ArbeitNowProvider)
    except Exception as exc:
        logger.exception("Failed to import ArbeitNowProvider", exc_info=exc)

    for provider_cls in provider_classes:
        try:
            provider = provider_cls.from_env()

            logger.warning(
                "[provider-init] cls=%s provider=%s",
                provider_cls.__name__,
                getattr(provider, "source_name", None),
            )
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
    "BaseJobProvider",
    "get_configured_providers",
]