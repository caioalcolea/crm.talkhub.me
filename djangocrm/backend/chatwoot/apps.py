from django.apps import AppConfig


class ChatwootConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatwoot"
    verbose_name = "Chatwoot Integration"

    # Registrado automaticamente pelo ConnectorRegistry.discover()
    connector_class = "chatwoot.connector.ChatwootConnector"

    def ready(self):
        from chatwoot.provider import ChatwootProvider
        from channels.registry import ChannelRegistry

        ChannelRegistry.register(ChatwootProvider)
