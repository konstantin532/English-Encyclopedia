"""Retry complete learning POSTs without locking the authentication user table."""
from functools import wraps
import sqlite3
import time

from django.db import OperationalError, connection, transaction
from django.http import HttpResponse


def serialized_learning_post(view):
    """Retry SQLite lock conflicts from a fresh transaction; retain PG row locks."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)
        outer = connection.in_atomic_block
        attempts = 1 if outer else 8
        for retry in range(attempts):
            try:
                with transaction.atomic():
                    return view(request, *args, **kwargs)
            except OperationalError as exc:
                code = getattr(exc.__cause__, "sqlite_errorcode", None)
                lock_error = connection.vendor == "sqlite" and (
                    code is not None and (code & 0xff) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                )
                if not lock_error or outer:
                    raise
                if retry == attempts - 1:
                    return HttpResponse(
                        "Данные заняты другим запросом. Повторите отправку.",
                        status=409, content_type="text/plain; charset=utf-8",
                    )
                time.sleep(0.01 * (retry + 1))
    return wrapped
