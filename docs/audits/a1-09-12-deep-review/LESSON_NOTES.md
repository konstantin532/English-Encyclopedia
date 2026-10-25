# A1 9–12: owned source implementation (not complete integrated acceptance)

Baseline: `5826785ee3f665fac765783ba9a95a5dd3b52655`. Worktree `/tmp/ee-a1-09-12-readthrough`, detached; root workspace was not edited. No commit, publication, merge or deploy.

Patch: `/tmp/a1-09-12-owned.patch` (six content files and one new Python test module). Exact 32 semantic before/after fields: `/tmp/a1-09-12-owned-semantic-ledger.json`. Identity evidence and final source hashes: `/tmp/a1-09-12-owned-integrity.json`.

## Implemented decisions

- N01: L11 points third-person -s teaching to lesson13 nextweek, not the actual nextlesson12.
- N02: milk dictionary scopes noncount to substance and acknowledges portions, matching existing L9 explanation.
- N07–N10: local accepted lists gain full there’s water replies, five-dollar digit forms, shared-subject and-coordination, and breakfast-at-eight digit forms. Existing correct answers retained. No global normalizer change.
- N12–N15: 17 bindings no longer award unrelated full-phrase progress. EX59 YesIdo and EX63 bareat keep real ExerciseAttempt records but have empty units, rather than falsely certifying work/every or a full Igetupatfive phrase. No new lexical meaning/UID and no repurposed class. Existing lesson units, IDs and review_of links remain.
- N16: watch is not limited to moving objects; listen does not invariably require to when no object is stated; dinner means main meal, often evening, with context-specific timing.
- N19 PARTIAL: white removed from L9 color list because its lexical introduction is week12. Shared micro cases remain for parent integration.
- Related consistency fixes: EX47 explanation distinguishes bare Yes there is (no contraction) from full there’s water; EX61 prompt explicitly allows and to express its two thoughts. L11 unsupported almostalways don’t claim scoped; have breakfast explained as an idiom for eating breakfast, not literal ownership.

## Not implemented here

N03–N06, N11, N17–N18, remaining N19, N20 affect shared JSON/week/story/poem outside assigned ownership. These remain in the unchanged 20-group readthrough packet for root. No narrative present was labelled erroneous. Lexical noun work and temporal at meanings were not silently reassigned to existing verb/place IDs.

Static progress associations describe the canonical task target, not perfect semantic parsing of every accepted paraphrase. In particular preserved Do you have milk? alternative and some/no variants do not prove every token of the canonical construction was independently produced. No business-logic rewrite or retrospective learner progress recalculation was attempted.

## Reproducible new verification

Same frozen 13-test module SHA256 `a8733a4a3c4605e437c74ab4191d0de17fc07f12a98b75c53fb413ac3fdd6e37`:

- Base separate worktree `/tmp/ee-a1-09-12-regression-base`: 13 tests, 25 failures, no errors. Wrapper11.882s. `/tmp/a1-09-12-targeted-before.log` and `.json`.
- After: 13 tests OK, no errors. Wrapper9.913s. `/tmp/a1-09-12-targeted-after.log` and `.json`.
- Final after small prompt/explanation alignment: all same13 plus21 relevant existing tests =34 tests OK, body6.954s/wrapper19.316s. `/tmp/a1-09-12-related-after.log` and `.json`.

Exact new comparable command:

```
/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python manage.py test tests.test_a1_editorial_deep_09_12 --noinput
```

Related modules: tests.test_a1_editorial_week06, tests.test_grammar_answer_integrity, tests.test_a1_pedagogical_continuity, tests.test_a1_second_pass. Full exact argv captured in JSON.

Each run used explicit config.settings.test plus fresh SQLite paths prefixed ee-a1-09-12-, DATABASE_URL and TEST_DATABASE_URL both overridden; no production connection. New tests submit to actual authenticated exercise/practice APIs, verify known positive keys, changed number/subject/drink/meal/negation/order negatives, and actual UnitProgress/ExerciseAttempt persistence. A finite unmatched transfer answer remains needs_review, not a declaration of ungrammaticality.

Fresh isolated guard→migrate→load_content→audit_course: all exit0, audit “Ошибок нет.” Commands, temp database and times in `/tmp/a1-09-12-load-audit-results.json`; full `/tmp/a1-09-12-{guard,migrate,load-content,audit-course}.log`. Existing course-wide warnings retained, including story lengths and A1-to-A1+ recycling.

An earlier draft before-run had zero tests due to my incorrect create_user call in test setup. It was fixed before freezing the comparable module; draft setup-error log/JSON retained separately, never counted as a course defect.

## Integrity and limits

YAML parsed; seven layers, all stable IDs, canonical answers, old accepted answers, ordering and review links retained. Lexical UID/lemma/class/forms/IPA/example texts unchanged. Four lessons have24 main exercises and16 translations. Application/schema/auth/CI/lockfiles untouched.

No full course test run for this owned package, browser desktop390px, real audio listening, PostgreSQL or human learner pilot. These are not PASS. Parent must integrate shared-source fixes, independently review source and run the complete installed suite on the integrated state.

Sources actually consulted for substantial lexical decisions: Merriam-Webster dinner (https://www.merriam-webster.com/dictionary/dinner), American Heritage watch (https://www.ahdictionary.com/word/search.html?q=watch). Cambridge listen grammar primary search exposes objectless “I’m listening”; full grammar URL403, not represented as fully read. Milk substance/portion distinction already exists in current L9 layer6 and is reconciled rather than invented as a new ban or meaning.

## Final boundary clarification after parent challenge

After rereading complete L11 layer6 and L13 layers1–6, the L11 preview is now explicitly an affirmative statement about a habit, scoped to most verbs (-s/-es). The already-known exception be→is is named without introducing a new unexplained term; detailed forms/questions/negatives stay in actual lesson13. This avoids teaching a universal -s rule that would later conflict with doesn't + base form. No lesson13 file changed.

The same frozen13 tests plus21 related tests were rerun on this final text:34 tests OK. Full final log `/tmp/a1-09-12-boundary-final.log`, exact command/timing/test hash `/tmp/a1-09-12-boundary-final.json`. Patch, semantic ledger and source hashes above were regenerated. The earlier34-test and load/audit results describe the preceding text; final integrated load/audit/full suite remain parent's responsibility. This is a source clarification, not a new grammar-engine behavior.
