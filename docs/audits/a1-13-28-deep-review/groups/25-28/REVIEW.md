# A1 25–28: scoped implementation and evidence

Base: `5826785ee3f665fac765783ba9a95a5dd3b52655`. Detached worktree `/tmp/ee-a1-25-28`; no publishing or merge. This report concerns these four lessons, not acceptance of the whole course.

## Decisions

|Lesson|Reviewed related surfaces|Implemented|
|---|---|---|
|25 a1-can-skills|Seven layers, pronunciation/contractions, EX140–145, four translations, study/study_plus lexicon, week13, active/scenarios/repair25, scaffold, understanding, micro/delayed review|Can + **verb**, not an action-only classification; language article scope in lesson and LX243; strong can scoped to the affirmative short answer; EX143 accepts reversing the order of the same two languages. Generated Russian meeting context uses **На встрече**.|
|26 a1-why-because|Seven layers, pronunciation/contractions, EX146–151, four translations, same week13/lexicon links and all parallel lesson26 surfaces|Like explained as what someone likes, not what they do. Ordinary full Why question scoped; translation hint explicitly shows Why + are + you instead of an unexplained general question order.|
|27 a1-bus-ticket|Seven layers, pronunciation/contractions, EX152–157, four translations, travel/travel_plus lexicon, week14, active/scenarios/repair27, scaffold, understanding, micro/delayed review, assigned poem7|EX155 park route no longer credits a memorized **Park Street** phrase; EX156 arrival no longer credits **leave**. LX255 destination substitution respects articles; LX258 t reduction is optional. Generated destination prompt works for both masculine and feminine Russian nouns. Understanding guide specifies does + go rather than deriving a universal helper rule from “action.”|
|28 a1-review-everything|Seven layers, pronunciation/contractions, EX158–163, four translations, travel_plus/story05 lexicon, week14, active/scenarios/repair28, scaffold, understanding, micro/delayed review, assigned story5|EX162 sunny answer no longer credits the absent noun weather. LX470 trip does not require a return journey; LX477 distinguishes selecting an from requiring an article before every umbrella. Poem7 open in Is it open? uses adjective J2, not verb D2.|

Already correct and retained: can vs do short-answer contrasts; because/because of explanation and discourse context; teach me to read support before review; ordinary arrive at/in contrast; role-based language ability; taking a bus/ordering coffee; 7-layer structure. Noun subclasses remain thematic. LX178 is the actual phrase **It's on the right.**, so its translation-progress binding was retained. The mixed **My name's Anna. I am from Russia.** answer already passes because its existing local key contains I'm and practice normalizes that pronoun contraction; no redundant answer was added.

No global grader or contraction normalization was changed. Negative regressions preserve negation, ownership/origin, the required question order, and prevent replacing the requested two-language reply with a Russian-only extra sentence.

## Evidence: new executions

Runtime: existing parent lockfile-prepared `.venv/bin/python`; no dependency versions or lockfiles changed. All commands run with `DJANGO_SETTINGS_MODULE=config.settings.test` and explicit **both** DATABASE_URL and TEST_DATABASE_URL pointing only into `/tmp/a1-25-28-evidence/`. Guard for the migration/load/audit fixture asserted SQLite engine and the exact resolved fixture path before any operation. Django test runner creates/destroys its own isolated test database.

Command prefix `P=/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python` (explanatory abbreviation only).

- Clean detached base `/tmp/ee-a1-25-28-before`: `$P manage.py test tests.test_a1_deep_25_28 --noinput`: **6 tests, FAIL with 7 failures**. Log `/tmp/a1-25-28-evidence/before-final-frozen.log`. Failures are two valid language orders, three false progress bindings, the actual poem HTML adjective marker and generated Russian meeting preposition. These are behavioral failures, not missing imports/data.
- Edited worktree: `$P manage.py test tests.test_a1_deep_25_28 tests.test_a1_editorial_week13_14 --noinput`: **15 tests PASS**. Log `/tmp/a1-25-28-evidence/after-final.log`. The six new tests are identical to those copied to the clean base: SHA256 `4da2d27a920c4fea1bfb1c089211269c8b4414e17cb33c6571fa2a3fef70f0e9`.
- Guarded Django `call_command('migrate', interactive=False)`, `call_command('load_content')`, `call_command('audit_course')`: PASS; final log `/tmp/a1-25-28-evidence/load-audit-final.log`. Loaded1047 units/60 lessons/11 stories/7 poems/30 weeks. Audit: **zero errors**, warnings retained for unverified CEFR, A1 story length and cross-level recycling below target. Story5 99 words,95% known. No audit thresholds weakened.
- Python `yaml.safe_load` over all `content/**/*.yaml`: PASS. JSON parsed while building semantic ledger. `git diff --check`: PASS. Stable lesson slugs/order/weeks, EX UIDs/order, seven numbered layers and poem's marker-stripped body compared to base: PASS.

An early intermediate run caught two unquoted YAML explanations containing colons. Quoting was corrected before the final valid load/test/audit; those setup failures do not count as content-test passes. No earlier GitHub Actions log is presented as a new execution.

## Sources for substantive language decisions

Consulted directly on2026-10-25:

- https://www.merriam-webster.com/dictionary/trip — noun journey/voyage; return is not part of the general definition (distinct round trip).
- https://www.merriam-webster.com/dictionary/open — adjective for not shut/available; supports contextual adjective marker in **Is it open?**.
- https://owl.purdue.edu/owl/general_writing/grammar/using_articles.html — sound selects a/an; names of languages and streets; the can identify specific count/noncount referents. Supports scoped language/umbrella/destination teaching.
- https://owl.purdue.edu/owl/general_writing/grammar/articles_a_versus_an.html — phonetic basis of a/an.

Frequency claims were not invented. No British variant was mislabeled an error.

## Limits / integration handoff

Full suite, PostgreSQL, real desktop/mobile browser pass and CI: **NOT RUN by this scoped child owner**, deferred to parent integration; actual authenticated poem HTML is covered by the new server-response regression. No browser screenshot or audio listening is claimed.

No recorded English utterance changed: poem7 plain body is byte-identical after markers are removed; only its contextual marker changed. Week13/14 scripts, story5 text/spoken, poem words/pronunciation/gaps and lesson pronunciation text/IPA remain unchanged. Modified Russian explanatory notes, lexical metalanguage and additional accepted key variants are not claims of regenerated/listened audio. Existing real audio files were not available/validated in this worktree. No audio regeneration is justified by a marker-only poem edit.

`SEMANTIC_LEDGER.json` contains complete before/after values for every changed structured content field, selected through stable UID/slug/n/order/number where available. `SOURCE_HASHES.json` includes all changed content hashes; `COVERAGE_HASHES.json` identifies the direct read set. Parent should review/apportion the shared manifest only at these four slugs. No IDs, primary lexical classes, palette meanings, accounts/auth/schema/geometry, other levels or CI were edited.
