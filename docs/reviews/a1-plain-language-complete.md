# A1: простыми словами — итог редакторского этапа

Ветка: `codex/a1-plain-language-week01-20261027`. Редакторская база: `341f2538`; первые два урока показаны отдельным diff в коммите `a5249633`, продолжение выполнено после ответа пользователя «Да». Основа включает отдельный неслитый коммит упрощения страницы урока. В main ничего не сливалось, push/PR не выполнялись.

Рабочая копия: `C:/Users/SystemX/Documents/Codex/2026-10-27/new-chat-4/work/English-Encyclopedia`. Исходная рабочая копия и база на F: не изменялись. Предпросмотр: http://localhost:8003/lessons/a1-nouns-first-words/ .

## Что изменено

- Проверены и отредактированы все 28 уроков A1. Дополнительные грамматические названия заменены объяснениями обычными словами; знакомые «существительное» и «глагол» остаются в последующих уроках как повторение.
- Убраны утечки T2/T3 и двойные точки. ASCII-многоточия заменены символом «…».
- Этимология и дополнительные значения перенесены в закрытые нативные блоки «Для любопытных». Содержание сохранено.
- Карточки ошибок используют конкретные неправильные фразы новичков: This is book, I from Russia, I am want, Go to straight, I like read, Why you like it, Do he like it.
- Всплывающие подписи цветных линий на страницах A1 теперь тоже объясняют роль слова простыми словами. Внутренний реестр, коды, классы, цвета и подписи других уровней сохранены.
- Старые тесты, буквально требовавшие слова «герундий», «подлежащее» и единственный details на слой, обновлены: они продолжают проверять смысловые различия, примеры и порядок вопроса перед разбором.

## Проверки

- PASS: 81 затронутый лёгкий тест, 8.895 с, без браузера и без создания тестовой БД. Полный набор тестов не запускался по просьбе пользователя.
- PASS: проверка реально отрендеренного текста всех 28 A1-уроков, включая закрываемый материал и data-label, который JavaScript показывает как подсказку: внутренних кодов и последовательностей ASCII-точек нет. A1/A2 как названия уровней и внутренние атрибуты data-cat/data-cls не считаются утечкой.
- PASS: блок «Для любопытных» закрыт по умолчанию и экранирует HTML. Подписи A1 сохраняют исходные слова, коды и цвета.
- PASS: сверка всех 28 YAML и карточек понимания с базой 341f2538. Лексические ID, номера слоёв, slug/order/focus, количество заданий и переводов, UID, ключи ответов, accepted/options, review_of, образцы произношения, IPA и проверяемые модели ответа сохранены. Новых английских токенов по каждому уроку с карточкой понимания: 0. Словарь, модели и миграции не менялись.
- PASS: безопасное обновление только текстовых полей отдельной preview-БД в транзакции, без удаления записей; ID и ответы упражнений, количество ответов пользователя и записей прогресса до/после совпадают. Общий load_content не запускался, поскольку его замена записей противоречит запрету пользователя на удаление данных.
- PASS: audit_course — ошибок нет. Остались прежние предупреждения о неполной сверке CEFR, повторении A1 в A1+ ниже цели и трёх опережающих словах; это не результат данного изменения.
- PASS: HTTP-проверка всех 28 URL в локальном предпросмотре — 200, финальный блок, закрытый дополнительный раздел и простые подписи присутствуют.
- PASS: git diff --check.
- Отдельная текстовая проверка представительных формулировок и 11 новых подписей другим агентом не выявила существенных лингвистических ошибок. Это не аудит полного курса и не доказательство эффективности обучения.

Команда тестирования (из корня рабочей копии):

