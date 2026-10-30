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
