import os

import dj_database_url

from .base import *  # noqa: F401,F403

# Быстрый прогон — SQLite в памяти. CI дополнительно гоняет тесты на настоящем PostgreSQL
# (TEST_DATABASE_URL): блокировки select_for_update и ограничения ведут себя только там как в продакшене.
if os.getenv("TEST_DATABASE_URL"):
    DATABASES = {"default": dj_database_url.parse(os.environ["TEST_DATABASE_URL"])}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# Тесты содержимого открывают страницы курса без входа. Замок курса проверяют
# tests/test_course_access.py — там он включён явно (override_settings).
EE_COURSE_LOGIN_REQUIRED = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
