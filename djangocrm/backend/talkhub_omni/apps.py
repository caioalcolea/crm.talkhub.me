from django.apps import AppConfig


class TalkhubOmniConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talkhub_omni"
    verbose_name = "TalkHub Omni Integration"

    # Registrado automaticamente pelo ConnectorRegistry.discover()
    connector_class = "talkhub_omni.connector.TalkHubOmniConnector"

    # Registrado automaticamente pelo ChannelRegistry.discover()
    channel_provider_class = "talkhub_omni.channel_provider.TalkHubOmniProvider"

    def ready(self):
        # Importar signals para ativar receivers
        import talkhub_omni.signals  # noqa: F401
