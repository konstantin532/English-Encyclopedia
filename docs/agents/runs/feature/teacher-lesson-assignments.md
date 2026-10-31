# Назначения уроков группам

Baseline: `a362900630ef42ffe8fbb0587ff0c7db66ac70d9`, ветка `feature/teacher-lesson-assignments`.
Источник требований: `docs/specs/2026-10-31-group-lesson-assignments.md`.
Готово, когда реализованы пять этапов, проверены права и экраны, подготовлен PR без слияния.
Учебный контент и существующие посторонние untracked-файлы не меняем.

## Этапы

1. Данные: завершён, коммит `bcb36a8a`. Профильные 42 теста прошли; migration check без изменений.
2. Правила и доступ: реализованы. RED: отсутствующий сервис, затем четыре воспроизведённых сбоя привязки/выхода. GREEN: 106 профильных тестов (`test_teaching_assignments`, `test_teaching`, `test_teacher_review`, `test_a1_teacher_review`, `test_a1_scaffold_variants`, `test_a1_independent_understanding`, `test_group_entry`), OK.
3. Кабинет ученика: реализован. 57 профильных тестов OK (`test_teaching_assignments`, `test_group_entry`, `test_a1_independent_understanding`, `test_teacher_review`). Карточки, POST открытия/завершения, отдельная история с отзывом; самостоятельный маршрут сохранён. Визуальная приёмка запланирована на этап 5.
4. Кабинет учителя: реализован. 61 профильный тест OK; `manage.py check` без ошибок. Форма своей группы/опубликованного урока, отдельные назначения и статусы текущих участников, очередь ревью и постраничные просрочки. Проверены чужая группа, CSRF, подмена контекста и глобальное разрешение.
5. Финальная проверка выполнена; PR готовится как черновик, полный набор не зелёный.
   - 115 профильных тестов OK; `makemigrations --check --dry-run` → No changes detected; `manage.py check` → no issues.
   - `node scripts/check_lesson_assignments.cjs` → PASS на отдельной временной SQLite: 375/390/768/1440 px, повторная выдача, оба источника завершения, ответ и отзыв, выход и история, Tab/Enter, reduced motion. Скриншоты просмотрены; горизонтальной прокрутки и ошибок JS нет.
   - Найденное браузером переполнение длинного select исправлено узким SCSS формы; проверка переполнения сохранена.
   - `pnpm check:css` → Stylesheets verified: 25. `pnpm test:ui` → 203 PASS после освобождения портов 8133/8134. Промежуточный запуск столкнулся с портами визуального сравнения, тесты не ослаблялись.
   - Контрольное Visual review с одинаковыми `EE_PHRASE_MEMORY_ENABLED=0`, `EE_VOCABULARY_TRAINER_ENABLED=0` завершено: 40 снимков, новых поломок нет. Артефакты `atlas-browser-evidence/assignments-comparison-equal-flags/`. Просмотрены пары на 390 px: новый блок внимания учителя и блок назначений ученика; небольшие отличия недель/истории находятся в загруженной длительности аудио, не в учебном тексте. Новые страницы формы/списка проверены отдельно. Первое сравнение с разными локальными флагами не используется как чистое доказательство.
   - Единственный полный прогон `uv run python manage.py test tests --parallel auto` завершился: Ran 1342 tests in 534.363s; FAILED (failures=762, errors=6, skipped=8). Вывод `C:\Users\SystemX\AppData\Local\Temp\droid-bg-1793445213472-578a5c26-efd1-4203-b2c1-1573752ca31c.out`. Повторно полный набор НЕ запускать.
   - Узкое воспроизведение: `tests.test_content_and_learning.ContentTests.test_word_search_by_english_and_russian_respects_filters` и `tests.test_spoken.SpokenTests.test_spoken_variant_on_story_page` с `--parallel 2` падают одинаково на baseline и в ветке (302 вместо 200 / пустой HTML). Без parallel оба проходят. Рабочая гипотеза: Windows spawn не получает изменение EE_COURSE_LOGIN_REQUIRED из setup_test_environment родительского процесса. Runner и защита курса не менялись.
   - `uv run python manage.py test tests.test_content_and_learning.ContentTests.test_word_search_by_english_and_russian_respects_filters tests.test_spoken.SpokenTests.test_spoken_variant_on_story_page tests.test_course_access tests.test_audio_distribution.AudioDistributionTests.test_render_build_installs_complete_audio_without_project_on_pythonpath` → Ran 16 tests, OK. Таймаут установки аудио из полного набора отдельно не воспроизвёлся. Все 768 сообщений полного набора не классифицированы; нельзя утверждать, что все они существовали на baseline.

## Решения без автора

- Самостоятельные посещения и ответы не привязываем к назначению автоматически.
- История сохраняется после выхода; повторное вступление не оживляет снятое назначение.
- Для назначенных ответов проверяем исходную группу и время выхода. Прежние правила видимости самостоятельных ответов и глобальное разрешение учителя сохранены.
- `withdrawn_at` сохраняем также для завершённых заданий: статус остаётся «Завершено», но после выхода изменение запрещено навсегда.
- Контекст ответа задаётся явным ID назначения с проверкой владельца, урока и членства на сервере; одноразовые токены формы разделены по назначениям. Подмена контекста не переносит ответы.
- Из-за неуспешного полного набора публикуем только draft PR. Не исправляем посторонний Windows test runner в ветке назначений и не повторяем полный набор вопреки ограничению автора.

## Ограничения

- `gh` отсутствует; для создания PR подготовлен API-скрипт.
- GitHub-коннектор не предлагается организацией; Git credential manager настроен. Подготовлен локальный, некоммитируемый `atlas-browser-evidence/create-assignment-pr.py` для разрешённого создания PR через API, без вывода или сохранения учётных данных.
- PostgreSQL-конкурентность в настоящем PostgreSQL пока не проверена (локальные тесты SQLite).
- Посторонние `audio-human-review.csv`, `git`, `update_after_pr147.bat` не включать.

## Следующий шаг

Проверить описание по шаблону, сохранить журнал коммитом и открыть draft PR без слияния. Перед переводом PR из черновика требуется отдельное решение по сбою полного набора: Windows runner и регрессии ещё не подтверждены целиком. Полный набор этой задачи уже запускался ровно один раз.
