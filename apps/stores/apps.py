from django.apps import AppConfig


class StoresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stores"
    verbose_name = "Stores"

    def ready(self) -> None:
        """Connect signals when app is ready."""
        import apps.stores.signals  # noqa: F401
