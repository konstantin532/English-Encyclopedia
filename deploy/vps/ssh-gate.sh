#!/usr/bin/env bash
# Ключ GitHub Actions может выполнить на сервере ровно две команды: deploy и backup.
# setup.sh копирует этот файл в /usr/local/bin, чтобы правка в репозитории не расширяла доступ сама.
set -Eeuo pipefail
APP_DIR=/opt/english-encyclopedia
case "${SSH_ORIGINAL_COMMAND:-}" in
  deploy)
    exec "$APP_DIR/deploy/vps/update.sh" ;;
  backup)
    # Дамп базы в стандартный вывод; шифрует его уже GitHub Actions.
    exec docker compose -f "$APP_DIR/deploy/vps/compose.yml" exec -T db \
      pg_dump -U english -d english --format=custom --no-owner --no-privileges ;;
  *)
    echo "Команда не разрешена." >&2
    exit 1 ;;
esac
