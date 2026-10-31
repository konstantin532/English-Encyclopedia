"""Общие настройки English Encyclopedia.

База данных задаётся одной переменной DATABASE_URL.
Локально без неё используется SQLite, в продакшене — PostgreSQL на Supabase.
"""
import os
from pathlib import Path
from typing import Any

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

EE_VOCABULARY_TRAINER_ENABLED = env_bool("EE_VOCABULARY_TRAINER_ENABLED", False)
# Модуль «Память слов» и тренировка сгенерированных фраз. Выключен по умолчанию.
EE_PHRASE_MEMORY_ENABLED = env_bool("EE_PHRASE_MEMORY_ENABLED", False)
# Материалы курса только после входа (apps/core/access.py). На сайте всегда True.
# Выключается только в тестах содержимого страниц (tests/runner.py); сам замок
# проверяют tests/test_course_access.py с включённой настройкой.
EE_COURSE_LOGIN_REQUIRED = env_bool("EE_COURSE_LOGIN_REQUIRED", True)


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

PROJECT_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.teaching",
    "apps.taxonomy",
    "apps.lexicon",
    "apps.curriculum",
    "apps.lessons",
    "apps.stories",
    "apps.poems",
    "apps.drills",
    "apps.learning",
    "apps.publishing",
    "apps.api",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # WhiteNoise отдаёт статику и в разработке: поддерживает перемотку аудио (HTTP Range).
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "axes",
    *PROJECT_APPS,
]

MIDDLEWARE = [
    # ID запроса, журнал и счётчики — первыми, чтобы охватить всю обработку (apps/core/observability.py).
    "apps.core.observability.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Материалы курса — только после входа; открытые страницы в apps/core/access.py.
    "apps.core.access.CourseAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
                "apps.core.public_metadata.metadata",
            ],
        },
    },
]

# --- База данных -----------------------------------------------------------
# Supabase даёт два адреса: прямой (порт 5432) и пулер в режиме transaction
# (порт 6543). Для пулера отключаем серверные курсоры и подготовленные
# запросы: соединения в нём делятся между запросами.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=0, conn_health_checks=True)}
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault("sslmode", os.getenv("DATABASE_SSLMODE", "require"))
    if env_bool("DATABASE_USES_TRANSACTION_POOLER", True):
        DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
        DATABASES["default"]["OPTIONS"]["prepare_threshold"] = None

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Проверяем блокировку до дорогостоящего хеширования пароля.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5  # 30 минут
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
# LoginForm принимает email в стандартном поле AuthenticationForm "username".
AXES_USERNAME_FORM_FIELD = "username"
AXES_LOCKOUT_TEMPLATE = "accounts/lockout.html"

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "learning:dashboard"
LOGOUT_REDIRECT_URL = "core:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CONTENT_DIR = BASE_DIR / "content"

# Тесты: курс загружается в тестовую базу один раз (tests/runner.py).
TEST_RUNNER = "tests.runner.ContentLoadedRunner"

# Explicit public origin for canonical/social URLs; blank in local development.
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "")

# --- Наблюдаемость (apps/core/observability.py) ------------------------------
# На сервере журнал — строки JSON с ID запроса; локально с DJANGO_DEBUG — читаемый текст.
LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("DJANGO_LOG_FORMAT", "text" if DEBUG else "json")
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "apps.core.observability.RequestIDFilter"}},
    "formatters": {
        "json": {"()": "apps.core.observability.JsonFormatter"},
        "text": {"format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": LOG_FORMAT, "filters": ["request_id"]},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# /metrics/ для Prometheus: без токена адрес отвечает 404.
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")

# Ошибки и время ответа в Sentry — только если задан SENTRY_DSN. Без личных данных:
# сервис внешний, а сервер в России (152-ФЗ) — перед включением обновите политику конфиденциальности.
SENTRY_RELEASE = os.getenv("SENTRY_RELEASE", "")
from apps.core.observability import init_sentry  # noqa: E402

init_sentry(
    os.getenv("SENTRY_DSN", ""),
    environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
    release=SENTRY_RELEASE,
    traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
)
