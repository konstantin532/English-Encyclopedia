# A1 13–16 — core lesson and lexicon implementation

author: Codex, independent owned-source agent
reviewed_by: parent integration pending; shared-source owner coordinated
verification_status: technical_review (targeted only)
date: 2026-10-25
source_notes: actual current source and before/after; American dictionaries listed below; no human acceptance

Base `5826785ee3f665fac765783ba9a95a5dd3b52655`; separate worktree `/tmp/ee-a1-13-16-owned`. Eight content files plus two new regression modules (thirteen API/HTML methods and two contextual-label methods). Parent source tree, shared manifests, weeks/stories/poems, schema, accounts, authentication, CI and registry are not changed.

Deliverables: `/tmp/a1-13-16-owned.patch`, `/tmp/a1-13-16-owned-semantic-ledger.json` (52 exact semantic fields), `/tmp/a1-13-16-owned-integrity.json`, new module `tests/test_a1_editorial_deep_13_16.py` inside that patch. Canonical answers, all old accepted answers, UID, order, review_of and seven layers preserved. No occupied class/marker/palette definition is changed.

## Implemented

- L13 unsupported almost-always contraction claim replaced with contextual conversational and full-form distinction.
- Local EX73 keys allow start-work digit/clock variants, preserving partial-slot subject and hour; EX79 adds explicit mother/mom noun contractions with at/in hospital; EX83 adds explicit cafe/café full and contracted location forms. Global normalization untouched. The new tests reject wrong owner, job, polarity, hour, subject and order.
- Four main bindings no longer credit unrelated targets: Mia/cafe response no longer credits Tom-at-home; No,she reply no longer credits No,he; starts slot no longer credits nurse supplied in the prompt; doctor reply no longer credits teacher phrase.
- Fifteen practice bindings no longer award irrelevant school questions, office statements, price/direction or different-person phrases. Real authenticated API requests verify actual UnitProgress sets and ExerciseAttempt retention. Static bindings represent the canonical task target, not semantic parsing of every paraphrase.
- Existing L16 personal-pronoun table marks object her as T8, not possessive determiner T3. No new object-pronoun lesson/section introduced. Actual lesson HTML checks the delivered label, not a phrase in the YAML file.
- L14 -er occupational model scoped to some names and examples, not a universal word-formation algorithm. Profession article note scoped to the full construction rather than a blanket claim covering all jobs and fragments.
- Lexical explanations reconciled: nurse is not confined to a hospital; farmer is not merely anyone who has a farm; job is a countable job/position, not necessarily a physical workplace; workplace in an office does not require current physical presence inside; American patient in the hospital does not ban work at/in a hospital.
- Pronoun I/me note now follows grammatical role rather than position at the beginning/after a verb. next to t reduction scoped to quick speech; polite sorry versus excuse me usage not made exclusive.
- between A and B uses and in that model, but between does not universally require and; spatial meaning does not impose a universal two-only rule. across from does not inherently require a street; opposite is also valid American English, not a British error. EX85 expressly practices the learned two-word expression, without expanding accepted to unintroduced opposite.
- The ordinary noun park is introduced week10; early proper-name Park Street does not establish its meaning. Core explanatory example, EX85 display/context/explanation and the lexical across-from example consistently use already-known school. The answer across from remains unchanged.

## Audio implications

Plain English changed only in L15's illustrative across-from example / EX85 displayed fragment and LX-00340 example (park→school); these exact fields are in the ledger. Dictionary detail template `templates/lexicon/detail.html` renders the example and has no example audio pointer/control; LexicalUnit has no audio field. `apps/api/views.py:recall_unit` includes example_en in textual feedback. Searches of the audio generation scripts did not find a lexicon example_en or exercise prompt/answer recording input. This source inspection does NOT prove that no external/older recording exists. If an external recording of these particular examples is used, it must be refreshed from park to school. No weekly dialogue, story, poem, IPA, sound-note example or prerecorded script file was changed. Actual audio listening is NOT performed.

## Rejected / bounded findings

- Map S4→S2 was initially proposed, then rejected after reading the actual registry and SemanticClass model. S4 is thematic «Места и город», not a strict ontological category of buildings; a city map can legitimately belong there. Original LX-00346 class S4 and S4 tokens are preserved. No color preference is presented as a language norm.
- Valid American opposite is not added as a hidden exception or future-vocabulary whitelist. The explicit target expression narrows this exercise; unlisted open responses remain needs_review rather than certified language errors.
- Existing review_of links are retained. L16/P4 asking where the bank is has no exact main exercise in L16; order4 is a related directions task, not an exact question recheck. This limitation is not masked by a fake exact-match claim.
- Existing at/from home and near/next-to alternatives preserve their contextual differences. Static unit associations cannot certify that every accepted paraphrase overtly produced each canonical word.
- Driver's definition remains in this lesson's occupational meaning; no false claim is made that every person driving must be professionally employed.

## New verification

Final frozen thirteen-method SHA256 `de2e0b41e5b0cfead4740de9932f6299573acf62aa3ed30b48858ec97b519188`:

- Same module on clean base worktree: 13 tests, 28 failures, no errors. `/tmp/a1-13-16-targeted-before-frozen.{log,json}`.
- Same module on final owned source: 13 tests OK. `/tmp/a1-13-16-targeted-after-frozen.{log,json}`; body0.421s/wrapper11.793s.
- New13 plus relevant existing modules: 49 tests OK, body10.993s/wrapper24.606s. `/tmp/a1-13-16-related.log`; exact argv/timing in `/tmp/a1-13-16-final-checks.json`.
- Fresh isolated SQLite guard, migrate, load_content, audit_course: all exit0; audit reports «Ошибок нет», preserving existing broader-course warnings. Logs `/tmp/a1-13-16-{guard,migrate,load-content,audit-course}.log`.
- Source integrity verifier `/tmp/verify-13-16-owned.py`: PASS; seven layers, stable IDs, old answers and registry/locks preserved. Scoped git diff --check: PASS.

Each run overrides both DATABASE_URL and TEST_DATABASE_URL with a new temporary SQLite filename and config.settings.test. No production connection. Baseline/after definitions are identical; failure counts are subtest observations, not a quality score or independent language-error count.

Earlier logs named before/after/before-final/after-final are superseded drafts: one HTML parser accidentally included an untyped translation span, and the rejected map hypothesis also affected draft expectations. These are NOT the final comparable evidence. Final frozen logs are expressly suffixed before-frozen/after-frozen.

No full Django/pytest, desktop/390px visual check, real audio, PostgreSQL or human pilot performed by this agent. Parent must integrate shared materials, validate exact before values, then run the full installed suite on that integrated snapshot. No commit, push, PR, merge or deploy performed.

## Primary sources actually opened

- Merriam-Webster nurse: https://www.merriam-webster.com/dictionary/nurse — nursing profession not restricted to hospital employment.
- Merriam-Webster farmer: https://www.merriam-webster.com/dictionary/farmer — cultivating/raising animals rather than bare ownership.
- Merriam-Webster across from: https://www.merriam-webster.com/dictionary/across%20from — opposite side, with a table example, not a street-only rule.
- Merriam-Webster opposite: https://www.merriam-webster.com/dictionary/opposite — prepositional opposite and American-edited examples; no invented frequency or British-only label.
- American Heritage between: https://www.ahdictionary.com/word/search.html?q=between — plural complements and forms without and.
- Project registry and models — exact thematic S4 and personal-pronoun T8 semantics.

Explanations are original paraphrases; no external exercise or long dictionary quotation copied.


## Additional confirmed contextual side labels before final freeze

Parent challenged the individual right/left tags inside on the right/on your left. Primary American dictionaries confirm noun side/location senses: Merriam-Webster right noun5b with an on-his-right example; left noun1b; American Heritage right noun2a/b. The full on-phrase is adverbial, but the word following the determiner names a side and is a noun. This is not the thematic-map preference rejected above.

Five existing fields (six tokens) now use contextual S4 for side names in on the right/on the left: L15layer4; L16layer1 andlayer5; lexical example LX00169 andLX00344. A short explanation in existing L16layer2 contrasts noun side with directional adverb Turn left. No English string or IPA changes in these replacements; no new grammar section. Primary directional units LX00168/LX00169 remain A3, with their UID/meaning unchanged. Their definitions already include both directional/positional meaning, so existing bindings are retained; progress does not certify every contextual POS.

New separate two-method actual lesson/dictionary HTML test SHA256 `84d4e218f23a440ebe4e7a6fbe99977f72c4391e12023cb5ab4a59d8c8337ba2`: clean base has4failures; after2PASS, identical definitions. Exact evidence `/tmp/a1-13-16-targeted-side-{before,after}.{json,log}`. Original thirteen-test module remains byte-identical.

Final combined related run is now51tests OK, body10.835s/wrapper20.569s; fresh isolated guard/migrate/load/audit all exit0 on the same final source. Current results retain `/tmp/a1-13-16-final-checks.json` and corresponding logs; old49 results copied to `/tmp/a1-13-16-pre-side-*`, not misrepresented as final. Full patch updated in the same path. For a worktree with the old46-field patch already applied, use incremental `/tmp/a1-13-16-side-only.patch`.

Source references actually opened: https://www.merriam-webster.com/dictionary/right ; https://www.merriam-webster.com/dictionary/left ; https://www.ahdictionary.com/word/search.html?q=right . The AHD left page was inaccessible, not counted as read. No frequency claims or external long quotes. Shared owner coordinates the same role correction in week8 andpoem4; those files remain outside this patch.


## Final standalone dictionary bridge (2026-10-25)
Two existing usage_note fields for LX-00168/LX-00169 now distinguish directional Turn left/right (adverb) from on the left/right (noun naming a side). Primary A3 classes, all IDs, English examples and IPA retained. Final semantic ledger: 54 fields across eight owned source files. Same 13+2 frozen tests retained. Latest isolated migration, load_content, audit_course all exit0; 51 related tests PASS (body9.913s). Audit still showed false caf warning pending separate Unicode helper patch; no valid café answer removed.
