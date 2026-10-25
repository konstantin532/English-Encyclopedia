# Новые проверки A1 5–8

author: Codex; reviewed_by: automated reproducible checks; verification_status: technical_review; date: 2026-10-25
source_notes: actual local process exit codes, full logs under evidence/current-main.

Baseline 5826785ee3f665fac765783ba9a95a5dd3b52655, явная изолированная временная SQLite. Production не использовалась.

| Проверка | Команда | Результат | Секунды |
|---|---|---|---|
| database-guard | `uv run --frozen python manage.py shell -c from django.conf import settings; d=settings.DATABASES['default']; assert d['ENGINE']=='django.db.backends.sqlite3' and d['NAME']=='/tmp/ee-a1-05-08-verification-_6otf_54/fixture.sqlite3'; print(d['ENGINE'],d['NAME'])` | PASS (exit 0) | 0.432 |
| uv-sync | `uv sync --frozen` | PASS (exit 0) | 0.013 |
| pnpm-install | `pnpm install --frozen-lockfile --ignore-scripts` | PASS (exit 0) | 0.58 |
| compileall | `uv run --frozen python -m compileall -q apps config tests` | PASS (exit 0) | 0.072 |
| check | `uv run --frozen python manage.py check` | PASS (exit 0) | 0.471 |
| collectstatic | `uv run --frozen python manage.py collectstatic --noinput --verbosity 0` | PASS (exit 0) | 0.36 |
| makemigrations | `uv run --frozen python manage.py makemigrations --check --dry-run` | PASS (exit 0) | 0.565 |
| migrate | `uv run --frozen python manage.py migrate --noinput -v0` | PASS (exit 0) | 3.182 |
| load-content | `uv run --frozen python manage.py load_content` | PASS (exit 0) | 8.656 |
| audit-course | `uv run --frozen python manage.py audit_course` | PASS (exit 0) | 8.65 |
| targeted | `uv run --frozen python manage.py test tests.test_a1_editorial_deep_05_08 tests.test_a1_deep_05_08_support --noinput` | PASS (exit 0) | 12.861 |
| review-contracts | `uv run --frozen python manage.py shell -c from apps.learning.mistake_review import question_bank,COUNT; from apps.learning.understanding import understanding_bank,SKILLS; from apps.drills.retry_guidance import PILOT_SLUGS; b=question_bank(); assert set(b)==set(PILOT_SLUGS); assert all(all(len(c)==COUNT for c in e.values()) for e in b.values()); u=understanding_bank(); assert set(u)==set(PILOT_SLUGS); assert all(set(g['tasks'])==set(SKILLS) for g in u.values()); print(len(b),len(u))` | PASS (exit 0) | 0.467 |
| css | `pnpm check:css` | PASS (exit 0) | 1.28 |
| js | `pnpm test:ui` | PASS (exit 0) | 3.065 |
| audio-readiness | `uv run --frozen python scripts/audio_readiness.py` | PASS (exit 0) | 0.061 |
| cefr | `uv run --frozen python scripts/audit_cefr_evidence.py --strict` | PASS (exit 0) | 0.974 |
| fuzz | `uv run --frozen python scripts/qa_evolution.py fuzz --run-number 0 --seed 20261025` | PASS (exit 0) | 0.448 |
| mutation | `uv run --frozen python scripts/qa_mutation_probe.py --report /workspace/scratch/6babac9ddb0c/English-Encyclopedia/docs/audits/a1-05-08-deep-review/evidence/current-main/mutation-report.md` | PASS (exit 0) | 3.476 |
| django-full | `uv run --frozen python manage.py test tests --parallel auto --noinput` | PASS (exit 0) | 431.216 |
| pytest-full | `uv run --frozen pytest -q -rfE` | PASS (exit 0) | 1439.921 |

Полные результаты: [RESULTS.json](evidence/current-main/RESULTS.json). Каждый лог назван по имени проверки.

## Ограничения

- PostgreSQL: BLOCKED — нет postgres/initdb/Docker. SQLite PASS не заменяет проверку другой СУБД.
- Desktop/390 px, клавиатура/reduced-motion: BLOCKED — нет браузера; попытка установки Chromium завершилась повреждённым ZIP. HTTP-проверка и разбор HTML не являются визуальной приёмкой.
- Настоящая озвучка: BLOCKED — прослушивание не проводилось. audio-readiness с exit 0 — диагностический отчёт, не аудиоприёмка.
- Coverage workflow: BLOCKED — pytest-cov не входит в frozen lockfile; зависимости не обновлялись ради этого прогона.
- Пилот с людьми и повторная содержательная приёмка: BLOCKED — не проводились.

## Разделение доказательств

targeted-before: исходные 18 методов, 66 failures; support-before: 3 метода, 5 failures; JS before: 1 failure в 2 тестах. Это ожидаемые воспроизведения на исходнике fb79cd7. SHA тестов зафиксированы; целевые материалы 5–8 не менялись в merge117.

Каталоги final/final-complete/verified и ранние targeted-логи — промежуточные версии. Остановленные прогоны не считаются PASS. Последняя последовательность current-main относится к main после слияния117; отдельные последние уточнения R17 при наличии отмечаются отдельно.

Старые журналы GitHub Actions не использованы для присвоения PASS новым правкам. Новый CI после публикации PR должен рассматриваться отдельно.

## Последние уточнения и границы результата

- Django: 844 tests, OK, skipped=2; started before the three final R17 wording changes.
- Final 47 targeted tests and full pytest ran against final source, including R17.
- Final content reload/audit and seven HTTP200 checks: FINAL_EXTRA.json.
- CSS17, JS124, fuzz64, mutation probes4/4; mutation probes are a smoke test, not a project-wide mutation score.
- CEFR strict validates the existing evidence format; it does not confirm all lexical levels. Audit still reports 1004 unverified units, A1+547/550, recycling44% versus70%, and old story-length warnings.

Raw artifact whitespace: `git diff --cached --check` reports spaces in SOURCE.patch context and raw logs (exit2). These artifacts are preserved exactly; the same check restricted to changed source/tests/journal passes. This is not a weakened CI check.
