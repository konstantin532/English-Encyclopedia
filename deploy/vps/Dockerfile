# Сайт English Encyclopedia для своего сервера (VPS). Сборка: см. docs/deploy/vps-moscow.md
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=config.settings.production

RUN pip install --no-cache-dir --disable-pip-version-check uv==0.8.22

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev && uv pip install --python .venv/bin/python 'gunicorn==23.0.0'

COPY . .

# Озвучка не хранится в git. Если в .env заданы адрес и хеш архива — ставим её при сборке,
# иначе сайт работает без звука (как на Render).
ARG A1_AUDIO_ARCHIVE_URL=""
ARG A1_AUDIO_ARCHIVE_SHA256=""
RUN A1_AUDIO_ARCHIVE_URL="$A1_AUDIO_ARCHIVE_URL" A1_AUDIO_ARCHIVE_SHA256="$A1_AUDIO_ARCHIVE_SHA256" \
    ./.venv/bin/python -m deploy.install_audio_archive

# collectstatic не нужна база: подставляем временные значения только на время сборки.
RUN DJANGO_SECRET_KEY=build-only-not-secret DATABASE_URL=postgresql://build:build@localhost/build \
    ./.venv/bin/python manage.py collectstatic --noinput --verbosity 0

RUN useradd --create-home --uid 1000 app && mkdir -p /app/media && chown -R app /app/media
USER app

EXPOSE 8000
ENTRYPOINT ["/app/deploy/vps/entrypoint.sh"]
