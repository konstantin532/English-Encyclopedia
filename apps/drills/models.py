from django.db import models

from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit


class Exercise(models.Model):
    class Kind(models.TextChoices):
        CHOICE = "choice", "Выбор ответа"
        FILL = "fill", "Вставить слово"
        BUILD = "build", "Собрать фразу"

    class Stage(models.TextChoices):
        RECOGNITION = "recognition", "Узнавание"
        SUBSTITUTION = "substitution", "Подстановка"
        PRODUCTION = "production", "Производство"
        TRANSFER = "transfer", "Перенос"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="exercises")
    order = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices)
    stage = models.CharField(max_length=14, choices=Stage.choices)
    prompt_ru = models.CharField(max_length=240)
    prompt_en = models.CharField(max_length=240, blank=True, help_text="Может содержать разметку и пропуск ___")
    options = models.JSONField(default=list, blank=True)
    answer = models.CharField(max_length=200, help_text="Для build — слова через пробел в верном порядке")
    accepted = models.JSONField(default=list, blank=True, help_text="Другие правильные варианты")
    hint_ru = models.CharField(max_length=240, blank=True)
    explanation_ru = models.TextField()
    units = models.ManyToManyField(LexicalUnit, blank=True, related_name="exercises")

    class Meta:
        ordering = ["lesson", "order"]
        constraints = [models.UniqueConstraint(fields=["lesson", "order"], name="uniq_exercise_order")]

    def __str__(self) -> str:
        return f"{self.lesson.slug} #{self.order}"

    @staticmethod
    def normalize(text: str) -> str:
        # Запятые не решают верность ответа: «Tea, please» = «Tea please».
        return " ".join(text.lower().replace("’", "'").replace(",", " ").strip(" .!?").split())

    def is_correct(self, given: str) -> bool:
        given_n = self.normalize(given)
        return any(given_n == self.normalize(a) for a in [self.answer, *self.accepted])
