# Точка продолжения: тренажёр слов и фраз

**Возобновлено 2026-10-26 по сообщению пользователя «Продолжай». Task1 и Task2 завершены и прошли независимое ревью; далее Task3 (интерфейс), Task4 (полная проверка/draft PR).**

## Репозиторий и границы

- Repo: https://github.com/konstantin532/English-Encyclopedia
- Согласованный base/main: fbec5724b67b9caf7045fa3a4da386607eedb759. PR129 слит; удалённый переключатель глубины не возвращать.
- Ветка: feat/vocabulary-phrase-pilot.
- Исследовательская копия: /workspace/scratch/9aa7896d9057/English-Encyclopedia (detached base, чужих изменений нет).
- Рабочий worktree: /workspace/scratch/9aa7896d9057/English-Encyclopedia/.worktrees/vocabulary-phrase-pilot.
- Пользователь явно одобрил дизайн и разработку. Merge/auto-merge и миграции к рабочей/production БД не разрешены. Испытания миграций разрешены только на disposable DB.
- Сохранённый дизайн: docs/superpowers/specs/2026-10-26-vocabulary-phrase-trainer-design.md.
- План: docs/superpowers/plans/2026-10-26-vocabulary-phrase-trainer.md.

## Что уже сделано

1. ce9649a — записан одобренный дизайн и план.
2. 05f77af08d482ca75ed66739da74568231678e7e — реализована Task1, ровно три файла:
   - content/manifests/a1_vocabulary_trainer.json;
   - apps/learning/trainer_content.py;
   - tests/test_vocabulary_trainer_content.py.
3. Независимый review_content_impl проверил diff ce9649a..05f77af: Spec compliant, Quality Approved, material findings none. Подтвердил пререквизиты по уроку5. Повторно тесты не запускал.

Пилот: ровно LX-00055 tea, LX-00285 I would like a coffee, please., LX-00084 Sorry? Can you say it again, please?, после a1-cafe-order (урок5/неделя3). Новых LX, изменений уроков/лексикона нет. Мнемоники смысловые, AI-reviewed, без ложного подтверждения преподавателем или эффективности на людях.

## Проверки и точные ограничения

- Baseline targeted: 63 Django-теста существующих SRS/MistakeReview/atomic/independent/data-rights PASS на disposable SQLite.
- Baseline frontend: pnpm check:css —20/20; pnpm test:ui —139/139 PASS.
- Task1 latest: `uv run python manage.py test tests.test_vocabulary_trainer_content --settings=config.settings.test --noinput` —13/13 PASS (0.043–0.045s).
- Disposable in-memory migrate→load_content→audit_course: exit0, «Ошибок нет». Существующие предупреждения:1004unverified CEFR, A1→A1+ recycling221/500(44%) vs70%,3forwardcollocations. Эти предупреждения не исправлялись в рамках пилота.
- Первый полный прогон Task1:971test/405.877s, FAIL1, skipped2. Единственная ошибка test_repeat_requires_full_reviewed_phrase_not_keyword: во время прогона был загружен старый тест could=correct, затем manifest уточнён до could=uncertain; последний отдельный13-test прогон зелёный. Не выдавать этот полный прогон заPASS. Дальнейшие полные прогоны выполнять с неизменяемыми исходниками.
- Второй полный прогон Task1 остановлен по решению root, exit130, чтобы не дублировать предстоящий frozen integration run. Финальный полный Django-прогон ОБЯЗАТЕЛЕН.
- Отдельный root baseline959run завершился без финальной сводки в логе: UNKNOWN, неPASS. Лог scratch /workspace/scratch/9aa7896d9057/baseline-full-tests.log.
- Макеты, HTTP и полный browserjourney пока не реализованы/не проверены. PostgreSQL/concurrency пока не проверены.
- Рабочие/production БД не открывались и не мигрировались. Схемы ещё не менялись.

## Контракт Task1 для следующего исполнителя

Constants: PILOT_ID='a1-vocabulary-phrase-pilot', CONTENT_VERSION='1.0', PILOT_SLUG='a1-cafe-order', UNIT_UIDS=('LX-00055','LX-00285','LX-00084').

Functions: pilot_content()->dict; unit_content(uid)->dict; normalize_answer(text)->str; assess_recall(unit, answer, *, task_id=None)->dict.

