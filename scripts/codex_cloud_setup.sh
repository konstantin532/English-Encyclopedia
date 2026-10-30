#!/usr/bin/env bash
# Подготовка облачного окружения Codex для English Encyclopedia.
# В настройках окружения Codex вставь в поле установки одну строку:
#     bash scripts/codex_cloud_setup.sh
# Нужен доступ к менеджерам пакетов (пресет «Package managers»).
# Скрипт можно запускать повторно: он только доустанавливает недостающее.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --quiet --user uv || python3 -m pip install --quiet --break-system-packages uv
  export PATH="$HOME/.local/bin:$PATH"
fi
uv sync --frozen

if command -v npm >/dev/null 2>&1; then
  # Та же версия, что в CI; без самопереключения pnpm на другую версию.
  export npm_config_manage_package_manager_versions=false
  if [ "$(pnpm --version 2>/dev/null || true)" != "11.25.0" ]; then
    npm install --global pnpm@11.25.0
  fi
  pnpm install --frozen-lockfile --ignore-scripts
else
  echo "npm не найден: проверки CSS и UI (pnpm) в этом окружении будут BLOCKED." >&2
fi

uv run python manage.py check
echo "Окружение готово. Быстрые тесты: uv run python manage.py test tests --exclude-tag slow --parallel auto"
