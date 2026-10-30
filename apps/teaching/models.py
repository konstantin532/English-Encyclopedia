"""Группы учеников. Учитель видит учеников своих групп (или всех, если так решил владелец)."""
import secrets

from django.conf import settings
from django.db import models

# Без похожих символов: 0/O, 1/I/L — код диктуют голосом и переписывают с экрана.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def new_join_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class StudyGroup(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                related_name="study_groups", verbose_name="учитель")
    name = models.CharField("название", max_length=80)
    join_code = models.CharField("код для входа в группу", max_length=CODE_LENGTH, unique=True,
                                 default=new_join_code)
    is_open = models.BooleanField("принимает новых учеников", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "группа"
        verbose_name_plural = "группы"
        ordering = ["name", "pk"]

    def __str__(self) -> str:
        return f"{self.name} · {self.teacher}"


class GroupMembership(models.Model):
    """Ученик состоит не больше чем в одной группе: так понятно, чей он ученик."""

    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="memberships",
                              verbose_name="группа")
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name="group_membership", verbose_name="ученик")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ученик в группе"
        verbose_name_plural = "ученики в группах"
        ordering = ["-joined_at"]

    def __str__(self) -> str:
        return f"{self.student} → {self.group.name}"


class CourseIssue(models.Model):
    """Сообщение об ошибке в материалах курса от ученика или учителя. Разбирает владелец."""

    class Status(models.TextChoices):
        OPEN = "open", "Новое"
        FIXED = "fixed", "Исправлено"
        REJECTED = "rejected", "Не ошибка"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="course_issues", verbose_name="кто сообщил")
    reporter_is_teacher = models.BooleanField("сообщил учитель", default=False)
    page = models.CharField("страница", max_length=300)
    quote = models.CharField("цитата с ошибкой", max_length=300, blank=True)
    comment = models.TextField("что не так", max_length=2000)
    status = models.CharField("статус", max_length=10, choices=Status.choices, default=Status.OPEN)
    owner_note = models.TextField("ответ владельца", blank=True)
    created_at = models.DateTimeField("когда", auto_now_add=True)
    resolved_at = models.DateTimeField("когда разобрано", null=True, blank=True)

    class Meta:
        verbose_name = "ошибка в курсе"
        verbose_name_plural = "ошибки в курсе"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"], name="course_issue_status_idx")]

    def __str__(self) -> str:
        return f"{self.page}: {self.comment[:60]}"


class ContentDraft(models.Model):
    """Черновик урока или истории от учителя. На сайт сам не попадает.

    Курс собирается из YAML-файлов репозитория (load_content). Одобренный
    черновик владелец или агент переносит в YAML по правилам курса: лексика,
    разметка, знакомые слова. Иначе следующая загрузка курса затёрла бы правки.
    """

    class Kind(models.TextChoices):
        LESSON = "lesson", "Урок"
        STORY = "story", "История"

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SUBMITTED = "submitted", "На проверке у автора курса"
        APPROVED = "approved", "Одобрено — будет перенесено в курс"
        REJECTED = "rejected", "Нужно доработать"

    EDITABLE = (Status.DRAFT, Status.REJECTED)

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                               related_name="content_drafts", verbose_name="автор")
    kind = models.CharField("что это", max_length=8, choices=Kind.choices, default=Kind.LESSON)
    level = models.CharField("уровень", max_length=8, default="A1")
    week = models.PositiveSmallIntegerField("неделя", null=True, blank=True)
    title = models.CharField("название", max_length=120)
    body = models.TextField("текст", max_length=20000,
                            help_text="Объяснение на русском и примеры на английском — как вы видите урок или историю.")
    status = models.CharField("статус", max_length=10, choices=Status.choices, default=Status.DRAFT)
    owner_note = models.TextField("ответ автора курса", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "черновик учителя"
        verbose_name_plural = "черновики учителей"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.title}"

    @property
    def editable(self) -> bool:
        return self.status in self.EDITABLE
