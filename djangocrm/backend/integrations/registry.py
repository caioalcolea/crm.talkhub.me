"""
ConnectorRegistry — Registro global de conectores de integração.

Populado automaticamente via Django app discovery no IntegrationsConfig.ready().
Apps que definem `connector_class` no seu AppConfig são registrados automaticamente.
"""

import logging

from django.apps import apps

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Registro global de conectores, populado via Django app discovery."""

    _connectors: dict[str, type] = {}

    @classmethod
    def register(cls, connector_class):
        """Registrar um conector. Valida interface obrigatória."""
        required_methods = [
            "connect",
            "disconnect",
            "sync",
            "get_status",
            "get_health",
            "get_config_schema",
            "handle_webhook",
        ]
        for method in required_methods:
            if not callable(getattr(connector_class, method, None)):
                raise TypeError(
                    f"{connector_class.__name__} missing required method: {method}"
                )

        slug = getattr(connector_class, "slug", None)
        if not slug:
            raise TypeError(f"{connector_class.__name__} missing required attribute: slug")

        cls._connectors[slug] = connector_class
        logger.info("Registered connector: %s (%s)", slug, connector_class.__name__)

    @classmethod
    def get(cls, slug: str):
        """Retornar classe do conector pelo slug, ou None."""
        return cls._connectors.get(slug)

    @classmethod
    def all(cls) -> dict[str, type]:
        """Retornar todos os conectores registrados."""
        return dict(cls._connectors)

    @classmethod
    def discover(cls):
        """Auto-discover conectores de apps instalados via Django app registry."""
        from django.utils.module_loading import import_string

        for app_config in apps.get_app_configs():
            connector_ref = getattr(app_config, "connector_class", None)
            if connector_ref is not None:
                try:
                    # Resolver string dotted path para classe real
                    if isinstance(connector_ref, str):
                        connector_class = import_string(connector_ref)
                    else:
                        connector_class = connector_ref
                    cls.register(connector_class)
                except (TypeError, ImportError) as e:
                    logger.error("Failed to register connector from %s: %s", app_config.name, e)
