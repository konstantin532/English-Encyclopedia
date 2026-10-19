from .base import *  # noqa: F401,F403
import os
from .base import SECRET_KEY, env_bool

DEBUG = False
# Free hosting has an ephemeral filesystem: learner progress MUST live in PostgreSQL.
if not os.getenv("DATABASE_URL") or DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise RuntimeError("Для продакшена необходим PostgreSQL DATABASE_URL (SQLite запрещён).")
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_hostname:
    if render_hostname not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(render_hostname)
    render_origin = "https://" + render_hostname
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
if SECRET_KEY.startswith("dev-only"):
    raise RuntimeError("Задайте DJANGO_SECRET_KEY для продакшена.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_CONTENT_TYPE_NOSNIFF = True
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
