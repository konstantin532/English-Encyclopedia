from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync(sender, apps, **kwargs):
    from .sync import sync_registry

    sync_registry(apps.get_model("taxonomy", "PartOfSpeech"), apps.get_model("taxonomy", "SemanticClass"))


class TaxonomyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.taxonomy"
    verbose_name = "Реестр маркеров"

    def ready(self):
        post_migrate.connect(_sync, sender=self, dispatch_uid="taxonomy_sync")
