# Применение agents-shared-rules.patch

Дата: 2026-10-30. Ветка: `agents/shared-rules`.

Цель: применить предоставленный патч от актуального main, выполнить проверки, открыть PR без слияния. Критерий завершения: оба коммита применены, .patch удалён, результаты и ограничения переданы в PR, четыре навыка обнаружены Codex.

## Этапы и результаты

1. `git fetch origin main`, обновление только fast-forward: main `0d7689d2f1f99f8a6a8d6868772880d634697a7c`, уже актуален. Создана `agents/shared-rules`. `git am agents-shared-rules.patch` применил оба коммита без конфликтов: `5475f9e3`, `ddc7b4dc`. Файл патча удалён, Git его не отслеживает.
2. Целевой прогон: сначала 26 тестов, один FAIL сравнения старых навыков. Все 95 различий оказались CRLF/LF; рабочие байты приведены к LF по существующему .gitattributes, хеши равны Git-индексу. После обновления служебных меток дерево индекса неизменно, содержательного diff нет. Повторный целевой прогон: 26 tests, OK.
3. Быстрый прогон `uv run python manage.py test tests --exclude-tag slow --parallel auto`: 1149 tests in 206.872s, FAILED (failures=3, skipped=8). Один сбой сравнения копий устранён локально. Два остальных воспроизведены на исходном main: 2 tests in 0.593s, FAILED (failures=2). Рабочая копия возвращена в тематическую ветку.
4. `uv run python manage.py check`: 0 issues. `uv run python manage.py makemigrations --check --dry-run`: No changes detected. Полный прогон один раз: `uv run python manage.py test tests --parallel auto`, 1199 tests in 419.175s, FAILED (failures=2, skipped=8). Остаются только два сбоя, подтверждённые на main.
5. `Codex app-server skills/list`, cwds проекта, forceReload=true: pr-review, long-run, course-content, ui-acceptance — все enabled=true, errors=[]. Буквальное меню $ визуально не проверено (BLOCKED: текущий чат вне проекта).
6. Независимый агент повторил `uv run python manage.py test tests.test_agent_setup.PullRequestHandoffTests tests.test_docs --verbosity 1`: 8 tests, OK. Воспроизведены два ограничения check_pr_handoff.py: вложенный подзаголовок даёт ложный отказ, многострочный HTML-комментарий — ложный успех. Две строки добавлены в журнал уроков; исправления кода вне предоставленного патча не внесены.

Старые сбои: tests.test_phrase_memory.PhraseEntryLinkTests.test_link_hidden_when_disabled; tests.test_phrase_memory.RegisterHookTests.test_disabled_flag_writes_nothing. Точная команда воспроизведения на main и финальные результаты записаны в описании PR.

## Решения без автора

Сохранить реализацию двух предоставленных коммитов. Дополнительно — только этот журнал и две строки lessons.md по новым правилам. Чужие неотслеживаемые файлы сохранены. Секреты не открывались. Глобальные настройки Git не менялись; доступ к F: выполнен через разрешённые операции вне изолированной среды. Открыть PR черновиком из-за двух старых сбоев и двух ограничений P2.

## Границы проверки

Облачный setup, буквальное меню $, итог CI и независимое ревью Claude — BLOCKED до фактической проверки. Страницы сайта, модели и учебные материалы патч не меняет. Correctness: FAIL (два ограничения валидатора); Regression: FAIL (два старых сбоя); Security: N/A для аудита runtime, проверки guard проходят; Data Integrity и UX: N/A; Integration: BLOCKED до CI; Evidence: PASS.

## Следующий шаг

Проверить PR ветки agents/shared-rules: публикуется сразу после этого журнала по шести разделам шаблона. Дождаться CI и независимого ревью Claude; отдельно решить два ограничения валидатора и старые сбои phrase_memory. Слияние в main выполняет только автор.
