"""
ChannelRegistry — Registro global de provedores de canal.

Populado automaticamente via Django app discovery no ChannelsConfig.ready().
Apps que definem `channel_provider_class` no seu AppConfig são registrados.
"""

import logging

from django.apps import apps

from channels.base import MessageCapability

logger = logging.getLogger(__name__)


class ChannelRegistry:
    """Registro global de provedores de canal."""

    _providers: dict[str, type] = {}

    @classmethod
    def register(cls, provider_class):
        """Registrar um provedor de canal."""
        channel_type = getattr(provider_class, "channel_type", None)
        if not channel_type:
            raise TypeError(f"{provider_class.__name__} missing required attribute: channel_type")

        cls._providers[channel_type.value if hasattr(channel_type, "value") else str(channel_type)] = provider_class
        logger.info("Registered channel provider: %s (%s)", channel_type, provider_class.__name__)

    @classmethod
    def get(cls, channel_type: str):
        """Retornar classe do provedor pelo channel_type, ou None."""
        return cls._providers.get(channel_type)

    @classmethod
    def all(cls) -> dict[str, type]:
        """Retornar todos os provedores registrados."""
        return dict(cls._providers)

    @classmethod
    def get_for_capability(cls, capability: MessageCapability) -> list[type]:
        """Retornar provedores que suportam uma capacidade específica."""
        result = []
        for provider_cls in cls._providers.values():
            try:
                if capability in provider_cls().get_capabilities():
                    result.append(provider_cls)
            except Exception:
                continue
        return result

    @classmethod
    def discover(cls):
        """Auto-discover provedores de canal de apps instalados."""
        from django.utils.module_loading import import_string

        for app_config in apps.get_app_configs():
            provider_ref = getattr(app_config, "channel_provider_class", None)
            if provider_ref is not None:
                try:
                    if isinstance(provider_ref, str):
                        provider_class = import_string(provider_ref)
                    else:
                        provider_class = provider_ref
                    cls.register(provider_class)
                except (TypeError, ImportError) as e:
                    logger.error("Failed to register channel provider from %s: %s", app_config.name, e)
