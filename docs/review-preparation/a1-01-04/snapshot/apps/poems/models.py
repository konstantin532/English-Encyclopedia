from django.db import models

from apps.curriculum.models import Level, Week
from apps.lexicon.models import LexicalUnit


class Poem(models.Model):
    """Одно из 60 стихотворений (раздел 13): закрепляет известные слова и тренирует произношение."""

    number = models.PositiveSmallIntegerField(unique=True)
    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name="poems")
    week = models.ForeignKey(Week, on_delete=models.SET_NULL, null=True, blank=True, related_name="poems")
    title = models.CharField(max_length=120)
    rhyme_scheme = models.CharField(max_length=10, blank=True)
    theme_ru = models.CharField(max_length=240, blank=True)
    phonetic_goals = models.JSONField(default=list, blank=True)
    body = models.TextField(blank=True, help_text="Строки с разметкой [S1]word[/]")
    pronunciation = models.JSONField(default=list, blank=True, help_text="[{stress, ipa}] по строкам")
    gaps = models.JSONField(default=list, blank=True, help_text="[{line, word}] для упражнения с пропусками")
    target_units = models.ManyToManyField(LexicalUnit, blank=True, related_name="poems")
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["number"]
        constraints = [models.CheckConstraint(condition=models.Q(number__gte=1, number__lte=60), name="poem_number_1_60")]

    def __str__(self) -> str:
        return f"Стихотворение {self.number}. {self.title}"
