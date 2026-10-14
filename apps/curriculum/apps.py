from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync(sender, apps, **kwargs):
    from .registry import LEVELS

    Level = apps.get_model("curriculum", "Level")
    Week = apps.get_model("curriculum", "Week")
    for lv in LEVELS:
        level, _ = Level.objects.update_or_create(
            code=lv.code,
            defaults=dict(order=lv.order, block=lv.block, cefr_band=lv.cefr_band,
                          target_units=lv.new_units, weeks=lv.weeks, summary_ru=lv.summary_ru),
        )
        for n in range(1, lv.weeks + 1):
            Week.objects.get_or_create(level=level, number=n)


class CurriculumConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.curriculum"
    verbose_name = "Программа"

    def ready(self):
        post_migrate.connect(_sync, sender=self, dispatch_uid="curriculum_sync")
