#!/usr/bin/env bash
# Обновить сайт на сервере до свежего main и перезапустить контейнеры.
# Запускается GitHub Actions по SSH (через ssh-gate) или вручную: sudo -u deploy /opt/english-encyclopedia/deploy/vps/update.sh
set -Eeuo pipefail
APP_DIR=${APP_DIR:-/opt/english-encyclopedia}
cd "$APP_DIR"
git fetch --quiet origin main
git reset --quiet --hard origin/main
echo "Версия: $(git log -1 --format='%h %s')"
compose=(docker compose -f deploy/vps/compose.yml)
"${compose[@]}" up -d --build --remove-orphans
# Ждём, пока сайт ответит на /healthz/ (до 5 минут: первая загрузка курса небыстрая).
for _ in $(seq 1 60); do
  status=$("${compose[@]}" ps --format '{{.Health}}' web 2>/dev/null || true)
  if [ "$status" = "healthy" ]; then echo "Сайт работает."; docker image prune -f >/dev/null; exit 0; fi
  sleep 5
done
echo "Сайт не ответил за 5 минут. Последние строки журнала:" >&2
"${compose[@]}" logs --tail 60 web >&2
exit 1
