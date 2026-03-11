from django.apps import AppConfig


class ChannelsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "channels"
    label = "crm_channels"
    verbose_name = "Communication Channels"

    # Registrado automaticamente pelo ConnectorRegistry.discover()
    connector_class = "channels.connector.SMTPConnector"

    def ready(self):
        from channels.providers.smtp_native import SMTPNativeProvider
        from channels.registry import ChannelRegistry

        ChannelRegistry.discover()
        # Registrar provedor nativo SMTP (sempre disponível)
        ChannelRegistry.register(SMTPNativeProvider)