Unit includes source/prerequisites/explanation/mnemonic/reviewer_note/examples; recall_tasks (2 distinct task_id/family_id,prompt,model,accepted,meaning_errors,valid_alternatives,evidence_kind); applications (2 ungraded scenarios,criteria,valid_examples,assessment=self_report_only); spoken (no audio,self-report).

Assessment returns outcome(correct/incorrect/uncertain),feedback,canonical_answer,goal_achieved(bool|None),target_used(bool),task_id,family_id,evidence_kind. Result is SERVER-PRIVATE until correct stage; do not put canonical_answer in assessment HTML/data/hidden fields. Unknown natural English remains uncertain, notwrong. Could variants not taught by lesson5 remain uncertain; can and please-position variants reviewed. Source variation tea within request is permitted, not a new sense or automatically component-word mastery.

## Следующие действия после явного разрешения продолжить

1. Read this checkpoint, AGENTS.md, CLAUDE.md, approved spec and plan. Check actual branch/HEAD/dirty state/remote main/related PRs; preserve changes. Task1 complete, do not rebuild it.
2. Task2: persist sessions/enrollment/private mnemonics and extend IndependentAttempt; single UnitProgress gate with idempotency/concurrency/assistance/evidence and legacy compatibility; additive migration tests onlydisposableDB. Read Task2 brief in plan. No implementation of Task2 has started.
3. Task3: accessible integrated views/templates/SCSS/JS, default-off flag+opt-in, guarded entrylinks, fulljourney and recovery, browser/HTTP tests and rollout/evaluation docs.
4. Task4: independent wholebranch review, fix regressions, fresh fullsuite/Node/CSS/audit/migrationchecks, remotecommit and actualCIverification; one separate draftPR, no merge.

## Среда и воспроизведение

- Existing frozen deps installed only in ignored worktree .venv/node_modules: `uv sync --frozen`, `pnpm install --frozen-lockfile --ignore-scripts`. Dependency manifests unchanged. Python3.13.16, Django5.2.18; lock supports3.12–3.14.
- Run Django with `--settings=config.settings.test --noinput` to ensure disposableDB. `uv run python manage.py collectstatic --settings=config.settings.test --noinput --verbosity0` prepared ignoredstaticfiles; spelling requires `--verbosity 0` as separate arguments when rerunning.
- For manageable fullsuite: `DJANGO_TEST_PROCESSES=4 uv run python manage.py test tests --parallel auto --settings=config.settings.test --noinput` (same tests, bounded worker count). Do not edit source while fullsuite runs.
- Test browser available: /tmp/chromium, Chromium153.0.8010.0; Playwright preinstalled under CODEX_PRIMARY_RUNTIME_NODE_MODULES/playwright. Smoke launch+setContent+title PASS. Launch args: --no-sandbox,--disable-dev-shm-usage,--disable-gpu,--single-process,--no-zygote. This is infrastructure readiness, not product browser acceptance.
- Direct Playwright CDN download failed; ephemeral browser obtained via npm @sparticuz/chromium package under /workspace/scratch/9aa7896d9057/test-browser (not a project dependency). Manual Brotli decompression was required because package automatic extraction attempted unsupported chown. Browser may need re-preparation if scratch disappears. No browsercode or dependency added to repo yet.
- PostgreSQL unavailable locally; apt setup unsupported in this environment. Do not bypass permissions. Existing CI PostgreSQL16 job can verify future real races; report actual status.
- Ignored task artifacts: .superpowers/sdd/vocabulary-phrase-trainer/{progress.md,task-N-brief.md,task-1-report.md,task-1-review-package.diff}. Essential state is duplicated in this tracked checkpoint so scratch loss does not lose recovery information.

DraftPR has not been created. Nothing has been merged or deployed.

## Обновление после возобновления

Task2 реализован08c62c6, исправленияревьюf234b94. Независимое scopedревью:SpecPASS/QualityApproved;3находкизакрыты. Последнийцелевойпрогон47PASS12.596s (server/data-rights/SQLitethreaded/migration). PostgreSQLещёBLOCKEDлокально, полныйfrozenintegrationrunиUI/browserpending.

Удалённаяветка на моментвозобновления04cafb0, локальнаяисторияэквивалентнаподругимSHA:ce9649a→801eff9;05f77af→d6b918d;80e388d→04cafb0. Деревьяидентичны. Продолжениеведётсявпрежнемизолированномworktree; обычныйgitpushнеимеетcredentials, новыеcommitsбудутпереданычерезподключённыйGitHubсleaseбезforce.
