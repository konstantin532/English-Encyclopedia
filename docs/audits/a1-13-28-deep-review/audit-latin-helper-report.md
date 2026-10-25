# Related audit tokenizer defect — separate helper patch

Base: 5826785ee3f665fac765783ba9a95a5dd3b52655. Independent worktree /tmp/ee-audit-latin-helper. Three files only: apps/publishing/audit.py, content/seed_lexicon/a1_w06_day.yaml, tests/test_audit_latin_tokens.py. Patch /tmp/audit-latin-helper.patch.

The ASCII tokenizer incorrectly split a legitimate new EX-00083 accepted café spelling into unknown caf. It could also mistakenly certify unknown piñata as two known ASCII fragments. Candidates now preserve complete words and normalize NFC; pure non-Latin explanations stay ignored, mixed-script words with any Latin character stay visible as unknown. All three audit WORD.findall consumers route through text_tokens. Vocabulary storage/token keys/recycling use the same NFC identity, without accent folding. No changes to answer grading, thresholds, normalization of 's, CI, registry, schema or accounts.

LX-00131 retains cafe, UID, meaning, class, IPA and unit count; adds café/cafés forms. Searches found no duplicate accented lemma/forms. Existing usage_note already recognized cafe/café. Primary AmE reference actually opened: https://www.merriam-webster.com/dictionary/cafe (café, variant cafe). No claim of frequency or British exclusivity.

## Reproducible evidence
Frozen test SHA256 608ffc2a07e5af1a7a1d8b74cbf73f763d17a606309c2187d31d37c39d360211, identical definitions before/after: clean base 10 tests/8 failures; patched source 10 PASS. Tests cover NFC/NFD, non-composable diacritics, explicit form registration, unknown piñata, résumé≠resume, pure Russian, cаfe with Cyrillic а, old contractions/punctuation and real run_audit with valid plus invalid keys. Earlier nine-test draft is superseded. Commands and DB paths: /tmp/a1-13-16-targeted-latin-frozen-{before,after}.json; logs same stems.

Actual manage.py audit_course on two fresh guarded SQLite DBs, after migrate/load_content and injection of exactly the same new accepted café key: before warns “Незарегистрированные слова ... caf (a1-where-is-prepositions/задание 4)”; after this warning disappears. Both exit0; unrelated CEFR/story-length/recycling/collocation warnings remain. This is not a whitelist or audit weakening. Exact command/DB/exit metadata: /tmp/audit-latin-course-results.json; individual logs /tmp/audit-latin-course-{before,after}-{guard,migrate,load,inject-key,audit}.log.

No production DB used. Full suite and integrated browser checks delegated to parent; no audio was generated or verified. No publication/merge performed.

## Existing related regression run
`manage.py test tests.test_audit_latin_tokens tests.test_a1_recycling tests.test_p0_audit_regressions tests.test_audit_weeks tests.test_audit_fifteen --noinput`: 42 PASS, body139.746s, wrapper149.236s, isolated /tmp/ee-a1-13-16-latin-related-dr4pa0hh/fixture.sqlite3. New exact metadata /tmp/a1-13-16-targeted-latin-related.json and log same stem. Staticfiles directory warning is from the independent source worktree; system check reports no issues. Both final patches pass git diff --check.
