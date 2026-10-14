from django.core.validators import RegexValidator
from django.db import models

from apps.curriculum.models import Level, Week
from apps.taxonomy.models import PartOfSpeech, SemanticClass


class CEFR(models.TextChoices):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    UNVERIFIED = "unverified", "CEFR: требует проверки"


class Verification(models.TextChoices):
    PENDING = "pending", "Требует проверки"
    PARTIAL = "partial", "Частично подтверждено"
    VERIFIED = "verified", "Подтверждено источником"


class UnitType(models.TextChoices):
    WORD = "word", "Слово"
    PHRASE = "phrase", "Устойчивая фраза"
    COLLOCATION = "collocation", "Коллокация"
    PHRASAL_VERB = "phrasal_verb", "Фразовый глагол"
    IDIOM = "idiom", "Идиома"
    PATTERN = "pattern", "Речевой паттерн"


class LexicalUnit(models.Model):
    """Учебная единица корпуса: конкретное значение слова или выражения.

    Одна форма с двумя значениями — две записи. Повторное использование
    единицы в уроках не создаёт новую запись.
    """

    uid = models.CharField(
        max_length=12, unique=True,
        validators=[RegexValidator(r"^LX-\d{5}$", "ID формата LX-00001")],
        help_text="Постоянный идентификатор, не меняется никогда",
    )
    lemma = models.CharField(max_length=80, db_index=True)
    meaning = models.CharField(max_length=160, help_text="Конкретное значение (англ. толкование)")
    unit_type = models.CharField(max_length=16, choices=UnitType.choices, default=UnitType.WORD)
    part_of_speech = models.ForeignKey(PartOfSpeech, on_delete=models.PROTECT, related_name="units")
    semantic_class = models.ForeignKey(SemanticClass, on_delete=models.PROTECT, related_name="units")
    grammar_features = models.JSONField(default=list, blank=True, help_text="Напр. countable, irregular_plural")
    forms = models.JSONField(default=list, blank=True, help_text="Формы слова (am, is, are; has). Новыми единицами не считаются")
    cefr = models.CharField(max_length=10, choices=CEFR.choices, default=CEFR.UNVERIFIED)
    internal_level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name="units")
    week = models.ForeignKey(Week, on_delete=models.SET_NULL, null=True, blank=True, related_name="units")
    ipa_us = models.CharField(max_length=80, blank=True)
    stress_note = models.CharField(max_length=120, blank=True)
    translation_ru = models.CharField(max_length=160)
    frequency_source = models.CharField(max_length=120, blank=True)
    verification_status = models.CharField(max_length=10, choices=Verification.choices, default=Verification.PENDING)
    verification_note = models.CharField(max_length=240, blank=True)
    collocations = models.JSONField(default=list, blank=True)
    chunks = models.JSONField(default=list, blank=True)
    grammar_dependencies = models.JSONField(default=list, blank=True)
    example_en = models.CharField(max_length=240)
    example_ru = models.CharField(max_length=240, blank=True)
    pattern = models.CharField(max_length=160, blank=True)
    substitutions = models.JSONField(default=list, blank=True)
    situation = models.CharField(max_length=200, blank=True)
    typical_error = models.CharField(max_length=300, blank=True)
    usage_note = models.TextField(blank=True)
    search_text = models.CharField(max_length=600, blank=True, editable=False, db_index=True,
                                   help_text="Слово, формы и перевод в нижнем регистре — для поиска")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["uid"]
        constraints = [
            models.UniqueConstraint(fields=["lemma", "meaning", "part_of_speech"], name="uniq_sense"),
        ]
        indexes = [models.Index(fields=["internal_level", "part_of_speech"])]
        verbose_name = "лексическая единица"
        verbose_name_plural = "лексические единицы"

    def __str__(self) -> str:
        return f"{self.uid} {self.lemma}"

    def build_search_text(self) -> str:
        # casefold в Python: SQLite сам не понижает регистр кириллицы.
        return " ".join([self.lemma, *(self.forms or []), self.translation_ru]).casefold()[:600]

    def save(self, *args, **kwargs):
        self.search_text = self.build_search_text()
        super().save(*args, **kwargs)

    @property
    def markup_code(self) -> str:
        """Код для текстовой разметки, напр. S1."""
        return self.semantic_class.class_id
