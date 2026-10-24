from django.db import models

from . import registry


class PartOfSpeech(models.Model):
    """Одна из 11 учебных категорий визуальной схемы (не «ровно 11 частей речи»)."""

    code = models.CharField(max_length=1, unique=True)
    key = models.CharField(max_length=20, unique=True)
    name_ru = models.CharField(max_length=60)
    grammar_term_ru = models.CharField(max_length=80)
    marker = models.CharField(max_length=20, unique=True, choices=[(k, v[2]) for k, v in registry.MARKERS.items()])
    order = models.PositiveSmallIntegerField(unique=True)
    content_word = models.BooleanField(help_text="Знаменательная категория (маркер снизу)")

    class Meta:
        ordering = ["order"]
        verbose_name = "учебная категория"
        verbose_name_plural = "учебные категории"

    def __str__(self) -> str:
        return f"{self.key} ({self.code})"

    @property
    def marker_label(self) -> str:
        return registry.MARKERS[self.marker][2]


class SemanticClass(models.Model):
    """Тематический класс внутри категории. Цвет выводится из номера и не хранится отдельно."""

    category = models.ForeignKey(PartOfSpeech, on_delete=models.PROTECT, related_name="classes")
    number = models.PositiveSmallIntegerField()
    name_ru = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80)

    class Meta:
        ordering = ["category__order", "number"]
        constraints = [
            models.UniqueConstraint(fields=["category", "number"], name="uniq_class_number_per_category"),
            models.CheckConstraint(condition=models.Q(number__gte=1, number__lte=10), name="class_number_in_palette"),
        ]
        verbose_name = "класс"
        verbose_name_plural = "классы"

    def __str__(self) -> str:
        return f"{self.class_id} {self.name_ru}"

    @property
    def class_id(self) -> str:
        return registry.class_id(self.category.code, self.number)

    @property
    def color(self) -> str:
        return registry.color_for(self.number)

    @property
    def color_name(self) -> str:
        return registry.PALETTE[self.number][0]
