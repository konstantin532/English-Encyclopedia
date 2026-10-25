# A1 lessons 21–24: implementation handoff

Base: `5826785ee3f665fac765783ba9a95a5dd3b52655`. Detached worktree `/tmp/ee-a1-21-24-deep`. No commit/publication/merge. Parent integrates patch, then runs full suite/browser. This is a bounded four-lesson revision, not acceptance of the full course.

## Actual scope
Read four lessons (slugs `a1-what-hurts`, `a1-cant-cannot`, `a1-dont-doesnt`, `a1-letters-address`), their main exercises EX-00116–EX-00139, all 16 translation practice items, health/health_plus/post/post_plus/story04 lexical packs, weeks11–12 scripts/twisters, course_map assignments story4/poem6, the four scoped entries in scaffold/understanding, both active topic/error-repair/scenario files, full micro21–24 and delayed21–24 banks. Root AGENTS/CLAUDE, situation-weeks spec, taxonomy registry checked; no additional applicable directory instructions found. Source hashes cover changed sources; immutable base provides unchanged snapshots.

## Corrections and rationale
- `hurt`, `know` and adjectives: removed misleading grammatical decision “action vs state”. A state may be expressed with an independent verb (I like, I know); be/feel + adjective is a specific construction. Consistent changes in lessons, lexical usage, active context and understanding guide.
- EX117 completing only headache cannot certify supplied `I have a headache`; EX129 completing don't cannot certify the entire supplied stamp sentence. EX121 canonical My leg hurts cannot certify unused noun pain. EX126 choosing thirsty cannot certify tired and hungry distractors. Removed only inappropriate evidence bindings. Whole-lesson unit inventories untouched.
- Practice23#2 retained both old accepted variants; clarified already identified old mailbox context, so omitting old does not lose the intended referent. Removed full `It does not get letters` chunk credit from an answer that actually names mailbox, retained mailbox/letter units.
- EX139 locally accepts `My last name's Belova`. Possessive 's, wrong owner, wrong field, negation and wrong order remain rejected. No global contraction or grader change.
- Scaffold24 used repeat (introduced week13) and again (not found as an independent A1 unit). Replaced with already known spell requests; no new lexical IDs or themes. Original address/recipient narrative remains intact.
- sleep lexical meaning is not limited to nighttime. white definition uses American color. The /ð/ sound is not Russian з. Weak are explained as the selected sample /ɚ/, not universal disappearance; full /ɑr/ remains possible.
- Story4 and poem6 no before nouns is T4 determiner, spatial on is P1; isolated No answers remain O4. Occupied registry definitions/colors untouched. English story/poem words, IPA and spoken text are unchanged after removing markers.

## Frozen reproductions and new checks
Exact same final test module in clean before and edited after, SHA256 `1ce9b2b9f0e4036ac0f640c9b8a32438e98d36590963fb2a38b707296071c2d6`. Both final copies match; `/tmp/a1-21-24-frozen-tests.sha256`.
- BEFORE: 7 tests, 5 failures (4 lexical progress defects plus local noun-is contraction). `/tmp/a1-21-24-before.log`.
- AFTER: 7 new tests plus 8 existing week09_10 tests = 15 PASS. `/tmp/a1-21-24-after.log`.
- Related active quality/studio, independent understanding, microsteps and scaffold variants: 76 PASS. `/tmp/a1-21-24-related.log`.
- Isolated migrate PASS; load_content PASS:1047units/60lessons/11stories/7poems/30weeks. audit_course PASS (“Ошибок нет”), existing length/repetition/forward-word warnings retained. Logs `/tmp/a1-21-24-{migrate,load,audit}.log`.
- Explicit SQLite DB guard PASS. `/tmp/a1-21-24-db-guard.log`.
- JSON/YAML parse, exact seven layers, lesson inventories and stable exercise identities, shared-manifest change scope PASS. `/tmp/a1-21-24-integrity.log`. Git diff --check PASS.

Commands use existing lockfile-prepared parent interpreter (no dependency/lock changes):
```
PY=/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python
DATABASE_URL=sqlite:////tmp/ee2124-before.sqlite3 TEST_DATABASE_URL=sqlite:////tmp/ee2124-before.sqlite3 DJANGO_SETTINGS_MODULE=config.settings.test SECRET_KEY=isolated-test "$PY" manage.py test tests.test_a1_editorial_deep_21_24 --noinput
DATABASE_URL=sqlite:////tmp/ee2124-after.sqlite3 TEST_DATABASE_URL=sqlite:////tmp/ee2124-after.sqlite3 DJANGO_SETTINGS_MODULE=config.settings.test SECRET_KEY=isolated-test "$PY" manage.py test tests.test_a1_editorial_deep_21_24 tests.test_a1_editorial_week09_10 --noinput
DATABASE_URL=sqlite:////tmp/ee2124-related.sqlite3 TEST_DATABASE_URL=sqlite:////tmp/ee2124-related.sqlite3 DJANGO_SETTINGS_MODULE=config.settings.test SECRET_KEY=isolated-test "$PY" manage.py test tests.test_a1_active_quality tests.test_a1_active_studio tests.test_a1_independent_understanding tests.test_a1_microsteps tests.test_a1_scaffold_variants --noinput
```
Before command cwd `/tmp/ee-a1-21-24-before`; remaining cwd edited worktree. Migrate/load/audit used BOTH DB URLs `sqlite:////tmp/ee2124-isolated-final.sqlite3`, same test settings/secret, subcommands `migrate --noinput`, `load_content`, `audit_course`. No production DB was accessed. Dependency sync not repeated in child; interpreter reused from parent, lockfiles unchanged.

## Primary references actually retrieved
- Cambridge English Grammar Today, Do: https://dictionary.cambridge.org/grammar/british-grammar/do — auxiliary do negatives and infinitive without to. Applies to shared standard grammar; no British-specific replacement imposed.
- Cambridge Essential American Dictionary, sleep: https://dictionary.cambridge.org/us/dictionary/essential-american-english/sleep?q=sleep_2 — state of rest, not restricted to night.
- Cambridge grammar samples https://assets.cambridge.org/97805216/65773/sample/9780521665773ws.pdf — stative verbs including know are normally simple; state ≠ be/feel-only rule.
- Direct retrieval of Cambridge are/the entries returned403. No claim of successful retrieval/audio verification for those pages; selected weak are IPA already in actual source. /ð/ distinction is articulatory correction, no frequency assertion.

## Limits / deferred
Full test suite, actual browser desktop/390px and CI/publication are reserved for parent integration. Four lesson HTML GETs and grading APIs passed; this is not visual QA. No PostgreSQL/concurrency claim. No real audio files found at static/audio or media (only media/.gitkeep); no listening claimed. Existing dialogue/story/poem spoken English unchanged, so no audio regeneration indicated by these edits. Scaffold model changes have no identified audio asset; unknown remote audio remains unverified. Questions of medical advice correctness are outside these language fixes; no treatment recommendations changed. Existing story length/repetition warnings remain.

Deliverables: `/tmp/a1-21-24-deep.patch`, stable-identifier semantic ledger `/tmp/a1-21-24-semantic-ledger.json`, source hashes `/tmp/a1-21-24-source-hashes.json`, exact final frozen test module and logs. Original incremental ledger is superseded by parsed final semantic ledger.
