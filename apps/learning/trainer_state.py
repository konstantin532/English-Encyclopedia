"""Shared atomic user gate for the trainer and existing lexical writers.

SQLite must acquire its write lock before reading state. PostgreSQL locks the
existing user row, including enrollment creation. No authentication value changes.
Retries encompass the entire caller operation, never a half-committed subservice.
"""
from functools import wraps
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import OperationalError, connection, transaction
from django.db.models import F


class TrainerUnavailable(Exception):
    status_code = 404
    canonical = None


class TrainerConflict(Exception):
    status_code = 409

    def __init__(self, message='Состояние изменилось. Продолжите с текущего шага.', *, canonical=None):
        super().__init__(message)
        self.canonical = canonical


class TrainerLimit(Exception):
    status_code = 429
    canonical = None


def enabled():
    return getattr(settings, 'EE_VOCABULARY_TRAINER_ENABLED', False)


def require_user(user):
    if not enabled() or not user.is_authenticated:
        raise TrainerUnavailable('Тренажёр сейчас недоступен.')


def run_serialized(user, operation):
    # Evaluate request.user's lazy authentication before starting a transaction:
    # SQLite read-then-write upgrades otherwise make concurrent locks brittle.
    authenticated = user.is_authenticated
    user_pk = user.pk if authenticated else None
    outer = connection.in_atomic_block
    attempts = 1 if outer else 8
    for retry in range(attempts):
        try:
            with transaction.atomic():
                if enabled() and authenticated:
                    users = get_user_model().objects.filter(pk=user_pk)
                    if connection.vendor == 'sqlite':
                        # A database-level lock across processes, not a Python mutex.
                        pk_name = get_user_model()._meta.pk.name
                        users.update(**{pk_name: F(pk_name)})
                    else:
                        users.select_for_update().get()
                return operation()
        except OperationalError as exc:
            lock_error = connection.vendor == 'sqlite' and any(
                word in str(exc).lower() for word in ('locked', 'busy'))
            if not lock_error or outer:
                raise
            if retry == attempts - 1:
                raise TrainerConflict('Данные заняты другим запросом. Повторите отправку.') from exc
            time.sleep(0.01 * (retry + 1))


def serialized(function):
    @wraps(function)
    def wrapper(user, *args, **kwargs):
        return run_serialized(user, lambda: function(user, *args, **kwargs))
    return wrapper


def trainer_mutation(function):
    @wraps(function)
    def wrapper(user, *args, **kwargs):
        require_user(user)
        return run_serialized(user, lambda: function(user, *args, **kwargs))
    return wrapper
