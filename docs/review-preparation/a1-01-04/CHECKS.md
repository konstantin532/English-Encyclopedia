# CHECKS — новые запуски и прежний CI отдельно

Исходный учебный snapshot: `8d3a41d9aa61cbf074caff602d53b22920ca3efa`.

Ни production, ни удалённая база сайта не использовались. Новая SQLite: `/tmp/ee-preparation-test-6gzxob6_/baseline.sqlite3`.
Все Python-команды нового baseline выполнялись с явными `DJANGO_SETTINGS_MODULE=config.settings.test`,
`DATABASE_URL=sqlite:////tmp/ee-preparation-test-6gzxob6_/baseline.sqlite3`, `TEST_DATABASE_URL=sqlite:////tmp/ee-preparation-test-6gzxob6_/baseline.sqlite3`,
`DJANGO_TEST_PROCESSES=4` и локальными allowed hosts. Фактический engine/path проверены до миграций.
В тестовых runner Django/pytest создаются дополнительные тестовые SQLite; это не рабочая база сайта.

Полные stdout/stderr, без сокращения: указанные `.log`; argv, exit codes, время и длительность: `evidence/local/RESULTS.json`.

## Новые локальные команды

| Проверка | Команда (при указанном выше окружении) | Статус | Exit | Секунды |
|---|---|---|---:|---:|
| uv-sync-frozen | `uv sync --frozen` | PASS | 0 | 0.114 |
| pnpm-install-frozen | `pnpm install --frozen-lockfile --ignore-scripts` | PASS | 0 | 0.466 |
| database-isolation | `uv run --frozen python manage.py shell -c 'from django.conf import settings; import json; d=settings.DATABASES['"'"'default'"'"']; assert d['"'"'ENGINE'"'"']=='"'"'django.db.backends.sqlite3'"'"'; assert str(d['"'"'NAME'"'"'])=='"'"'/tmp/ee-preparation-test-6gzxob6_/baseline.sqlite3'"'"'; print(json.dumps(d)); print('"'"'ISOLATED SQLITE VERIFIED'"'"')'` | PASS | 0 | 1.167 |
| compileall | `uv run --frozen python -m compileall -q apps config tests` | PASS | 0 | 0.215 |
| django-check | `uv run --frozen python manage.py check` | PASS | 0 | 0.415 |
| collectstatic | `uv run --frozen python manage.py collectstatic --noinput --verbosity 0` | PASS | 0 | 0.365 |
| audio-readiness | `uv run --frozen python scripts/audio_readiness.py` | PASS | 0 | 0.064 |
| cefr-evidence | `uv run --frozen python scripts/audit_cefr_evidence.py --strict` | PASS | 0 | 0.716 |
| migration-drift | `uv run --frozen python manage.py makemigrations --check --dry-run` | PASS | 0 | 0.365 |
| review-structure | `uv run --frozen python manage.py shell -c 'from apps.learning.mistake_review import question_bank,COUNT; from apps.drills.retry_guidance import PILOT_SLUGS; b=question_bank(); assert set(b)==set(PILOT_SLUGS); assert all(exercises and all(len(cards)==COUNT for cards in exercises.values()) for exercises in b.values()); print('"'"'A1 review structure OK:'"'"',len(b),'"'"'lessons'"'"')'` | PASS | 0 | 0.315 |
| understanding-structure | `uv run --frozen python manage.py shell -c 'from apps.learning.understanding import understanding_bank,SKILLS; from apps.drills.retry_guidance import PILOT_SLUGS; b=understanding_bank(); assert set(b)==set(PILOT_SLUGS); assert all(set(guide['"'"'tasks'"'"'])==set(SKILLS) for guide in b.values()); print('"'"'A1 understanding structure OK:'"'"',len(b),'"'"'guides'"'"')'` | PASS | 0 | 0.315 |
| migrate-isolated | `uv run --frozen python manage.py migrate --noinput -v 1` | PASS | 0 | 2.27 |
| load-content-isolated | `uv run --frozen python manage.py load_content` | PASS | 0 | 5.632 |
| audit-course-isolated | `uv run --frozen python manage.py audit_course` | PASS | 0 | 6.896 |
| css | `pnpm check:css` | PASS | 0 | 0.968 |
| javascript | `pnpm test:ui` | PASS | 0 | 2.325 |
| django-full | `uv run --frozen python manage.py test tests --parallel auto --noinput` | PASS | 0 | 239.902 |
| pytest-full | `uv run --frozen pytest -q -rfE` | BLOCKED | None | — |
| pytest-full-retry | `uv run --frozen pytest -q -rfE` | PASS | 0 | 888.936 |

### Новые итоговые строки runner

`django-full.log`: Ran 804 tests in 232.724s
`django-full.log`: OK (skipped=2)
`pytest-full-retry.log`: 806 passed, 2 skipped, 4948 subtests passed in 887.32s (0:14:47)


### Дополнительная проверка связанных поверхностей

`build_packet.py` → `extracts/PACKET_VALIDATION.json`: PASS, 163 полных файлов, 1508921 байт; SHA/размеры и сохранение всех исходных полей проверены. Это не оценка учебного языка.

Точная runtime-команда после создания marker `REVIEW_DATABASE_ONLY` со SHA snapshot в каталоге тестовой БД:

