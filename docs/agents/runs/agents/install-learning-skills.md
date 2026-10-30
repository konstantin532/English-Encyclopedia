# Установка найденных учебных навыков

## Цель и область

По прямому запросу автора установить найденные `language-learning` и
`skills-proficiency-mapper` для проекта, одинаково для Codex и Claude.
Учебный контент, приложение и production не меняются; merge делает автор.

База: `origin/main` = `f88bca0224ca24e49b2f16fb78083a0e5cb14572`.
Ветка: `agents/install-learning-skills`. При старте открыт PR #160 о регистрации;
его файлы не пересекаются с новым навыком. Проверки CI базы завершены успешно.

## Этапы

1. Проверить источники, лицензию и текущие навыки — выполнено.
2. Установить доступный навык в обе папки, проверить согласованность и тесты — выполнено; результаты ниже.
3. Создать коммит, отправить ветку и открыть PR для независимой проверки Claude.

## Источники и результат

- `language-learning`: `SkillMedev/skills`, путь `skills/language-learning`,
  коммит `97a13607d669157a4a16d5ba79b77f208319f7b9`. Прочитан весь SKILL.md,
  в папке нет скриптов; лицензия MIT сохранена. Использован системный установщик
  `skill-installer/scripts/install-skill-from-github.py` с точным `--ref`.
- Добавлены локальная область применения и происхождение. Общие рекомендации
  относятся к личному плану занятий; предметные требования курса приоритетны.
- `skills-proficiency-mapper`: **BLOCKED**. API репозитория
  `panaversity/agentfactory` и raw-путь `.claude/skills/skills-proficiency-mapper/SKILL.md`
  возвращают HTTP 404. Старое имя `panaversity/ai-native-software-development`
  также недоступно. Копия текста в каталоге ссылается на недоступную папку
  `reference`; вместо исходника она не устанавливалась.

## Допущения

Установка локальная для English Encyclopedia, а не глобальная. Независимое
подтверждение методических числовых советов upstream не выполнялось; этот навык
не закрывает проверку CEFR конкретных значений слов. Новые пакеты приложения
не требуются. Три ранее существовавших неотслеживаемых файла сохранены.

## Проверки

- `uv run python manage.py test tests.test_agent_setup tests.test_docs --settings=config.settings.test`
  — 44 tests, OK (1.580s).
- `uv run python manage.py test tests --parallel auto --settings=config.settings.test`
  — 1282 tests in 307.490s; FAILED (failures=2, skipped=8).
- Падают только `tests.test_phrase_memory.PhraseEntryLinkTests.test_link_hidden_when_disabled`
  и `tests.test_phrase_memory.RegisterHookTests.test_disabled_flag_writes_nothing`.
  Повтор этой пары с `--settings=config.settings.test --parallel 1` воспроизвёл оба падения.
  Оба disabled-теста не задают отключённое состояние `EE_PHRASE_MEMORY_ENABLED`;
  его также не фиксирует test.py, результат зависит от внешней конфигурации.
- Та же пара с явно отключённым `EE_PHRASE_MEMORY_ENABLED` только в тестовом
  процессе — 2 tests, OK (0.101s). Исходное окружение восстановлено, `.env` не менялся.
  Полный набор повторно не запускался; исходный полный прогон остаётся FAIL.
- `uv run python manage.py check` — System check identified no issues (0 silenced).
- `uv run python manage.py makemigrations --check --dry-run` — No changes detected.
- `uv run python scripts/skills_inventory.py --json` — language-learning найден
  в обеих папках, flags=[] для каждой.
- Независимая проверка: три файла в зеркалах побайтно одинаковы, hash оригинала
  совпадает с SOURCE.md, исходный текст и MIT-лицензия сохранены; P0–P2 нет.
- `git diff --exit-code f88bca0224ca24e49b2f16fb78083a0e5cb14572 -- apps config tests templates`
  — exit 0: код приложения и существующие тесты не изменены.

Проверка навыков и конфигурации — PASS. Полный Regression — FAIL с указанной
зависимостью двух тестов от настройки. Data Integrity, UX и Integration приложения
— N/A: код и данные не менялись. Security/Evidence ограничены прочитанными
текстовыми файлами, точным источником и выполненными командами.

BLOCKED: второй навык, фактическое использование нового навыка в свежем чате,
независимое подтверждение методических чисел upstream. Последнее не требуется
для копирования файлов и не заявляется выполненным.

## Следующий шаг

Независимая проверка Claude и решение автора по PR; второй навык остаётся
BLOCKED до появления доступного полного исходника. После создания PR он находится
по ветке `agents/install-learning-skills`; merge выполняет только автор.
