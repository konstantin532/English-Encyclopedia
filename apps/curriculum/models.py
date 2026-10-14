from django.db import models


class Level(models.Model):
    code = models.CharField(max_length=4, unique=True)
    order = models.PositiveSmallIntegerField(unique=True)
    block = models.CharField(max_length=1, choices=[("A", "Блок A"), ("B", "Блок B")])
    cefr_band = models.CharField(max_length=40)
    target_units = models.PositiveIntegerField()
    weeks = models.PositiveSmallIntegerField()
    summary_ru = models.CharField(max_length=200)

    class Meta:
        ordering = ["order"]
        verbose_name = "уровень"
        verbose_name_plural = "уровни"

    def __str__(self) -> str:
        return self.code

    @property
    def slug(self) -> str:
        return self.code.lower().replace("+", "-plus")


class Week(models.Model):
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="week_set")
    number = models.PositiveSmallIntegerField(help_text="Номер недели внутри уровня")
    theme_ru = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["level__order", "number"]
        constraints = [models.UniqueConstraint(fields=["level", "number"], name="uniq_week_per_level")]

    def __str__(self) -> str:
        return f"{self.level.code} · неделя {self.number}"
