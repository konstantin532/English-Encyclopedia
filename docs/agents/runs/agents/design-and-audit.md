# Применение design-and-audit.patch

Дата: 2026-10-31. Ветка: `agents/design-and-audit`.

## Цель

Применить предоставленные три коммита к актуальному main, удалить два исходных патча, выполнить указанные проверки и открыть PR без слияния.

## Исходное состояние

- Каталог: `F:/english-Encyclopedia`; исходная ветка `feat/week-motion-gsap`, SHA `67e6909524a26f9d5dc78abb5313617be27f1b36`.
- Отслеживаемые файлы не изменены. Файлы `audio-human-review.csv`, `git`, `update_after_pr147.bat` сохранены.
- После `git fetch origin` локальный main обновлён через `git merge --ff-only origin/main` до `17e6680adaa7b4c9ea0b4b8dfe2cda41e3d8bdc6`.

## Этапы и доказательства

1. Создана `agents/design-and-audit`; `git am design-and-audit.patch` применил все три коммита без конфликтов: `9cc7a724`, `2e12dedf`, `c6db861f`.
2. По прямому указанию автора удалены только `design-and-audit.patch` и `design-pipeline.patch`; они не отслеживались Git.
3. `uv run python manage.py test tests.test_agent_setup tests.test_docs`: Ran 44 tests in 1.461s; OK.
4. `uv run python manage.py test tests --exclude-tag slow --parallel auto`: Ran 1232 tests in 172.899s; FAILED (failures=2071, errors=5, skipped=8); exit 1. Число failures включает вложенные проверки (subtests).
5. `uv run python manage.py check`: System check identified no issues (0 silenced).
6. `uv run python manage.py makemigrations --check --dry-run`: No changes detected.
7. `git diff --check main...HEAD`: exit 0.
8. Независимый субагент прочитал патч, валидатор и тесты; существенных регрессий не подтвердил. Прямые вызовы валидатора подтвердили вложенные подзаголовки и исключение многострочных HTML-комментариев. Это не проверка Claude.

## Диагностика падений

- Два неизменённых теста `tests.test_content_and_learning.ContentTests.test_word_search_by_english_and_russian_respects_filters` и `tests.test_spoken.SpokenTests.test_spoken_variant_on_story_page` запущены вместе с `--parallel 2`: 2 tests, 2 failures (1.562s).
- Та же команда с `--settings=config.settings.test`: 2 tests, OK (1.674s).
- В Windows дочерние процессы запускаются заново и не наследуют присваивание `EE_COURSE_LOGIN_REQUIRED=False` из `ContentLoadedRunner.setup_test_environment`; модуль test.py задаёт флаг явно. Это подтверждает причину двух представительных сбоев, а не всех 2071 failures и 5 errors.
- `git diff main -- tests/runner.py config/settings/test.py config/settings/base.py config/settings/local.py manage.py apps/core/access.py tests/test_content_and_learning.py tests/test_spoken.py`: пустой diff. Патч не меняет этот механизм.
- Повтор всего набора с другими настройками не выполнялся; полный разбор остальных сбоев — BLOCKED в рамках применения патча. Исходный патч не расширяется исправлением тестового runner.

## Решения без автора и границы

- Быстрый прогон — команда из AGENTS.md с `--exclude-tag slow --parallel auto`; полный набор со slow не запрашивался и не запускается.
- Смысл предоставленного патча сохранён; дополнительный файл — только этот журнал по навыку long-run.
- Новая опись навыков охватывает явно перечисленные каталоги; `~/.codex/skills` и навыки плагинов в неё не входят.
- Навыки не выполнялись на реальном редизайне или аудите; браузерная проверка N/A, потому что интерфейс не меняется.
- GitHub connector недоступен, gh отсутствует; PR создаётся через GitHub API с существующим Git credential helper. Секрет не записывается и не выводится.

## Следующий шаг

Коммит журнала, проверка описания PR, отправка ветки и создание draft PR: быстрый набор остаётся FAIL. Слияние не выполнять.
