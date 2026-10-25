# A1 9–12: связанные материалы и подготовка сюжетов

author: Codex, агент next_09_12_shared
reviewed_by: parent review pending; separate lesson/lexicon owner coordinated
verification_status: technical_review (partial package, not human acceptance)
date: 2026-10-25
source_notes: actual project source, stable registries, supplied readthrough findings, primary dictionaries listed below

Baseline `5826785ee3f665fac765783ba9a95a5dd3b52655`. Own detached worktree `/tmp/ee-a1-09-12-shared`; parent root worktree was not changed. After preserving the shared-only patch, the lesson-owner patch was applied ONLY in this worktree for targeted integration checks. No commit, push, PR, deploy or merge.

## Deliverables

- `/tmp/a1-09-12-shared.patch`: ten owned source/template files, excluding lesson/lexicon files owned by the other agent and excluding tests.
- `/tmp/a1-09-12-shared-contract.patch`: separate correction of one old overfitted assertion in `tests/test_a1_scaffold_variants.py`.
- `/tmp/ee-a1-09-12-shared/tests/test_a1_deep_09_12_shared.py`: nine new behavioral tests; copy as a new module on integration.
- `/tmp/a1-09-12-shared-semantic-ledger.json`: 53 exact before/after field changes with stable identifiers where available.
- `/tmp/a1-09-12-shared-source-hashes.json`, `/tmp/a1-09-12-shared-integrity.json`: final source hashes, preserved audio/gap assertions and scope evidence.

## Applied decisions

N03/N04: remove unintroduced any from the L9 neutral water question in scaffolds/independent transfer. Keep Is there water? plus a polite Can I have some water, please? request; some does not require the quantity to be small. The prompt no longer insists on «немного».

N05: cold ticket/jacket purchase scaffolds replaced with already introduced sandwich/phone. Conditions, translations and reasons updated together.

N06: Saturday/read cold L11 scaffolds replaced with daily work/drink models, retaining a question and an independent statement about a habit.

Additional confirmed prerequisite gap: spatial in is introduced week8; L9 cold milk/chair models and the base independent writing model had required it at week5. The situation still places learner and guest in the kitchen/room, but the model can answer without naming the place again, or uses known here. Writing explicitly says the room need not be named. The old correct long writing answer with in the room remains accepted; the new base model is There are two books. No word meaning/UID was moved or disguised as already taught.

N11: local independent writing price answers accept It/That full and explicit contracted forms, with three/3. The real independent endpoint is tested for known matches and wrong price, negation, subject and order; unmatched open answers remain needs_review. No global apostrophe expansion.

N17: all five generated milk/water/tea/coffee/juice cards specify an ordinary Is + there question, distinguishing an echo question from the target form. The specific explanation acknowledges the conversational echo alternative instead of declaring it universally ungrammatical. Options, rotations, keys and five distinct contexts remain; real delayed-review POSTs check feedback and correctness for all choices.

N19: micro-review white/read/walk examples replaced with known brown/drink/work examples consistently, not just in a single sample. Early in the morning/evening micro cases use every morning/evening with corresponding translations. Active L11 still offers its original appropriate phrases, but explicitly prepares in the morning / in the evening as whole expressions with translations before their detailed L12 grammar. The scenario coach supplies the same bridge. L9 stray English Here in a Russian explanation was corrected to Здесь. Other active rows, including L13, are unchanged; unchanged error-repair and week6 files were preserved.

N18: poem3 Ten answers a clock question, so N1→N3. Work in go to work is a noun, so D2→S9. Its only work token is not the lexical verb taught by LX-00128 (only verb forms works/worked/working, meaning to do a job); remove that glossary association without deleting or repurposing the UID. In the full line A big cat comes in, in has no noun object and is a directional phrasal particle; P1→X3 after dictionary/registry verification. This is not a rule that every in is a particle. Comes stays in its motion category D4; no class meanings/colors changed.

The poem's English text, IPA and five gap solutions are identical after stripping markup. The target list is only the displayed glossary links in the actual view/template: removal does not remove a gap. The actual gap API checks the five original words and makes no UnitProgress writes, verified with positive/negative requests. We do not claim it previously granted automatic mastery merely because it listed a target.

The supported poem3 theme_ru in course_map now prepares go to work / coffee again / comes in and the recognition-only comes/drinks forms (206/240 chars). Existing introductory paragraph receives one narrowly scoped A1/poem3 condition, replacing its false universal «не вводит новых слов» claim with an honest preparation statement. No new model/field/template block/CSS/geometry was added. Actual HTML tests verify three translated chunks and verb/clock/particle labels. A1 poem2 and a transactional A1+ rendering fixture retain precisely the former introduction. The A1+ fixture is not a claim that an unpublished A1+ poem was audited.

