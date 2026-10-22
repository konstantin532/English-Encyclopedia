#!/usr/bin/env bash
# Запуск сайта в контейнере: миграции, загрузка курса, затем Gunicorn.
set -Eeuo pipefail
cd /app
./.venv/bin/python manage.py migrate --noinput
# Правки, сделанные через админку, не затираются исходными YAML.
./.venv/bin/python manage.py load_content --preserve-admin-edits
exec ./.venv/bin/gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --access-logfile - --error-logfile - --timeout 60
