# A1 audit: all 500 lexicon entries and 28 lesson exercise keys

Baseline: main at \`b09849d293a16ad8248647b8f3c859c8d7bc81c1\` (2026-10-19).
Scope: 36 A1 lexicon YAML packets, 28 A1 lesson YAML files, 163 original
lesson exercises. Project rules: original course content and IDs are preserved.

## Evidence register

| ID | Impact | Source | Proven finding | Treatment |
|---|---|---|---|---|
| A1-SRC-01 | High: misleading externally verified CEFR label | \`scripts/audit_cefr_evidence.py\` | Previously, any nonempty optimistic \`verification_note\` without one of a few prohibited phrases satisfied the "verified" condition. No URL or matching sense was necessary | Require structured sense label and a traceable HTTPS dictionary entry tied to the actual lemma |
| A1-SRC-02 | High: long-term regression in 500 examples | \`content/seed_lexicon/*.yaml\` | Existing checks verified nonempty bilingual fields but did not guarantee the target word or one of its documented inflections actually appears in its teaching example | Add all-500 coverage: target lemma or declared form must occur in the example; explicitly exempt only the intentionally abbreviated alphabet listing |
| A1-SRC-03 | Medium: false or unbuildable assessment | \`content/seed_lessons/*.yaml\` | Existing tests did not validate draggable word multiset or normalize distractor equivalence for each original lesson exercise | Add a 28-lesson, 163-exercise test for token multiplicity, answer presence, and normalized choice distinction |
| A1-SRC-04 | High: contradictory grammar translations | \`content/seed_lexicon/*.yaml\` | Automated negation parity was not enforced for all learner-facing bilingual examples | Add a 500-entry sweep, requiring an explicit negative meaning where the English example contains an overt negator |

The latter three are **preventive quality gaps**, not claims that every record
was incorrect. No content examples or answers were rewritten without a verified reason.

## Current course counts

- Lexical entries: **500**, as counted from the 36 A1 YAML packets.
- Lessons: **28**; original exercises: **163**.
- Documented sense-specific external records: **2** (some determiner UNKNOWN AMOUNT; eat verb FOOD).
- Lexical source status: **41 partial**, **457 pending**, **2 verified**. Partial does not certify the taught sense; pending is unverified.
- Special teaching cases: \`LX-00401\` shows plural **feet** for lemma foot; \`LX-00187\` is a single full-alphabet unit illustrated with an abbreviated alphabet sequence. They are not automatically corrected into misleading singular or full-length examples.

## Limitations and confidence

1. Evidence fields and URLs are *traceability checks*, not proof that a live source
   currently supports the sense. Only the two existing Cambridge-linked senses
   were manually cross-checked against their publicly accessible entries
   during this pass. New "verified" records still require a human sense-level review.
2. The example-to-lemma and overt-negation contracts are intentionally limited:
   they do not understand tense, register, politeness, conversation context or
   all possible semantic entailment. Passing means structural consistency, not
   natural idiomatic American English.
3. The lesson checks establish technical solvability of fixed answers, not that
   all distractors are linguistically wrong or that free answers have sufficient
   independent assessment.
4. Real audio listening, phone/TalkBack testing, content comprehensibility studies
   and a complete external CEFR sense-by-sense audit are not provided by CI.
5. All existing learning IDs, prompts, English/Russian content, and rubric semantics
   remain unchanged unless a specific independently supported defect is found.

## Reproduce

- \`uv run pytest -q tests/test_cefr_evidence.py tests/test_a1_corpus_alignment.py\`
- \`uv run python scripts/audit_cefr_evidence.py --strict\`
- \`uv run pytest -q\`
- \`node --test tests/js/*.test.cjs\`
- \`uv run python manage.py migrate\` then \`load_content\` and \`audit_course\`

Results must be linked to the **final PR commit** rather than inferred from
a previous merge or from the existence of code. Project score is not automatically
increased to 9.5/10 without field tests and independent editorial review.
