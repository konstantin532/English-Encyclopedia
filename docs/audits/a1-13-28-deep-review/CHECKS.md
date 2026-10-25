# Проверки A1 13–28

База 8788aac; опубликованный source commit f755656dbf8d76f56fed1f9bd5a0888d9df3be1a. Все локальные Django-команды используют config.settings.test и оба SQLite URL из DATABASE.json. На базу сайта не подключались.

## Первый полный прогон и подготовка

Каждая строка относится к фактическому новому запуску. Первый полный Django выполнен до двух addendum и корректно записан FAIL. Его нельзя считать проверкой конечного исходника.

|Команда|Exit|Время, с|
|---|---:|---:|
|`uv run --frozen python manage.py shell -c 'from django.conf import settings; d=settings.DATABASES['"'"'default'"'"']; assert d['"'"'ENGINE'"'"']=='"'"'django.db.backends.sqlite3'"'"' and d['"'"'NAME'"'"']=='"'"'/tmp/ee-a1-13-28-verification-07ft_u_u/fixture.sqlite3'"'"'; print(d['"'"'ENGINE'"'"'],d['"'"'NAME'"'"'])'`|0|1.286|
|`uv sync --frozen`|0|0.066|
|`pnpm install --frozen-lockfile --ignore-scripts`|0|1.037|
|`uv run --frozen python -m compileall -q apps config tests`|0|0.321|
|`uv run --frozen python manage.py check`|0|0.638|
|`uv run --frozen python manage.py collectstatic --noinput --verbosity 0`|0|0.546|
|`uv run --frozen python manage.py makemigrations --check --dry-run`|0|0.518|
|`uv run --frozen python manage.py migrate --noinput -v0`|0|3.715|
|`uv run --frozen python manage.py load_content`|0|9.368|
|`uv run --frozen python manage.py audit_course`|0|7.786|
|`uv run --frozen python manage.py test tests.test_a1_editorial_deep_13_16 tests.test_a1_side_context_13_16 tests.test_a1_deep_13_16_shared tests.test_a1_deep_13_16_shared_sides tests.test_a1_deep_17_20 tests.test_a1_editorial_deep_21_24 tests.test_a1_deep_25_28 tests.test_audit_latin_tokens --noinput`|0|19.687|
|`uv run --frozen python manage.py shell -c 'from apps.learning.mistake_review import question_bank,COUNT; from apps.learning.understanding import understanding_bank,SKILLS; from apps.drills.retry_guidance import PILOT_SLUGS; b=question_bank(); assert set(b)==set(PILOT_SLUGS); assert all(all(len(c)==COUNT for c in e.values()) for e in b.values()); u=understanding_bank(); assert set(u)==set(PILOT_SLUGS); assert all(set(g['"'"'tasks'"'"'])==set(SKILLS) for g in u.values()); print(len(b),len(u))'`|0|0.399|
|`pnpm check:css`|0|1.258|
|`pnpm test:ui`|0|2.43|
|`uv run --frozen python scripts/audio_readiness.py`|0|0.084|
|`uv run --frozen python scripts/audit_cefr_evidence.py --strict`|0|0.892|
|`uv run --frozen python scripts/qa_evolution.py fuzz --run-number 0 --seed 20261025`|0|0.508|
|`uv run --frozen python scripts/qa_mutation_probe.py --report /tmp/ee-a1-13-28/docs/audits/a1-13-28-deep-review/evidence/complete/mutation-report.md`|0|4.656|
|`uv run --frozen python manage.py test tests --parallel auto --noinput`|1|444.37|

## Конечный исходник

- `manage.py test tests.test_a1_active_quality tests.test_a1_active_studio tests.test_a1_deep_17_20 --noinput`:32 PASS, тело3.535s, `evidence/integrated/active-ex113-after.log`. Старые activequality tests не изменялись.
- `manage.py shell -c "exec(open('docs/audits/a1-13-28-deep-review/verify_reload_history.py').read())"`:PASS, дваload_content, identities1047/60/355/240 и четыре типа истории сохранены; guard проверяет test settings и изолированный путь.
- `python docs/audits/a1-13-28-deep-review/verify_integrity.py`:PASS,244полных изменённых полей; неизменныеidentities/protected scope; исходныеfailureактивнойпробы сохранены.
- `node --check scripts/verify_atlas.cjs`:PASS. `git diff --check -- apps content scripts tests`:PASS.
- GitHub Atlas run40186265539:PASS на f755656,58editorialpage/viewportchecks; artifact12596183379/report.json passed=true/errors=[]. L14/L20/poem7/story3mobile и L28desktop реально просмотрены.
- Полный конечный Django:PASS,899tests/2skip/441.714s; итоговая команда/exit0 в evidence/final/RESULTS.json. SQLite/PostgreSQL remoteCI40186265546:RUNNING, неPASS.

## Ограничения

Настоящее аудио и humanpilot/повторная содержательная приёмка не выполнены. Локальный Chromium ранее BLOCKED; это не подмена удалённого PASS. Coverage Quality Evolution40186265540 покаRUNNING и не считается пройденным; отдельный timeoutPR120 не дублируется. Более старые group логи сохранены отдельно, а draft/frozenbefore/after различаются в групповых отчётах.
