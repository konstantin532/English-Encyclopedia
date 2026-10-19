#!/usr/bin/env bash
set -Eeuo pipefail
python -m pip install --disable-pip-version-check uv
uv sync --frozen --no-dev
# Pinned production server; explicitly installed into the locked app environment.
uv pip install --python .venv/bin/python 'gunicorn==23.0.0'
# Optional approved release artifact; fail closed on absent hash or invalid archive.
./.venv/bin/python deploy/install_audio_archive.py
./.venv/bin/python manage.py check
./.venv/bin/python manage.py collectstatic --noinput