```powershell
& F:/english-Encyclopedia/.venv/Scripts/python.exe manage.py test `
  tests.test_a1_learner_text `
  tests.test_a1_microsteps `
  tests.test_diagnostic_reveal `
  tests.test_a1_usage_clarity.A1UsageMetadataTests `
  tests.test_a1_independent_understanding.A1ClarityQualityGatesTests `
  tests.test_lesson_core_template `
  tests.test_a1_linguistic_integrity `
  tests.test_a1_pedagogical_continuity `
  tests.test_a1_second_pass `
  tests.test_a1_editorial_week01_02.A1FirstFourEditorialStaticTests `
  tests.test_a1_editorial_week03_04.FirstEightEditorialStaticTests `
  tests.test_a1_a1plus_semantic_regressions `
  tests.test_a1_editorial_week09_10.A1QuestionReviewGrammarTests `
  tests.test_a1_editorial_week11_12.A1HealthPostReviewTests `
  tests.test_a1_editorial_week13_14.A1FinalReviewTests `
  tests.test_a1_editorial_01_04.EditorialContractionSafetyTests `
  tests.test_a1_deep_25_28.FinalA1DeepGeneratedReview `
  tests.test_a1_corpus_alignment `
  tests.test_a1_final_transfer_integrity.FinalTransferContractTests `
  --settings=config.settings.test --testrunner=django.test.runner.DiscoverRunner
```

## Визуальная проверка: BLOCKED

Свежая проверка этой редакторской версии на desktop/375px и новые скриншоты не получены. IAB возвращает `Tab 4 is not part of browser session` / `Tab not found in browser 2`; резервный Computer Use не запускается: `failed to launch codex app-server: program not found`. HTTP-проверка не заменяет визуальную проверку.

Сохранённые ранее скриншоты относятся к отдельному этапу упрощения структуры урока, до текущей редактуры текста:

