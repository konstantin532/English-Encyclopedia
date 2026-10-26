# Vocabulary and Phrase Trainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Выпустить добровольный трёхъединичный пилот внутри существующего Django-сайта с честными evidence и единым SRS.

**Architecture:** Versioned content → server encounter state → existing IndependentAttempt evidence → existing UnitProgress schedule. Новые user-owned сессии/мнемоники и additive migration; старые endpoints gated только для enrolled pilot targets.

**Tech Stack:** Django5.2, Python3.12, SQLite/PostgreSQL, templates, SCSS/CSS/vanilla JS. Только уже зафиксированные зависимости.

**Spec:** docs/superpowers/specs/2026-10-26-vocabulary-phrase-trainer-design.md

## Global Constraints

- Base main fbec572; ветка feat/vocabulary-phrase-pilot; не возвращать удалённый depth selector.
- Ровно LX-00055,LX-00285,LX-00084, после урока5; сохранить уроки, их порядок и UID.
- Инструкции/feedback RU, learning content natural AmE; all four methods connected, spoken self-report only, no recorder/API.
- Reuse LexicalUnit, UnitProgress, IndependentAttempt; preserve history; no new SRS, frameworks, paid services, dependency-manifest changes, authentication model/flow/permission changes.
- Disabled-by-default flag + opt-in; no merge/auto-merge; no migrations to working/user/production databases. Disposable test DBs allowed.
- Exact defaults:24h initial/min delayed;1,3,7,14day ladder;2recall tries;daily_limit1..10 default10;private mnemonic≤300chars;draft lifetime30days.
- DB idempotency+atomic schedule/session/attempt; PostgreSQL locks and SQLite write serialization/CAS bounded retry; owner/CSRF/private escaping/export/delete.
- Cosmetic continuity vs explicit assessment revision mapping; no historical recategorization; no mastery/CEFR claims from exposure.

## Review Focus

- Reveal/submission races and browser back must retain assistance and canonical state (Task2 service race and Task3 HTTP tests).
- Legacy APIs cannot bypass opt-in target gate or alter non-pilot behavior (Task2 regression tests).
- Version drift cannot silently change a resumed prompt or transfer historical meaning (Task1/2 compatibility tests).
- A valid open alternative may achieve the goal without target phrase evidence (Task1 assessment + Task3 self-check tests).
- Expired drafts/export/account deletion must preserve accepted history and exclude another user (Task2 lifecycle tests).

---

### Task 1: Reviewed pilot content and conservative assessment

**Files:** Create content/manifests/a1_vocabulary_trainer.json; apps/learning/trainer_content.py; tests/test_vocabulary_trainer_content.py.

**Interfaces:** Produces `PILOT_ID`, `CONTENT_VERSION`, `PILOT_SLUG`, `UNIT_UIDS`, `pilot_content() -> dict`, `unit_content(uid: str) -> dict`, `normalize_answer(text: str) -> str`, `assess_recall(unit: dict, answer: str) -> dict`. Entries include source/prerequisites/explanation/mnemonic/reviewer note/examples,2authored recall context families with stabletask IDs, accepted variants/meaning-changing examples,2application scenarios with criteria and several valid examples. No dynamic AI or exact grading of open English.

- [x] Write tests for exact3UIDs/source/prereqs/required reviewed mnemonics, distinct context families, cosmetic/assessment version mapping, task-specific accepted variants/normalization and unknown-vs-definite-error.
- [x] Run failing tests: `uv run python manage.py test tests.test_vocabulary_trainer_content --settings=config.settings.test --noinput`.
- [x] Implement manifest and loader with fail-closed editorial validation and conservative assessment. `assess_recall` returns outcome (`correct|incorrect|uncertain`), RUfeedback and canonical answer only service may expose after assessment; valid alternative goal success is separate from target evidence. Tea word task accepted tea only; would task accepts I'd/I would with taught coffee/tea context; repeat task accepts reviewed full phrase variants. Preserve internal apostrophes/negations/hyphens; no global normalizer rewrite.
- [x] Run green tests and commit task files only. Report exact RED/GREEN commands/results.

### Task 2: Persisted evidence, resumable session and one schedule owner

**Files:** Modify apps/learning/models.py, services.py, evidence.py, apps/api/views.py (whole-operation atomic retry), apps/accounts/data_rights.py (server-only export exclusions); Create additive apps/learning/migrations/0013_vocabulary_trainer.py (next actual number if changed), apps/learning/trainer_service.py, apps/learning/management/commands/expire_trainer_drafts.py; Create tests/test_vocabulary_trainer_service.py and tests/test_vocabulary_trainer_concurrency.py.

**Interfaces:** Consumes Task1 content functions. Produces `enroll(user, *, timezone_name='Europe/Moscow', daily_limit=10, prerequisites_confirmed=False)`, `dashboard(user, *, now=None) -> dict`, `start_encounter(user, uid, *, now=None) -> session`, `perform_action(user, session_id, token, revision, action, *, answer='', mode='text', self_rating='', now=None) -> dict`, `save_mnemonic(user, uid, text)`, `legacy_managed_units(user) -> set[str]`; exceptions `TrainerConflict`, `TrainerUnavailable`, `TrainerLimit` with RU messages. Return dict contains canonical session ID/revision/token/phase and allowed feedback; view controls rendering. Model names `TrainerEnrollment`, `TrainerSession`, `PersonalMnemonic`; directuser FK for export. Session owns private frozen content snapshot and task family, all phases and sticky assistance; attempts reuse IndependentAttempt with origin/target/session/server-owned evidence JSON. Review scheduling eligibility explicit; no competing progress table.