Story2 uses the supported preview field prediction_ru and grammar_ru to distinguish narrative present from habitual every day and prepare recognition of third-person comes/drinks/likes/has. The preview appears before reading, unlike relying only on a sidebar after the text on mobile. Its recorded script/spoken lines, English, roles, plot and new_units are unchanged. Forms are not required to be generated before L13; known alternatives remain available for short retelling.

N20: twister5 metadata no longer claims /æ/, absent from actual IPA/text. Retain dh; preserve text, IPA, warmup, goal and recording lines. This is not a listening verification or a claim that focus_sounds appeared as a visible label.

## Old-test contract correction (separate patch)

The first integrated run had 84 tests with one failure: old test_fifth_pass_questions_match_speaker_and_situation demanded literal any water. It did not verify vocabulary availability and forced a future A1+ word even though Is there water? is an ordinary valid question. Original failure/log retained at `/tmp/a1-09-12-integrated-targeted-before-contract-fix.{log,json}`.

With parent approval, replace that exact-word constraint with a shape check for an ordinary water question (optional some/any) while retaining the some water request. This does not turn any into known vocabulary: the new behavioral vocabulary test rejects unintroduced any in the actual model, and a real blind independent batch verifies question+request submission stays self-reported without fake lexical progress. Tests/CI are not disabled, and no global whitelist/normalization was relaxed.

## New reproducible verification

Same final nine-test definitions SHA256 `9efd5a4c52fc02df5d88d7ad87b327951631d99bffd49c9c732eee43a708b16c`:

- Fresh isolated baseline worktree `/tmp/ee-a1-09-12-shared-before`: 9 tests, 25 failures, no errors. Failures are subtest observations, not a quality score or a claim of 25 independent language errors. `/tmp/a1-09-12-shared-before.{log,json}`.
- Integrated owned-source after: 9 tests PASS, 1.243s test body / 11.414s wrapper. `/tmp/a1-09-12-shared-after.{log,json}`.
- Final integrated targeted: 86 tests PASS, 5.118s body; source contains owned lesson/lexicon patch plus shared changes and corrected old contract. `/tmp/a1-09-12-integrated-targeted.{log,json}`. This is NOT a full-suite result.

Exact argv, temp SQLite filenames, settings/base and test hashes are recorded in JSON. Python interpreter is the parent's existing frozen .venv; dependency versions were not updated. All runs explicitly override both DATABASE_URL and TEST_DATABASE_URL with fresh temporary SQLite paths and config.settings.test. No production connection.

Fresh final guard→migrate→load_content→audit_course runs are in `/tmp/a1-09-12-shared-load-audit.json` with separate logs `/tmp/a1-09-12-shared-{guard,migrate,load-content,audit-course}.log`. Existing course-wide warnings remain visible. Check the JSON exit codes before citing the run.

Earlier draft logs (7 tests; then 9 before the additional in-marker check; early missing-in fixes; the 84-test old-contract failure) are distinct superseded artifacts, not the final snapshot or false PASS.

## Sources actually consulted

- Source lexical chronology and vocab_until/is_known behavior; current lesson schedule and taxonomy registry X3 directional particles.
- American Heritage in, actual complete entry: https://www.ahdictionary.com/word/search.html?q=in (adverbial directional use into the inside).
- Oxford Learner's come in, actual complete entry: https://www.oxfordlearnersdictionaries.com/us/definition/english/come-in (phrasal verb; enter a room/building).
- Oxford Advanced American come in, actual complete entry: https://www.oxfordlearnersdictionaries.com/us/definition/american_english/come-in (phrasal-verb classification; this edition does not list the room-entry sense separately, so it is not cited for a nonexistent definition).
- Cambridge Dictionary blog, actual complete primary article: https://dictionaryblog.cambridge.org/2014/11/19/come-on-you-can-do-it-phrasal-verbs-with-come/ (come in for entering). Cambridge dictionary entry itself returned403; it is not represented as fully read.
- Merriam-Webster come in, actual complete entry: https://www.merriam-webster.com/dictionary/come%20in (intransitive forms, including comes in; no invented American-only or frequency claim).

Original explanations/translations were written for this course; no external exercise or long quotation copied.

## Remaining limits

Full Django/pytest, desktop/390px visual/keyboard/reduced-motion checks, PostgreSQL, real audio listening, human substantive acceptance and learner pilot are not performed here. All are for final parent integration, not PASS by delegation. The scoped template retains geometry code but a longer paragraph still needs visual review. Shared patch may need context-aware application beside existing 5–8 shared-row edits; do not overwrite whole JSON files from this detached worktree. The parent should use the exact semantic ledger to confirm current before values and preserve all unrelated rows.
