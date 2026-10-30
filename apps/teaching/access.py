"""Кто кого видит. Все проверки прав учителя — только здесь, чтобы их было легко проверить тестами."""
from functools import wraps

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet


def can_teach(user) -> bool:
    return bool(user.is_authenticated and user.is_active and (user.is_teacher or user.is_superuser))


def teacher_required(view):
    """Только для учителей и владельца. Остальным — 403, без подсказок о содержимом."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not can_teach(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def learners() -> QuerySet:
    """Ученики — не учителя, не команда и не владелец."""
    return get_user_model().objects.filter(is_active=True, is_teacher=False, is_staff=False, is_superuser=False)


def visible_students(user) -> QuerySet:
    """Ученики, которых этот учитель вправе видеть. Не учитель — никого."""
    if not can_teach(user):
        return learners().none()
    if user.is_superuser or user.teacher_sees_all:
        return learners()
    return learners().filter(group_membership__group__teacher=user)
