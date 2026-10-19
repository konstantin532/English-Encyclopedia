# A1 grammar scope — audit and placement candidates (2026-10-19)

Baseline: `main` at `68fd883b1cf416317984eb0daa71e0ef0f66502b`; plan: `content/manifests/weeks_plan.yaml`. **Planning note, not course expansion.** No new weeks, grammar lessons, vocabulary certification, or exercise banks are added in this PR.

## Reference and evidence limits

- [English Grammar Profile](https://englishprofile.org/?menu=english-grammar-profile): searchable descriptions of grammar observed at proficiency levels. Its presence in a category does **not** make every construction in that category mandatory at A1. Exact learner examples and subcategories need an editorial verification before labeling any specific use as EGP-A1.
- [Oxford 3000](https://www.oxfordlearnersdictionaries.com/about/wordlists/oxford3000-5000.html): graded **vocabulary**, not a grammar syllabus. Do not use its word labels to certify `Present Continuous`, `was/were`, or pronoun syntax.
- [CEFR scope](https://www.oxfordlearnersdictionaries.com/about/wordlists/cefr.html): describes communicative proficiency, not a canonical list of mandatory grammar points.

Evidence basis: the fourteen `grammar_ru` descriptors in `weeks_plan.yaml`, with a sanity check against the already documented dialogue usage. This is not a line-by-line independent EGP-entry certification.

| Candidate | Planned explicit teaching in current A1 | Recommendation, **not implemented** | Editorial caveat |
| --- | --- | --- | --- |
| Present Continuous for actions happening now (`I'm looking`) | No explicit week; isolated episode narration currently risks misleading habitual Present Simple | A1+ week 1, immediately contrast with A1 weeks 6–7 habitual Present Simple; alternatively assess inserting a tightly scoped A1 lesson after week 10 only if A1+ gate demands it | Confirm simple affirmative and question senses in EGP; new lessons require curriculum redesign and trials |
| Past `be`: `was/were` | No explicit week | A1+ week 2 after present/present-continuous contrast, or a small A1 week 14 diagnostic if independent coverage is required | Do not mix with general Past Simple before its own progression |
| Time prepositions `at / on / in` | **Partly covered:** `at seven` week 6, `on Saturday` and `in October` week 10 | A1 week 10: one explicit **contrast/retrieval** task combining all three; no new grammar chapter needed | This is a connection/assessment gap, **not** an absence of all three |
| Object pronouns `me/him/her` | Not listed as a target in the fourteen `grammar_ru` descriptors | A1+ week 1 after subject pronouns and possessives; consider an A1 week 9 speaking micro-task if editor confirms prerequisite vocabulary | Existing incidental tokens elsewhere do not establish independent production |
| Imperatives (`Turn left`, `Take a seat`) | **Present** in week 8 directions and used again in subsequent weeks | A1 week 8: label the already-taught request/direction pattern and test `go/turn` independently; **not missing** | Distinguish positive directions from negative commands that may be later-stage |

## Decision rule

No feature should be described as a confirmed missing **CEFR A1 requirement** solely from the above table. First review exact English Grammar Profile can-do/example records; inspect the full lesson, interactive practice and independent assessment; then approve a scope change. Present Continuous before its lesson is **not introduced** here. No A1+ content has been created.

## Speech tasks on the existing fourteen weeks

Every existing `mission_ru` was inspected. Weeks 2–14 already contain more than one learner-produced oral act (for example, describing a situation and asking somebody a question), even when expressed in one paragraph. Week 1 was the clearest gap: repeating one's own name three times was not a second situation. It now explicitly includes two independent, open-ended speaking situations without answer options. Roleplay and existing lesson exercises remain unchanged.

## Audio caveat

Changing authoring `script.text` or `script.spoken` does **not** regenerate previously synthesized audio or prove that existing audio matches updated lines. Rebuild impacted audio in a controlled environment, run `scripts/audio_readiness.py`, and listen to the resulting recordings before deployment. Do not mark human review automatically.