- [x] Write failing tests for opt-in/prereq gate,intro→recall→feedback→application→complete, hints/reveal,2tries,spoken self-report,text equivalence,first/delayed distinction,24h/ladder/errors/unknown/early, budget/timezones/DST/absence/families, stable snapshots/version/expired drafts, export/delete/ownership, duplicates/stale/reveal races/rollback, legacy gate and old evidence exclusion.
- [x] Run failing service tests before product changes. Use in-memory disposable DB only; never migrate default local DB.
- [x] Implement additive models/migration and service. Each request atomic, user-scoped serialized gate, compare revision/token, database uniqueness for logical attempts. Retry same payload returns same stored result; conflicting payload and stale action produce conflict without changing confirmed state. PostgreSQL locks; SQLite first-write serialization and bounded OperationalError retry. All pilot schedule mutation happens once per encounter and only via server eligibility. Assistance is persisted before return; all recorded assistance remains sticky for encounter. Existing correct/mistake statistics never fabricated from old data. Anonymous no enrollment. Legacy service entries skip trainer-owned LX progress but retain old lesson histories/48h queue; other users/LX unchanged.
- [x] Add real threaded TransactionTestCase concurrency with separate DB connections, synchronized requests and bounded joins; run SQLite and PostgreSQL where available, explicitly skip unsupported engine fixtures. Unique-constraint-only sequential checks do not count as real races.
- [x] Make expired draft cleanup scrub unsent drafts only and preserve attempts/snapshots/confirmed history. Include direct owned data export/delete tests.
- [x] Run targeted green tests, old SRS/MistakeReview/independent/data-rights regressions and makemigrations --check --dry-run with test settings. Commit task files only and report.

### Task 3: Accessible integrated learner journey and verification surfaces

**Files:** Create apps/learning/trainer_views.py, templates/learning/trainer.html, static/scss/vocabulary-trainer.scss and generated static/css/vocabulary-trainer.css, optional static/js/vocabulary-trainer.js; Modify apps/learning/urls.py, config/settings/base.py (disabled flag), templates/learning/dashboard.html, templates/lexicon/detail.html and relevant week template through guarded links; Create tests/test_vocabulary_trainer_views.py, tests/js/vocabulary-trainer.test.cjs, scripts/verify_vocabulary_trainer.cjs, docs/qa/vocabulary-phrase-trainer.md; update README only with actual preview/limitations.

**Interfaces:** Uses Task2 service exactly. New `/learn/vocabulary/` (actual config prefix verified in task), user-only GET/POST forms and POST→redirect→GET; canonical resume/status, optional draft autosave server-owned no localStorage sensitive text; CSRF forms work without JS. Disabledflag default false (`EE_VOCABULARY_TRAINER_ENABLED` env boolean). Flag-off must avoid querying missing new tables. Links guarded flag and selected unit/week.

- [x] Write failing HTTP/HTML tests:flag-off404/no schema queries,login/owner/CSRF,prereq introduction,all4methods,hidden target before attempt (no answer markup/data/title),bounded retries,unknown alternatives,spoken self-report vs text,mnemonic escaping,version conflict,resume/back/status,network-safe same operationtoken,pending/status/nextaction,expiry/export regressions.
- [x] Run RED. Implement views and readable mobile-first form flow using existing visual language/brand/fonts. All user text escaped; private/no-store; aria labels/live statuses/focus/noncolor indicators and no lost controls at320/390px and200% text. Current phase server-only; model is never sent as hidden DOM before attempt. No fake listening/prosody/CEFR metrics. Distinguish introduction answer visibility from assessment state.
- [x] Add guarded entry links. Display explainable4states. No long four-method ritual on every review; review first recall, optionalassistance, proportionate changed-context task and self-speaking reachable for eachunit.
- [x] Generate CSS with `pnpm build:css`; run `pnpm check:css` and `pnpm test:ui`. Add browser script using disposable DB + local preview (root owns process/fixture) forfulljourney,simulateddelay via server tests,keyboard,390px/desktop,200%text,back/doubleclick/requestfailure. Report automatedbrowser vsmanualvisual vsHTTP separately.
- [x] Document safe preview (`flag on`, migrations onlydisposableDB unlesspermission), compatible backup/restore/rollout/rollback, version map procedure, retention/export/delete, voluntary human evaluation with predefined48h/7dtasks/criteria/limitations.
- [x] Run completeDjango suite, migrationcheck,contentaudit in disposableDB,Node/CSS and browserchecks. Commit taskfiles only and report.

### Task 4: Whole-branch review, evidence and draft PR

**Files:** docs/qa/vocabulary-phrase-trainer.md, plan progress checkboxes; targeted fixes from independent review only.

**Interfaces:** Entire branch compared with fbec572; no merging or auto-merge.

- [x] Independently review spec coverage, history/migrations/security/concurrency and actual frontendbehavior, with concrete changedfiles/tests.
- [x] Resolve material findings with scoped regressiontests and re-review; no weakening checks.
- [x] Run finalfresh verification and recordPASS/FAIL/BLOCKED/N/A forCorrectness,Regression,Security,DataIntegrity,UX,Integration,Evidence.
- [ ] Commit and push feat/vocabulary-phrase-pilot; create one draft PR to main via GitHub plugin. Verify remoteSHA and actualCI state; wait for checks and fix failures in samebranch as necessary. Do notmerge.
- [ ] FinalreportRU:changedfiles,executedchecks/results,limitations,previewinstructions,PRlink and actualCI. Productionmigrationremainsseparatepermission.

Checkpoint перед публикацией: 1038 Django, 152 Node, 21 CSS, 40 actual browser checks, controlled delayed review и ручной осмотр — PASS; whole-branch и scoped review завершены без открытых материальных замечаний. Операционные действия draftPR/actualCI выполняются после этого коммита; их окончательные факты фиксируются в описании PR и финальном ответе.
