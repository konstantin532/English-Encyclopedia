from django.core.exceptions import ValidationError
from django.db import models

from apps.curriculum.models import Level, Week
from apps.lexicon.models import LexicalUnit
from apps.taxonomy.models import PartOfSpeech

LAYER_TITLES = {
    1: "Что это?",
    2: "Почему так называется?",
    3: "Как работает?",
    4: "Почему именно так?",
    5: "Как говорят американцы",
    6: "Исключения и нюансы",
    7: "Попробуйте сами",
}


class Lesson(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name="lessons")
    week = models.ForeignKey(Week, on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons")
    order = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=120)
    summary = models.CharField(max_length=240)
    focus = models.ForeignKey(PartOfSpeech, on_delete=models.PROTECT, null=True, blank=True, related_name="lessons")
    units = models.ManyToManyField(LexicalUnit, blank=True, related_name="lessons")
    minutes = models.PositiveSmallIntegerField(default=40)
    sound_notes = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["level__order", "order"]
        verbose_name = "урок"
        verbose_name_plural = "уроки"

    def __str__(self) -> str:
        return self.title


class LessonLayer(models.Model):
    """Один из семи слоёв объяснения (раздел 6 мастер-промпта)."""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="layers")
    number = models.PositiveSmallIntegerField(choices=[(k, f"{k}. {v}") for k, v in LAYER_TITLES.items()])
    body = models.TextField(help_text="Мини-формат: абзацы, «> » пример, «- » список, [S1]word[/] маркер")

    class Meta:
        ordering = ["lesson", "number"]
        constraints = [models.UniqueConstraint(fields=["lesson", "number"], name="uniq_layer_per_lesson")]

    @property
    def title(self) -> str:
        return LAYER_TITLES[self.number]

    def clean(self):
        from apps.taxonomy.markup import find_issues

        issues = find_issues(self.body)
        if issues:
            raise ValidationError("; ".join(f"{i.token}: {i.problem}" for i in issues))