```bash
env -u DATABASE_URL DJANGO_SETTINGS_MODULE=config.settings.test TEST_DATABASE_URL='sqlite:////tmp/ee-preparation-test-6gzxob6_/baseline.sqlite3' DJANGO_ALLOWED_HOSTS='testserver,localhost,127.0.0.1' .venv/bin/python docs/review-preparation/a1-01-04/runtime_smoke.py --database '/tmp/ee-preparation-test-6gzxob6_/baseline.sqlite3'
```

Exit 0; PASS; 448 assertions; temporary_rows_rolled_back=True. Полный JSON: `evidence/local/runtime-smoke.json`, stderr: `runtime-smoke.stderr.log`.
Проверены все явно записанные answer/accepted для 21 упражнения и 16 переводов; sentinel mismatch не является набором всех возможных грамматических ошибок. HTTP-клиент не заменяет визуальную приёмку.

| QA-команда | Результат | Exit |
|---|---|---:|
| `.venv/bin/python scripts/qa_evolution.py fuzz --run-number 0 --seed 20261025` | PASS | 0 |
| `.venv/bin/python scripts/qa_mutation_probe.py --report /workspace/scratch/6babac9ddb0c/English-Encyclopedia/docs/review-preparation/a1-01-04/evidence/local/mutation-report.md` | PASS | 0 |

Fuzz: 64 случая, seed=20261025, regular minimum budget. Mutation sentinels: 4/4 намеренно сломанных варианта обнаружены в одноразовой копии. Ни один из этих результатов не является полным mutation score.

## Смысл зелёных диагностик

- CSS: 17 stylesheet; JavaScript: 122 tests, 122 pass, 0 fail.
- `audit_course`: ошибок нет, но A1+ = 547/550, повторение A1 в A1+=44% при цели 70%, 1004 единицы с неподтверждённым CEFR, предупреждения о длине историй 1–5 и опережающих collocations. Это не новые доказанные грамматические ошибки и не разрешение менять контент в этой подготовке.
- `audit_cefr_evidence.py --strict` проверяет согласованность записанных свидетельств. Его PASS не означает независимую проверку CEFR всех слов. В A1 457 записей остаются `cefr_unverified`.
- `audio_readiness.py` завершился с exit 0, но обнаружил **0/33** ожидаемых manifest. Это диагностический PASS команды; реальное прослушивание/сверка отсутствующего аудио **BLOCKED**.
- Числа Django unittest и pytest могут различаться из-за правил discovery. Используйте итоги каждого журнала, не переносите число одного runner в другой.

## Повторный полный pytest

Первый pytest-full оборвался без итоговой сводки и без полученного exit code. Процесс больше не работал; причина не установлена. Оригинальный частичный pytest-full.log сохранён, запись имеет BLOCKED. Повторный полный запуск выполняется отдельно и имеет собственный pytest-full-retry.log и строку результатов; его исход не переносится на первый запуск.

## Согласованность выбранных материалов с runtime

Дополнительный read-only runtime_data_consistency.py выполнен на той же отмеченной изолированной SQLite, exit 0. Все 105 raw-карточек совпали с фактически собранным question_bank, четыре compiled guide совпали с основными объяснениями+scaffold, четыре active topic — с диалогом+repair+missions+twists. Загруженные ключи, accepted, подсказки, объяснения и review_of для всех 21 основного и 16 переводов совпали с выборками. Полный результат: evidence/local/runtime-data-consistency.json. Это проверка выбора и сборки источников, не языка.

## Исторические GitHub Actions — не новые запуски

Run `40111428333` на том же SHA повторно прочитан через GitHub API. Обе jobs completed/success. Полные журналы: `evidence/historical-sqlite.log`, `evidence/historical-postgres.log`.
- SQLite CI: 806 passed, 2 skipped, 4948 subtests passed, 1061.00s.
- PostgreSQL CI: 808 passed, 4948 subtests passed, 845.70s. Этот ранее непрочитанный журнал теперь получен; это всё равно исторический, не новый локальный PostgreSQL прогон.
- Действующий CI/Quality Evolution на source SHA зелёный в ранее выполненных workflow. Deploy только прочитан как метаданные; в этой работе не запускался.

## BLOCKED и не выполнявшееся

- Новый PostgreSQL: серверные binaries PostgreSQL и Docker отсутствуют в окружении; тестируется локальный SQLite. Нельзя выдавать исторический postgres job за новый запуск.
- Browser desktop/390px, keyboard, reduced motion: Playwright1.62.1 доступен, Chromium executable отсутствует. Штатная `playwright install chromium` завершилась exit1 (скачанный ZIP 0 MiB/обрезан, End of central directory record signature not found). `evidence/local/browser-launch.log` содержит отдельную полную диагностику отсутствующего executable; полный console-log неудачной загрузки не сохранён и не представлен как полный.
- Coverage ratchet из отдельного Quality Evolution: `pytest-cov` отсутствует в lockfile/locked venv. Чтобы не добавлять неприкреплённую зависимость командой CI `--with pytest-cov`, новый coverage-report/ratchet не запускался. Fuzz и mutation этого workflow выполнены отдельно; весь Quality Evolution заново пройденным не называется.
- Реальное аудио/голоса ОС и качество произношения не проверены. Отсутствие assets в checkout не доказывает отсутствие на рабочем сайте.
- GPT-6 Pro / независимая языковая рецензия не запускались. Статус NOT_REVIEWED, а не VERIFIED.

Версии среды: `evidence/local/ENVIRONMENT.json`. Lockfile hashes before/after: `RESULTS.json`. Исполняемый baseline helper: `run_baseline.py`; не запускайте команды из CI в случайно унаследованном production-окружении.
