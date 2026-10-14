from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from .db_security import enable_rls_on_public_tables

        post_migrate.connect(enable_rls_on_public_tables, dispatch_uid="core_enable_rls")
