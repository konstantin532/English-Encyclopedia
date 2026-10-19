# A1 evidence integrity and spaced-review consistency — 2026-10-19

## Baseline and scope

Baseline main: `94d6841138d4f2c47937a6ff20660aee1f4bfb84` (merged PR #36).
At baseline, CI and Quality Evolution passed. CI log: **560 Python tests,
3942 subtests, 194 warnings; 97 JavaScript tests**. Those checks do **not**
establish proficiency, professional listening approval, Android/TalkBack support,
or Render operation.

This is a targeted source audit, not a completed audit of every A1 text.

## Evidence ledger — confirmed code-level defects

| ID | Where / root cause | Reproduction using existing source | Repair / residual risk |
| --- | --- | --- | --- |
| LE-01 | `apps/learning/models.py:UnitProgress.register` | Four different model-matched exercise contexts advanced `recognition` through `guided_use` to `active`, without free output or teacher review. Existing unit test explicitly expected this. | Cap new model-checked progress at `guided_use`. Existing learner statuses, exercise histories, and unit IDs remain intact; **historical high statuses have not been independently validated**. |
| LE-02 | `SpeechPracticeProgress.register` | Posting `good` twice at the same timestamp advanced the interval a second time before it was due. | Additional early successful ratings do not advance the stage or postpone the due date; first rating and genuinely due ratings still work. It remains self-assessment, not speech recognition. |
| LE-03 | `apps/learning/services.py:record_recall` | Unlike `record_attempt`, the recall path used read–modify–save without a transaction or row lock. Concurrent requests could overwrite correct/wrong counters on PostgreSQL. | Add atomic transaction and `select_for_update`. Concurrency interleaving under production PostgreSQL still requires load testing. |
| LE-04 | `apps/learning/views.py:dashboard` | Counter displayed every due speech DB row, including removed lessons or fragments outside the current lesson, while the review page filtered them out. | Share valid-item selection with the review page; three bulk content queries replace per-key lookups. Full dashboard cost under high-volume progress still needs benchmarking. |
| LE-05 | `templates/learning/dashboard.html` | Four guided constructions were labeled as sufficient for active vocabulary. | Label historical statuses as historical, remove the misleading four-context threshold and state the evidence limitation. |

## Regression coverage

- `tests/test_content_and_learning.py`: several *different* guided contexts cannot be automatically promoted to independent/active use.
- `tests/test_speech_review.py`: repeated early good ratings / repeated POST cannot advance spaced stage; stale speech content is omitted from dashboard count; query-count regression protects against N+1 lookups.
- CI provides available Django, Python, JavaScript, and course-loading checks after a PR is opened. No pre-fix negative test run was executed; code-level counterexamples and former positive expectations are the initial evidence.

## What has not been proven

- No real audio from Kokoro has been generated, downloaded, acoustically listened to, or manually approved during this change.
- No complete independently sourced CEFR sense review: 457 pending, 41 partial, 2 verified is the last reviewed inventory, not a newly validated audit.
- No real Android/TalkBack run, real learner pilot, production PostgreSQL race test, Render deploy, backup/restore test, or live-browser screenshot comparisons.
- This PR does not retroactively reinterpret learner records or award teacher verdicts; independent proficiency requires evaluated open output and delayed application.

## Next high-impact verification

1. End-to-end PostgreSQL concurrency checks and production deployment rehearsal with backups.
2. Real audio artifact creation + structured listening review (99 tracks) before any `verified` status.
3. Human CEFR sense audit and beginner learner pilot with delayed transfer exercises.
4. Browser/device accessibility checks across 320–1280 px and real TalkBack.
