from __future__ import annotations

import importlib
import logging

from app.services.jobs.providers.base import BaseJobProvider

logger = logging.getLogger(__name__)

_PROVIDER_IMPORT_SPECS: tuple[tuple[str, str], ...] = (
    ("app.services.jobs.providers.usajobs", "USAJOBSProvider"),
    ("app.services.jobs.providers.greenhouse", "GreenhouseJobBoardProvider"),
    ("app.services.jobs.providers.jsearch", "JSearchProvider"),
    ("app.services.jobs.providers.remotive", "RemotiveProvider"),
    ("app.services.jobs.providers.jobicy", "JobicyProvider"),
    ("app.services.jobs.providers.arbeitnow", "ArbeitNowProvider"),
)


def _load_provider_class(
    module_path: str,
    class_name: str,
) -> type[BaseJobProvider] | None:
    """Import and return a provider class safely."""
    try:
        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)
    except Exception as exc:
        logger.exception(
            "Failed to import provider class. module=%s class=%s",
            module_path,
            class_name,
            exc_info=exc,
        )
        return None

    return provider_cls


def _get_provider_classes() -> list[type[BaseJobProvider]]:
    """Return provider classes in explicit priority order."""
    provider_classes: list[type[BaseJobProvider]] = []

    for module_path, class_name in _PROVIDER_IMPORT_SPECS:
        provider_cls = _load_provider_class(module_path, class_name)
        if provider_cls is not None:
            provider_classes.append(provider_cls)

    return provider_classes


def get_configured_providers() -> dict[str, BaseJobProvider]:
    """Return configured Layer 1 job providers.

    Layer 1 priorities:
    - Prefer U.S.-aligned and relatively stable sources first
    - Omit providers that are disabled or not configured
    - Keep provider trust/order explicit for debugging and staging quality
    """
    providers: dict[str, BaseJobProvider] = {}

    for provider_cls in _get_provider_classes():
        try:
            provider = provider_cls.from_env()
        except Exception as exc:
            logger.exception(
                "Provider initialization failed. provider_class=%s",
                provider_cls.__name__,
                exc_info=exc,
            )
            continue

        if provider is None:
            logger.info(
                "Provider not configured or disabled. provider_class=%s",
                provider_cls.__name__,
            )
            continue

        source_name = str(getattr(provider, "source_name", "") or "").strip()
        if not source_name:
            logger.warning(
                "Provider initialized without a usable source_name. provider_class=%s",
                provider_cls.__name__,
            )
            continue

        providers[source_name] = provider

        logger.info(
            "Provider initialized. provider_class=%s source_name=%s",
            provider_cls.__name__,
            source_name,
        )

    logger.info(
        "Configured job providers: %s",
        ", ".join(providers.keys()) if providers else "none",
    )

    return providers


__all__ = [
    "BaseJobProvider",
    "get_configured_providers",
]