# Agent Readiness: с уровня 1 до максимума

Дата: 2026-10-31. Ветка: chore/agent-readiness от origin/main a3629006.
План утверждён автором в сессии планирования (Factory Droid).

## Цель и «готово, когда…»

Закрыть критерии Agent Readiness Factory по уровням 1→5: линтер, форматтер, типы, pre-commit,
devcontainer, CODEOWNERS, шаблоны задач, поиск секретов, CodeQL, структурные журналы, трассировка,
метрики, поиск нестабильных тестов, аналитика и эксперименты, автоматическое ревью.
Готово, когда каждый этап закоммичен, быстрые тесты зелёные, полный прогон зелёный и PR оформлен
по шести разделам.

## Этапы

1. Уровень 1→2: ruff, mypy + django-stubs, workflow `lint`.
2. Уровень 2: pre-commit, devcontainer, CODEOWNERS, шаблоны задач, метки, `.factory/hooks.json`.
3. Уровень 3: dependabot, gitleaks, CodeQL, JSON-журналы, ID запроса, Sentry, `/metrics`.
4. Уровень 4: поиск нестабильных тестов, метрики CI и выкладок.
5. Уровень 5: PostHog, `apps/core/experiments.py`, ревью PR через Factory Droid.
6. Финал: `docs/agents/readiness.md`, строка в AGENTS.md, полный прогон, PR.

## Допущения

- Задача `lint` — отдельный workflow `lint.yml`: `tests/test_ci_workflows.py` требует, чтобы в `ci.yml`
  были ровно задачи `test` и `postgres`.
- `/healthz/` уже есть (`apps/core/views.py`), новый не нужен.
- Python в devcontainer — 3.13, как в `.python-version` и `deploy/vps/Dockerfile` (в плане было 3.12).

## Журнал

### Baseline

- `uv run python manage.py test tests --exclude-tag slow --parallel auto` (настройки по умолчанию) →
  1269 tests, FAILED (failures=762, errors=5): почти все — 302 на вход. `manage.py` берёт
  `config.settings.local`, а на Windows параллельные процессы не получают выключенный замок курса
  (`tests/runner.py` меняет настройку только в главном процессе). Это не дефект ветки; отдельная находка.
- С `--settings=config.settings.test` (как в прошлых журналах) → 1269 tests, 185.4s, OK (skipped=8).
  Дальше все прогоны — с этими настройками.

### Этап 1. Линтер, форматтер, типы

- Ruff: `select = E9, F, B006, B012, B018, W605` — синтаксис, неопределённые и неиспользуемые имена.
  Найдено 30: 19 неиспользуемых импортов (исправлено автоматически), 11 мёртвых переменных.
  Настоящих дефектов нет. Где присваивание неявно проверяло наличие ключа, поставлена явная проверка
  (`assertIn`), чтобы тест не ослаб.
- Формат: 282 старых файла в `[tool.ruff.format] exclude`, новые форматируются всегда.
- mypy + django-stubs: 38 ошибок в 15 модулях, все — пробелы типизации (проверены вручную).
  Модули в `[[tool.mypy.overrides]] ignore_errors`; `tests/test_tooling.py` не даёт спискам расти.
- `lint.yml` — отдельный workflow (ruff, формат, mypy, `pnpm check:css`) с кэшем uv и pnpm.
- pre-commit: ruff, ruff-format, check-yaml/toml/json, mixed-line-ending (`--fix=no`), gitleaks.
  `pre-commit run --files …` → все хуки Passed.
- gitleaks по всей истории: 194 ложных срабатывания (сторонние пакеты в `Lib/`, пароли тестовых
  пользователей, хеши в JSON аудитов). `.gitleaks.toml` с узкими исключениями → `no leaks found`.
- Проверки: `ruff check .` → All checks passed; `ruff format --check .` → 90 files already formatted;
  `mypy` → no issues in 138 files; быстрые тесты → 1274 tests, 315.9s, OK (skipped=8).

Следующий шаг: этап 2 — devcontainer, CODEOWNERS, шаблоны задач, метки, `.factory/hooks.json` + тест.
