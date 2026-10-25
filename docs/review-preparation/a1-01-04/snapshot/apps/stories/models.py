from django.db import models

from apps.curriculum.models import Level, Week
from apps.lexicon.models import LexicalUnit


class Story(models.Model):
    """Одна из 60 историй (раздел 12). Номер постоянен; распределение по уровням — в curriculum.registry."""

    number = models.PositiveSmallIntegerField(unique=True)
    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name="stories")
    week = models.ForeignKey(Week, on_delete=models.SET_NULL, null=True, blank=True, related_name="stories")
    title = models.CharField(max_length=120)
    hook_ru = models.CharField(max_length=300, blank=True)
    focus = models.CharField(max_length=11, blank=True, help_text="Тренируемые категории, коды S D J…")
    characters = models.JSONField(default=list, blank=True)
    grammar_ru = models.CharField(max_length=240, blank=True)
    visual_cues = models.JSONField(default=list, blank=True, help_text="Описания двух иллюстраций для прогноза")
    prediction_ru = models.CharField(max_length=240, blank=True)
    body = models.TextField(blank=True, help_text="Текст с разметкой [S1]word[/]; при наличии script собирается из него")
    script = models.JSONField(default=list, blank=True, help_text="Реплики по ролям: [{speaker, kind, text}]")
    ambience = models.CharField(max_length=40, blank=True, help_text="Фон сцены, напр. morning_home")
    audio = models.JSONField(default=dict, blank=True, help_text="manifest.json озвучки: файлы, тайминги, голоса")
    questions = models.JSONField(default=list, blank=True, help_text="[{q, a}] от фактов к мотивам")
    phrase_hunt = models.JSONField(default=list, blank=True, help_text="[{phrase, function}]")
    retell_words = models.JSONField(default=list, blank=True)
    retell_steps = models.JSONField(default=list, blank=True)
    creative_ru = models.TextField(blank=True)
    new_units = models.ManyToManyField(LexicalUnit, blank=True, related_name="introduced_in_stories")
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["number"]
        constraints = [models.CheckConstraint(condition=models.Q(number__gte=1, number__lte=60), name="story_number_1_60")]

    def __str__(self) -> str:
        return f"История {self.number}. {self.title}"

    @property
    def focus_list(self) -> list[str]:
        return list(self.focus)
