#!/usr/bin/env bash
set -Eeuo pipefail
python -m pip install --disable-pip-version-check uv
uv sync --frozen --no-dev
# Pinned production server; explicitly installed into the locked app environment.
uv pip install --python .venv/bin/python 'gunicorn==23.0.0'
./.venv/bin/python manage.py check
./.venv/bin/python manage.py collectstatic --noinput
