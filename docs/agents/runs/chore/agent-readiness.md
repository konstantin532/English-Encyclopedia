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

### Этап 2. Документация и процесс

- `.devcontainer/`: Python 3.13 (как `.python-version`), uv, Node 24, pnpm, PostgreSQL 16 для
  `TEST_DATABASE_URL`; установка — тот же `scripts/codex_cloud_setup.sh`, что в облаке Codex.
  Окружение uv вынесено из рабочей папки (`UV_PROJECT_ENVIRONMENT`), чтобы не смешивать `.venv` Windows и Linux.
- `.github/CODEOWNERS`, три шаблона задач, `.github/labels.json` + workflow `labels.yml` (через `gh label`,
  без сторонних действий), `dependabot.yml` (uv, npm, GitHub Actions).
- `.factory/hooks.json`: Droid вызывает тот же `guard.py`. Тест запускает `guard.py` с событием Droid
  (`tool_input.command` + `riskLevel`) → код 2 для `git reset --hard`, 0 для `git status`.
- Новый тест сразу нашёл ошибку YAML в шаблоне «Идея» (двоеточие в тексте) — исправлено.
- Проверки: `tests.test_agent_setup tests.test_tooling` → OK; pre-commit на новых файлах → Passed.

Следующий шаг: этап 3 — JSON-журналы, ID запроса, Sentry, `/metrics`; CodeQL и gitleaks уже написаны.

### Этап 3. Безопасность и наблюдаемость

- `codeql.yml` (Python и JavaScript, действие закреплено по SHA, v4.39.1) и `secret-scan.yml`
  (gitleaks 8.30.1 с проверкой SHA256 архива, тот же `.gitleaks.toml`).
- `apps/core/observability.py`: `RequestIDMiddleware` (принимает безопасный `X-Request-ID` или
  создаёт свой, возвращает в ответе), журнал строками JSON с ID запроса, счётчики запросов и времени
  ответа, `/metrics/` в формате Prometheus только с `Authorization: Bearer $METRICS_TOKEN` (без
  токена — 404, адрес не выдаёт себя), Sentry только при `SENTRY_DSN`, `send_default_pii=False`
  и `scrub_event` (вырезает cookies, заголовки авторизации, тело запроса, e-mail).
- `SENTRY_RELEASE` = SHA выкладки (`deploy/vps/update.sh`), переменные в `compose.yml` и примерах env.
- `posthog` добавлен в зависимости вместе с `sentry-sdk` (один `uv.lock`); используется на этапе 5.
- Проверки: `tests.test_observability` → OK; `ruff check .` → All checks passed; `mypy` → no issues
  in 141 files; быстрые тесты → 1292 tests, 244.8s, FAILED (failures=1):
  `test_nontrainer_audit.ConcurrencyAudit.test_two_domains` получил `[409, 409]` вместо `[200, 400]`.
  Отдельно 3 прогона подряд → OK. Тест гоняет два потока на одной SQLite и зависит от времени: под
  нагрузкой параллельного прогона оба запроса исчерпали повторы. Связи с этапом нет (middleware
  не трогает базу); считаю тест нестабильным, его проверит полный прогон и workflow этапа 4.

Следующий шаг: этап 4 — закоммитить поиск нестабильных тестов и метрики доставки.

### Этап 4. Нестабильные тесты и метрики поставки

- `flaky-tests.yml` (суббота): три прогона полного набора pytest в случайном порядке
  (`pytest-randomly==5.0.0` только в этом workflow), `scripts/flaky_report.py` сравнивает JUnit-отчёты;
  нестабильные тесты — в сводке и в задаче с меткой `flaky-test` (новая или комментарий в открытой).
- `delivery-metrics.yml` (понедельник): `scripts/delivery_metrics.py` — медиана и 90-й процентиль CI
  на PR, доля успешных, выкладки в неделю за 30 дней; только чтение API (`actions: read`).
- `deploy-vps.yml`: шаг «Mark release in Sentry» — отмечает выкладку SHA, без секретов `SENTRY_*`
  пропускается, ошибка Sentry выкладку не роняет.
- Проверки: `tests.test_delivery_tools tests.test_ci_workflows` → 11 tests, OK; `ruff check .` → All checks passed.

Следующий шаг: этап 5 — события PostHog в уроке и упражнениях, experiments, Droid review workflow.

### Этап 5. Аналитика, эксперименты, ревью Droid

- `apps/core/analytics.py`: серверный PostHog, только при `POSTHOG_KEY`. События `lesson_opened`
  (`lessons:detail`), `exercise_mistake` (проверенная ошибка, свободный ответ ошибкой не считается) и
  `lesson_completed` (первое верное решение, после которого решены все упражнения урока) в
  `api:check_exercise`. Имена событий и свойств проверяются и без ключа; без ключа `track_exercise`
  не делает запросов к базе. ID — HMAC-псевдоним, профили не создаются, GeoIP выключен.
- JS-скрипт PostHog в браузер не добавлен (в плане был): CSP и cookies не меняются, личных данных
  меньше. Записано в «Решения без автора».
- `apps/core/experiments.py`: флаг-пример `lesson-hint-style`, неизвестный вариант, сбой или нет ключа
  → значение по умолчанию.
- `droid-review.yml`: Factory-AI/droid-action по SHA (v13), автоматическое ревью и ревью безопасности
  на не-черновых PR, без секрета `FACTORY_API_KEY` — пропуск с пометкой; `persist-credentials: false`.
- Файл `apps/lessons/views.py` хранит смешанные окончания строк; правка сделана побайтно, чтобы diff
  был в 2 строки, а не переписал соседние.
- Проверки: `tests.test_analytics` → 8 tests OK; `tests.test_tooling tests.test_ci_workflows
  tests.test_analytics tests.test_agent_setup` → 67 tests OK; ruff check / format --check / mypy → чисто;
  быстрые тесты → 1307 tests, 369.0s, OK (skipped=8) — `test_two_domains` в этот раз прошёл.

Следующий шаг: финал — readiness.md, строка в AGENTS.md, полный прогон, push, PR.
