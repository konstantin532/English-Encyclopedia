# Agent Readiness: что настроено и как это поддерживать

Agent Readiness (Factory) — оценка того, насколько репозиторий готов к работе ИИ-агентов:
есть ли линтер, типы, тесты, сканеры, журналы, метрики и автоматическое ревью. Здесь — что
уже включено, где лежит и что включает автор. Журнал задачи: `docs/agents/runs/chore/agent-readiness.md`.

## Что включено

| Уровень | Что | Где |
|---|---|---|
| 2 | Линтер и форматтер ruff, типы mypy + django-stubs | `pyproject.toml`, `.github/workflows/lint.yml` |
| 2 | Долг старого кода только сокращается | `tests/test_tooling.py` (`FORMAT_LEGACY_MAX`, `MYPY_LEGACY_MAX`) |
| 2 | pre-commit: ruff, проверки YAML/TOML/JSON, окончания строк, gitleaks | `.pre-commit-config.yaml` |
| 2 | Среда разработки в контейнере (Python 3.13, Node, PostgreSQL 16) | `.devcontainer/` |
| 2 | Владелец кода, шаблоны задач, метки | `.github/CODEOWNERS`, `.github/ISSUE_TEMPLATE/`, `.github/labels.json` |
| 2 | Хуки Droid вызывают тот же `guard.py`, что у Codex и Claude | `.factory/hooks.json` |
| 3 | Обновления зависимостей | `.github/dependabot.yml` |
| 3 | Поиск секретов и уязвимостей в коде | `secret-scan.yml` (gitleaks), `codeql.yml` |
| 3 | Журнал строками JSON с ID запроса (`X-Request-ID`) | `apps/core/observability.py` |
| 3 | Ошибки и время ответа в Sentry | `SENTRY_DSN`, выключено по умолчанию |
| 3 | `/metrics/` для Prometheus | `METRICS_TOKEN`, без токена — 404 |
| 4 | Поиск нестабильных тестов (суббота, 3 прогона в случайном порядке) | `flaky-tests.yml`, `scripts/flaky_report.py` |
| 4 | Скорость CI и частота выкладок (понедельник) | `delivery-metrics.yml`, `scripts/delivery_metrics.py` |
| 4 | Отметка выкладки в Sentry | шаг в `deploy-vps.yml` |
| 5 | События урока в PostHog: открыт, пройден, ошибка | `apps/core/analytics.py`, `POSTHOG_KEY` |
| 5 | Эксперименты с безопасным значением по умолчанию | `apps/core/experiments.py` |
| 5 | Автоматическое ревью PR через Factory Droid | `droid-review.yml`, `FACTORY_API_KEY` |

## Личные данные (152-ФЗ)

Sentry и PostHog — внешние сервисы, а сервер в России. Поэтому:

- без `SENTRY_DSN` и `POSTHOG_KEY` ничего не отправляется;
- в Sentry не уходят cookies, заголовки авторизации, тело запроса и e-mail (`scrub_event`);
- в PostHog уходят только код урока, уровень, неделя, номер и тип упражнения; ID ученика —
  псевдоним (HMAC на `SECRET_KEY`), профили людей не создаются, IP не определяется;
- скрипт PostHog в браузер не загружается: CSP не меняется, сторонних cookies нет.

Перед включением любого из сервисов обновите политику конфиденциальности.

## Что делает автор

1. **GitHub → Settings → Branches:** правило для `main` — PR обязателен, проверки `test`, `postgres`,
   `lint` и `handoff` (workflow «PR handoff») должны пройти.
2. **Settings → Code security:** включить Secret scanning, Push protection, Dependabot alerts.
3. **Settings → Secrets and variables → Actions:** `FACTORY_API_KEY` (ревью Droid); по желанию
   `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` (отметка выкладок).
4. **На сервере** (`deploy/vps/.env`): по желанию `SENTRY_DSN`, `METRICS_TOKEN`, `POSTHOG_KEY`.
5. **Метки:** запустить workflow `Sync labels` один раз (дальше — сам при изменении `labels.json`).
6. **Перепроверка:** `/readiness-report` в Droid после слияния; раз в неделю — автоматизацией Factory
   с той же командой (Factory → Automations, расписание «каждый понедельник»).

## Как поддерживать

- Новый файл форматируется сразу (`uv run ruff format <файл>`); старый, исправленный целиком, убери из
  `[tool.ruff.format] exclude` и уменьши `FORMAT_LEGACY_MAX`.
- Новое событие аналитики — сначала в `EVENTS`, новое свойство — в `PROPERTIES`; иначе `capture`
  бросает ошибку и тесты падают.
- Новый эксперимент — в `FLAGS` с вариантами и значением по умолчанию, затем флаг с теми же
  вариантами в PostHog.
- Задача с меткой `flaky-test` — нестабильный тест: исправь причину, а не добавляй повтор.
