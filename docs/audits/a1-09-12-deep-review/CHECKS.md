# Проверки checkpoint A1 9–12

author: Codex
reviewed_by: targeted automated regression; final full review pending
verification_status: technical_review
date: 2026-10-25
source_notes: exact local process metadata and complete copied logs in evidence/

Baseline `5826785ee3f665fac765783ba9a95a5dd3b52655`. Все перечисленные мутации базы выполнены с config.settings.test и явно заданными DATABASE_URL / TEST_DATABASE_URL на отдельных временных SQLite. Production не использовалась.

| Проверка | Точная команда | Результат | Wrapper seconds |
|---|---|---|---|
| 13 новых тестов, before | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_editorial_deep_09_12 --noinput` | FAIL: 25 failures, воспроизведение на исходнике (exit 1) | 11.882 |
| 13 новых тестов, after | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_editorial_deep_09_12 --noinput` | PASS: 13 tests; предшествует финальным текстовым уточнениям (exit 0) | 9.913 |
| Owned финальная граница | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_editorial_deep_09_12 tests.test_a1_editorial_week06 tests.test_grammar_answer_integrity tests.test_a1_pedagogical_continuity tests.test_a1_second_pass --noinput` | PASS: 34 targeted/related tests (exit 0) | 20.363 |
| 9 новых shared-тестов, before | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_deep_09_12_shared --noinput` | FAIL: 25 failures, воспроизведение на исходнике (exit 1) | 10.536 |
| 9 новых shared-тестов, after | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_deep_09_12_shared --noinput` | PASS: 9 tests (exit 0) | 11.414 |
| Первый интегрированный прогон | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_deep_09_12_shared tests.test_a1_editorial_deep_09_12 tests.test_a1_translation tests.test_a1_scaffold_variants tests.test_a1_microsteps tests.test_a1_independent_understanding --noinput` | FAIL: 84 tests, одна ошибочная старая проверка any water (exit 1) | 15.37 |
| Финальный интегрированный прогон | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_deep_09_12_shared tests.test_a1_editorial_deep_09_12 tests.test_a1_translation tests.test_a1_scaffold_variants tests.test_a1_microsteps tests.test_a1_independent_understanding --noinput` | PASS: 86 tests, 5.118s body (exit 0) | 14.116 |

Все полные `.log` расположены рядом с одноимёнными JSON. Два before/after набора используют одинаковые окончательные определения тестов; SHA в метаданных и STATUS.json. Ранние промежуточные сравнения не подменяют окончательное.

## Загрузка и аудит

| Проверка | Команда | Exit | Seconds |
|---|---|---|---|
| guard | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py shell -c from django.conf import settings;d=settings.DATABASES['default'];assert d['ENGINE']=='django.db.backends.sqlite3' and d['NAME']=='/tmp/ee-a1-09-12-shared-load-audit-xesvm7pv/fixture.sqlite3';print(d['ENGINE'],d['NAME'])` | 0 | 0.937 |
| migrate | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py migrate --noinput -v0` | 0 | 3.272 |
| load-content | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py load_content` | 0 | 11.49 |
| audit-course | `/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py audit_course` | 0 | 7.866 |

Guard проверил конкретный путь SQLite перед migrate. Load/audit — на финальном интегрированном источнике; audit «Ошибок нет», но общие предупреждения не скрыты.

## Исправленный старый тестовый контракт

Исходный test_fifth_pass_questions_match_speaker_and_situation требовал именно any water. Слово any не вводится в A1 week5; нейтральный вопрос Is there water? грамматически допустим. Старый assert требовал будущую лексику вместо проверки наличия + просьбы. FAIL84/1 сохранён, не переименован в PASS.

Заменена только ошибочная обязательность any: проверяется форма обычного вопроса, сохранено some water в просьбе. Новый отдельный behavioral тест проверяет actual loaded-guide model по словарю этой недели и отправляет вопрос+просьбу через blind independent endpoint; результат остаётся SELF_REPORTED без ложного UnitProgress. Отдельные тесты проверяют правильные и ошибочные цены, все микрокейсы, пять gap API, реальные HTML-классы и вступления. Это не отключение теста или изменение expected без подтверждённой причины. Полный diff старого контракта — OLD_TEST_CONTRACT.patch.

## Что ещё не пройдено

- Полный Django: NOT_RUN на этом пакете.
- Полный pytest: NOT_RUN на этом пакете.
- CSS/JS полный прогон: NOT_RUN на этом пакете.
- Desktop/390px/keyboard/reduced-motion: BLOCKED — доступного браузерного прогона не было.
- PostgreSQL: NOT_RUN.
- Настоящая озвучка: BLOCKED — реальное прослушивание не выполнялось.
- Пилот с людьми и повторная содержательная приёмка: NOT_RUN.

86 targeted PASS не заменяет полный прогон. Старые журналы GitHub Actions и результаты группы5–8 не засчитываются этому checkpoint.

## Следующий полный изолированный запуск

Из корня этой ветки:

```bash
python docs/audits/a1-09-12-deep-review/run_verification.py --output docs/audits/a1-09-12-deep-review/evidence/full --full-pytest
```

Скрипт создаёт новый временный каталог SQLite, очищает окружение до базовых системных переменных, переопределяет оба URL базы и config.settings.test, проверяет конкретный путь до миграций, устанавливает frozen lockfile dependencies. Затем выполняет check/collectstatic/makemigrations/migrate/load/audit/targeted/контракты/CSS/JS/аудиодиагностику/CEFR/fuzz/mutation, полный `uv run --frozen python manage.py test tests --parallel auto --noinput` и полный `uv run --frozen pytest -q -rfE`. Логи и exit codes сохраняются; первый FAIL останавливает последовательность. Это подготовленная команда, её запуск здесь не заявлен.

Перед ним можно проверить неизменность checkpoint:

```bash
uv run --frozen python docs/audits/a1-09-12-deep-review/verify_checkpoint.py
```

Наличие миграций в команде не означает изменений схемы: схема в этом пакете не менялась. Audio-readiness с exit0 будет только диагностикой, а не проверкой произношения.
