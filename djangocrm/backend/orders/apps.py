from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "orders"

    def ready(self):
        import orders.signals  # noqa: F401
