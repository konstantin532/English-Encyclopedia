# Новые проверки A1 9–12

author: Codex; reviewed_by: recorded process exits; verification_status: technical_review; date:2026-10-25
source_notes: frozen source9749fab; all DB operations explicitly temporary SQLite; production unused.

| Проверка | Команда | Результат | Секунды |
|---|---|---|---|
|database-guard|`uv run --frozen python manage.py shell -c from django.conf import settings; d=settings.DATABASES['default']; assert d['ENGINE']=='django.db.backends.sqlite3' and d['NAME']=='/tmp/ee-a1-09-12-verification-0wdpv_le/fixture.sqlite3'; print(d['ENGINE'],d['NAME'])`|PASS / exit0|0.567|
|uv-sync|`uv sync --frozen`|PASS / exit0|0.016|
|pnpm-install|`pnpm install --frozen-lockfile --ignore-scripts`|PASS / exit0|0.73|
|compileall|`uv run --frozen python -m compileall -q apps config tests`|PASS / exit0|0.082|
|check|`uv run --frozen python manage.py check`|PASS / exit0|0.45|
|collectstatic|`uv run --frozen python manage.py collectstatic --noinput --verbosity 0`|PASS / exit0|0.401|
|makemigrations|`uv run --frozen python manage.py makemigrations --check --dry-run`|PASS / exit0|0.741|
|migrate|`uv run --frozen python manage.py migrate --noinput -v0`|PASS / exit0|7.913|
|load-content|`uv run --frozen python manage.py load_content`|PASS / exit0|7.29|
|audit-course|`uv run --frozen python manage.py audit_course`|PASS / exit0|7.897|
|targeted|`uv run --frozen python manage.py test tests.test_a1_editorial_deep_09_12 tests.test_a1_deep_09_12_shared --noinput`|PASS / exit0|20.301|
|review-contracts|`uv run --frozen python manage.py shell -c from apps.learning.mistake_review import question_bank,COUNT; from apps.learning.understanding import understanding_bank,SKILLS; from apps.drills.retry_guidance import PILOT_SLUGS; b=question_bank(); assert set(b)==set(PILOT_SLUGS); assert all(all(len(c)==COUNT for c in e.values()) for e in b.values()); u=understanding_bank(); assert set(u)==set(PILOT_SLUGS); assert all(set(g['tasks'])==set(SKILLS) for g in u.values()); print(len(b),len(u))`|PASS / exit0|0.426|
|css|`pnpm check:css`|PASS / exit0|1.294|
|js|`pnpm test:ui`|PASS / exit0|2.348|
|audio-readiness|`uv run --frozen python scripts/audio_readiness.py`|PASS / exit0|0.069|
|cefr|`uv run --frozen python scripts/audit_cefr_evidence.py --strict`|PASS / exit0|0.989|
|fuzz|`uv run --frozen python scripts/qa_evolution.py fuzz --run-number 0 --seed 20261025`|PASS / exit0|0.443|
|mutation|`uv run --frozen python scripts/qa_mutation_probe.py --report /workspace/scratch/6babac9ddb0c/English-Encyclopedia/docs/audits/a1-09-12-deep-review/evidence/complete/mutation-report.md`|PASS / exit0|4.481|

First full Django:845 tests,1FAIL,2skipped; full raw log evidence/final/django-full.log. The stale literal test was strengthened, not disabled: MISTAKE_REVIEW_TEST_FIX.json; independent corrected test PASS.

Corrected full Django repeat: BLOCKED by environment interruption, no final exit. Local full pytest: NOT_RUN. Standard GitHub CI will run full pytest on SQLite and PostgreSQL; results must be read from this PR, not PR118.

Earlier checkpoint86 targeted PASS and frozen13/9 before/after runs remain in evidence; the fresh targeted22 PASS is in evidence/complete. Frozen test definitions are unchanged.

Browser desktop390/keyboard/reduced-motion BLOCKED: install/launch errors in evidence/browser. Actual audio BLOCKED. No human pilot. Local PostgreSQL/Docker unavailable; coverage not run locally. General audit warnings retained.

Initial evidence/full stopped during dependency setup because network proxies were omitted; dependencies then installed with normal env and runner corrected to preserve only network proxy settings plus explicit isolated DB. evidence/verified stopped before full tests for final editorial corrections. evidence/final is the completed845/1FAIL run, not PASS. evidence/complete is the interrupted corrected repeat.

Source-only git diff --check PASS. Raw patch/log context spaces are preserved, not reformatted for whitespace output.