| Размер | До изменения структуры | После изменения структуры |
| --- | --- | --- |
| Desktop | [До](https://chatgpt.com/library?file_id=libfile_80eee209dadc8191887822d73a298ce6&account_id=personal) | [После](https://chatgpt.com/library?file_id=libfile_925f99e0634c8191a3f5732ec4953610&account_id=personal) |
| 375px | [До](https://chatgpt.com/library?file_id=libfile_48f4cdd5e88881919dc6acde17e97ae9&account_id=personal) | [После](https://chatgpt.com/library?file_id=libfile_86433f448a0081919ce82c9bd4acfa93&account_id=personal) |

## Статусы

| Проверка | Статус | Граница доказательства |
| --- | --- | --- |
| Correctness | PASS | Рендер текста и языковые регрессии |
| Regression | PASS | 81 затронутый лёгкий тест |
| Security | PASS | Экранирование HTML; авторизация не изменена |
| Data Integrity | PASS | Сравнение контента и отдельной preview-БД |
| UX | BLOCKED | Свежий браузерный просмотр недоступен |
| Integration | PASS локально | 28 URL; удалённый CI не запускался, PR не создавался |
| Evidence | PASS | Diff, тестовый лог, проверка инвариантов |

Следующее действие: после восстановления браузерного помощника проверить текущую версию на desktop и 375px. Интеграция в main требует отдельного прямого разрешения пользователя.

## Файлы текущей редактуры

- `apps/taxonomy/markup.py`
- `apps/taxonomy/templatetags/markers.py`
- `content/manifests/a1_understanding_checks.json`
- `content/seed_lessons/a1_w01_l01_nouns.yaml`
- `content/seed_lessons/a1_w01_l02_be.yaml`
- `content/seed_lessons/a1_w02_l03_determiners.yaml`
- `content/seed_lessons/a1_w02_l04_have_like_can.yaml`
- `content/seed_lessons/a1_w03_l05_cafe.yaml`
- `content/seed_lessons/a1_w03_l06_numbers.yaml`
- `content/seed_lessons/a1_w04_l07_family.yaml`
- `content/seed_lessons/a1_w04_l08_possession.yaml`
- `content/seed_lessons/a1_w05_l09_there_is.yaml`
- `content/seed_lessons/a1_w05_l10_how_much.yaml`
- `content/seed_lessons/a1_w06_l11_present_simple.yaml`
- `content/seed_lessons/a1_w06_l12_time.yaml`
- `content/seed_lessons/a1_w07_l13_he_works.yaml`
- `content/seed_lessons/a1_w07_l14_jobs.yaml`
- `content/seed_lessons/a1_w08_l15_where_is.yaml`
- `content/seed_lessons/a1_w08_l16_directions.yaml`
- `content/seed_lessons/a1_w09_l17_do_does.yaml`
- `content/seed_lessons/a1_w09_l18_spelling.yaml`
- `content/seed_lessons/a1_w10_l19_always_never.yaml`
- `content/seed_lessons/a1_w10_l20_like_doing.yaml`
- `content/seed_lessons/a1_w11_l21_what_hurts.yaml`
- `content/seed_lessons/a1_w11_l22_cant.yaml`
- `content/seed_lessons/a1_w12_l23_dont_doesnt.yaml`
- `content/seed_lessons/a1_w12_l24_address.yaml`
- `content/seed_lessons/a1_w13_l25_can_skills.yaml`
- `content/seed_lessons/a1_w13_l26_why_because.yaml`
- `content/seed_lessons/a1_w14_l27_bus.yaml`
- `content/seed_lessons/a1_w14_l28_review.yaml`
- `templates/components/drill.html`
- `templates/lessons/detail.html`
- `tests/test_a1_editorial_week01_02.py`
- `tests/test_a1_learner_text.py`
- `tests/test_a1_microsteps.py`
- `tests/test_a1_pedagogical_continuity.py`
- `tests/test_a1_second_pass.py`
- `tests/test_diagnostic_reveal.py`

Артефакты: `docs/reviews/a1-plain-language-complete.diff`, `docs/reviews/a1-plain-language-tests.txt`, этот отчёт; историческая заметка `a1-week01-checkpoint.md` дополнена ссылкой на продолжение.

## Все изменённые файлы кода, контента и тестов с начала двух задач

- `apps/taxonomy/markup.py`
- `apps/taxonomy/templatetags/markers.py`
- `content/manifests/a1_understanding_checks.json`
- `content/seed_lessons/a1_w01_l01_nouns.yaml`
- `content/seed_lessons/a1_w01_l02_be.yaml`
- `content/seed_lessons/a1_w02_l03_determiners.yaml`
- `content/seed_lessons/a1_w02_l04_have_like_can.yaml`
- `content/seed_lessons/a1_w03_l05_cafe.yaml`
- `content/seed_lessons/a1_w03_l06_numbers.yaml`
- `content/seed_lessons/a1_w04_l07_family.yaml`
- `content/seed_lessons/a1_w04_l08_possession.yaml`
- `content/seed_lessons/a1_w05_l09_there_is.yaml`
- `content/seed_lessons/a1_w05_l10_how_much.yaml`
- `content/seed_lessons/a1_w06_l11_present_simple.yaml`
- `content/seed_lessons/a1_w06_l12_time.yaml`
- `content/seed_lessons/a1_w07_l13_he_works.yaml`
- `content/seed_lessons/a1_w07_l14_jobs.yaml`
- `content/seed_lessons/a1_w08_l15_where_is.yaml`
- `content/seed_lessons/a1_w08_l16_directions.yaml`
- `content/seed_lessons/a1_w09_l17_do_does.yaml`
- `content/seed_lessons/a1_w09_l18_spelling.yaml`
- `content/seed_lessons/a1_w10_l19_always_never.yaml`
- `content/seed_lessons/a1_w10_l20_like_doing.yaml`
- `content/seed_lessons/a1_w11_l21_what_hurts.yaml`
- `content/seed_lessons/a1_w11_l22_cant.yaml`
- `content/seed_lessons/a1_w12_l23_dont_doesnt.yaml`
- `content/seed_lessons/a1_w12_l24_address.yaml`
- `content/seed_lessons/a1_w13_l25_can_skills.yaml`
- `content/seed_lessons/a1_w13_l26_why_because.yaml`
- `content/seed_lessons/a1_w14_l27_bus.yaml`
- `content/seed_lessons/a1_w14_l28_review.yaml`
- `static/css/lesson-core.css`
- `static/js/speech-studio.js`
- `static/scss/lesson-core.scss`
- `templates/components/drill.html`
- `templates/components/speech_studio_controls.html`
- `templates/lessons/detail.html`
- `tests/js/speech-studio.test.cjs`
- `tests/test_a1_editorial_week01_02.py`
- `tests/test_a1_learner_text.py`
- `tests/test_a1_microsteps.py`
- `tests/test_a1_pedagogical_continuity.py`
- `tests/test_a1_second_pass.py`
- `tests/test_diagnostic_reveal.py`
- `tests/test_lesson_core_template.py`
