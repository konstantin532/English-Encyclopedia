from django.db import models

from .registry import SPHERES, global_week


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
    sphere = models.CharField(max_length=16, blank=True, choices=list(SPHERES.items()))
    situation_ru = models.CharField(max_length=160, blank=True)
    grammar_ru = models.CharField(max_length=200, blank=True)
    grammar_markers = models.JSONField(default=list, blank=True,
                                       help_text="Коды классов (D1) или категорий (D), обязательные в диалоге недели")

    class Meta:
        ordering = ["level__order", "number"]
        constraints = [models.UniqueConstraint(fields=["level", "number"], name="uniq_week_per_level")]

    def __str__(self) -> str:
        return f"{self.level.code} · неделя {self.number}"

    @property
    def global_number(self) -> int:
        return global_week(self.level.code, self.number)


class WeekScene(models.Model):
    """Ситуация недели: цель, диалог по ролям, готовые фразы, задание в жизнь."""

    week = models.OneToOneField(Week, on_delete=models.CASCADE, related_name="scene")
    can_do_ru = models.CharField(max_length=240)
    mission_ru = models.CharField(max_length=300)
    script = models.JSONField(default=list, blank=True, help_text="Реплики: speaker, text, emotion, ru, spoken")
    chunks = models.ManyToManyField("lexicon.LexicalUnit", blank=True, related_name="week_scenes")
    ambience = models.CharField(max_length=40, blank=True)
    audio = models.JSONField(default=dict, blank=True)
    story_beat = models.JSONField(default=dict, blank=True,
                                  help_text="Необязательная русская рамка: intro_ru, outcome_ru, next_hook_ru")

    class Meta:
        verbose_name = "сцена недели"
        verbose_name_plural = "сцены недель"

    def __str__(self) -> str:
        return f"Сцена: {self.week}"


class TongueTwister(models.Model):
    class Series(models.TextChoices):
        SOUNDS = "sounds", "Трудные звуки"
        CONTRACTIONS = "contractions", "Сокращения"
        CONNECTED = "connected", "Слияния в живой речи"
        FAST = "fast", "Быстрая речь"

    class Source(models.TextChoices):
        ORIGINAL = "original", "Своя"
        FOLK = "folk", "Народная (до 1929 года)"

    number = models.PositiveSmallIntegerField(unique=True, help_text="Номер недели в курсе, 1–150")
    week = models.OneToOneField(Week, on_delete=models.CASCADE, related_name="twister")
    series = models.CharField(max_length=16, choices=Series.choices)
    text = models.CharField(max_length=300)
    ipa = models.CharField(max_length=300, blank=True)
    ru = models.CharField(max_length=300, blank=True)
    focus_sounds = models.JSONField(default=list, blank=True)
    full_form = models.CharField(max_length=300, blank=True)
    source = models.CharField(max_length=8, choices=Source.choices)
    source_note = models.CharField(max_length=200, blank=True)
    audio = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "скороговорка"
        verbose_name_plural = "скороговорки"

    def __str__(self) -> str:
        return f"Скороговорка {self.number}"
