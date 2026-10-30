# Запуск: agents/project-agents

## Цель и критерий завершения

Применить предоставленный третий коммит с агентами после PR #156, проверить обнаружение трёх ролей, удалить пять названных временных файлов, запустить проверки и открыть PR без слияния.

## Исходная точка

- Репозиторий: F:\english-Encyclopedia.
- После первого обновления main: baa8db76e3d740cd8c20df4ec9415263d785426e, PR #156 слит.
- За время проверки main пополнился PR #155. Перед итоговыми проверками локальный main обновлён fast-forward до 46afcdab; неопубликованный коммит агентов перенесён поверх него без конфликта и без force push.
- Отслеживаемые файлы перед работой чистые. Исходные посторонние untracked-файлы не изменялись.

## Изменения

1. `git am agents-step3.patch` применился без конфликта. Исходный результат 97e69e13, после переноса на свежий main — 98f0eb41. Содержание восьми файлов исходного патча сохранено: 166 добавленных строк.
2. Удалены только agents-step3.patch, agents-shared-rules.patch, codex-skills.zip, .agents/skills/codex-skills.zip, .agents/skills/codex-skills-and-agents.zip. Файлы не добавлялись в Git; отсутствие всех пяти проверено.
3. Этот журнал добавлен по навыку long-run из main. Приложение, курс, зависимости и настройки разрешений не менялись.

## Проверки

| Проверка | Результат |
|---|---|
| `uv run python manage.py test tests.test_agent_setup tests.test_docs` | PASS: 30 tests, 0.185s, OK на итоговой базе. |
| `uv run python manage.py test tests --exclude-tag slow --parallel auto --settings=config.settings.test` | FAIL: 1214 tests, 166.098s; failures=2, skipped=8. |
| `uv run python manage.py test tests --parallel auto --settings=config.settings.test` | FAIL: 1264 tests, 298.771s; failures=2, skipped=8. Полный набор выполнен один раз. |
| Те же два phrase_memory-теста на main 46afcdab с `--settings=config.settings.test` | FAIL baseline: 2 tests, 0.104s, failures=2. |
| `uv run python manage.py check` | PASS: System check identified no issues (0 silenced). |
| `uv run python manage.py makemigrations --check --dry-run` | PASS: No changes detected. |
| `codex debug prompt-input`, cwd F:\english-Encyclopedia | PASS: exit 0; Codex 0.166.0-alpha.5.1 добавил reviewer, course_editor, ui_reviewer в фактическую схему spawn_agent.agent_type; описания совпали с TOML. Запросов к модели не было. |
| Независимое ревью и статический разбор шести TOML/YAML файлов | PASS: подтверждённых новых дефектов нет; состав, обязательные поля и навыки корректны. |
| `git diff --check main..HEAD` | PASS: без ошибок. |

Два сбоя: `tests.test_phrase_memory.PhraseEntryLinkTests.test_link_hidden_when_disabled` и `tests.test_phrase_memory.RegisterHookTests.test_disabled_flag_writes_nothing`. Они воспроизведены отдельно на свежем main; в этом шаге не исправлялись.

## Диагностика обычного запуска на Windows

Первый буквальный быстрый прогон без явных тестовых настроек на базе baa8db76: 1192 tests, 206.333s, failures=2068 (включая подслучаи), errors=5, skipped=8. Большинство ответов — 302 вместо 200.

Причина: tests/runner.py выключает EE_COURSE_LOGIN_REQUIRED в родительском процессе, а Windows spawn заново импортирует обычные настройки. В существующем config.settings.test этот флаг задан непосредственно в модуле, поэтому итоговые общие прогоны используют его. Проверка замка курса остаётся в tests/test_course_access.py с явным включением флага.

На main 46afcdab: `uv run python manage.py test tests.test_error_pages.ErrorPageTests tests.test_lesson_core_template.LessonCoreTemplateTests --parallel 2` — 12 tests, 1.679s, FAILED (errors=1), NoReverseMatch accounts из middleware доступа. Те же 12 тестов с `--settings=config.settings.test` — OK. Код настроек и тестового runner не изменялся.

## Ограничения и решения

- Регрессионный бар общего набора BLOCKED двумя предсуществующими сбоями; профильные проверки агентов пройдены.
- Реальные задачи каждой новой роли через модель и интерфейс Claude не запускались; обнаружение Codex проверено отдельно без генерации.
- «Не менять файлы» — инструкция роли. Bash разрешён, Codex наследует права родителя; отдельного технического запрета любых записей патч не добавляет.
- Новых находок патча, пропущенных тестами, нет; журнал lessons.md не расширялся.
- Открыть PR черновиком по шести разделам шаблона; main не сливать. Итог CI и ревью Claude ещё не получены.

## Следующий шаг

Опубликовать проверенный коммит и этот журнал в одном PR из agents/project-agents, затем передать Claude на независимую проверку. Решение о слиянии — только автор.
