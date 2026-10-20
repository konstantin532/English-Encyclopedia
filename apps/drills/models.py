import re

from django.db import models

from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit


class ActiveExerciseManager(models.Manager):
    """Архивные упражнения скрыты от учеников, но их история ответов хранится."""

    def get_queryset(self):
        return super().get_queryset().filter(is_archived=False)


# Номер упражнения в архиве (10000 + pk): освобождает обычный номер для нового задания.
ARCHIVE_ORDER_BASE = 10000


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
    uid = models.CharField(max_length=12, unique=True, null=True, blank=True,
                           help_text="Постоянный ID (EX-00001): ответы учеников не «переезжают» при смене порядка")
    is_archived = models.BooleanField(default=False, help_text="Убрано из курса, но у учеников есть история по нему")

    objects = ActiveExerciseManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["lesson", "order"]
        base_manager_name = "all_objects"
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


# Пунктуация не влияет на диктант и перевод: «Hi, Tom!» = «hi tom».
PUNCTUATION = re.compile(r"[^\w\s']")
# Сокращение и полная форма равноправны: I'm = I am, isn't = is not.
# 's раскрывается только после местоимений и вопросительных слов:
# у существительных это может быть притяжательный падеж (Anna's).
CONTRACTION_FORMS = {
    "i'm": "i am", "you're": "you are", "we're": "we are", "they're": "they are",
    "it's": "it is", "he's": "he is", "she's": "she is", "that's": "that is",
    "what's": "what is", "where's": "where is", "who's": "who is", "there's": "there is",
    "here's": "here is", "how's": "how is",
    "isn't": "is not", "aren't": "are not", "don't": "do not", "doesn't": "does not",
    "can't": "can not", "cannot": "can not", "i'd": "i would", "you'd": "you would",
    "let's": "let us",
}


def loose_normalize(text: str) -> str:
    text = text.lower().replace("’", "'").replace("‘", "'")
    words = PUNCTUATION.sub(" ", text).split()
    out = []
    for word in words:
        word = word.strip("'")
        out.extend(CONTRACTION_FORMS.get(word, word).split())
    return " ".join(out)


class PracticeItem(models.Model):
    """Перевод с русского на английский: ученик сам строит фразу.

    Отдельно от шести основных заданий урока: их номера и банк отложенных
    повторений остаются прежними. Ответ сверяется со списком вариантов;
    несовпадение не считается доказанной ошибкой — перевод можно сказать иначе.
    """

    class Kind(models.TextChoices):
        TRANSLATE = "translate", "Перевод на английский"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="practice_items")
    order = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.TRANSLATE)
    prompt_ru = models.CharField(max_length=240)
    answer = models.CharField(max_length=200)
    accepted = models.JSONField(default=list, blank=True, help_text="Другие правильные варианты")
    hint_ru = models.CharField(max_length=240, blank=True)
    explanation_ru = models.TextField()
    review_of = models.PositiveSmallIntegerField(
        help_text="Номер основного задания урока, чьё отложенное повторение можно назначить")
    units = models.ManyToManyField(LexicalUnit, blank=True, related_name="practice_items")

    class Meta:
        ordering = ["lesson", "order"]
        constraints = [models.UniqueConstraint(fields=["lesson", "order"], name="uniq_practice_order")]

    def __str__(self) -> str:
        return f"{self.lesson.slug} перевод #{self.order}"

    def is_correct(self, given: str) -> bool:
        given_n = loose_normalize(given)
        return bool(given_n) and any(given_n == loose_normalize(a) for a in [self.answer, *self.accepted])
