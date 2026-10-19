#!/usr/bin/env bash
set -Eeuo pipefail
# On a free instance there is no preDeployCommand. Fail closed if DB is absent.
./.venv/bin/python manage.py migrate --noinput
# Preserves human-admin changes; source-controlled lessons remain the initial seed.
./.venv/bin/python manage.py load_content --preserve-admin-edits
exec ./.venv/bin/gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --access-logfile - --error-logfile - --timeout 60
