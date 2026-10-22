# A1: pilot of context-sensitive explanations and verb classes

Status: focused, unmerged review changes (not a full teacher-grade course certification).

## Baseline

- Repository: `konstantin532/English-Encyclopedia`
- Base branch: `main`
- Base commit: `c4e2ab9d1283e219f84525de26845166fbd14db3` (2026-10-22)
- Review scope: selected A1 lexicon entries, be lesson 2, dictionary detail page, taxonomy legend and new regressions.
- A1-wide inventory, pronunciation listening, browser accessibility, CEFR sense review and teacher evaluation: **not performed** in this pilot.

## Observations and evidence

| Item | Before | Correction | Evidence |
| --- | --- | --- | --- |
| Dictionary passport | Class code without its Russian meaning | Display code **and** semantic class name; link to complete legend | `templates/lexicon/detail.html`; `apps/taxonomy/registry.py` |
| Grammar label | No separate inflection-type explanation next to D-class | Render `irregular`, `regular` or `modal` only if explicitly tagged; otherwise state unverified | `apps/lexicon/models.py`, `content/seed_lexicon/a1_w06_day.yaml` |
| `go`, `work`, `eat` | Forms present but morphological feature missing | Tag go/eat irregular, work regular without reassigning D4/D2 | `content/seed_lexicon/a1_w06_day*.yaml` |
| `home` and `at` | Dictionary notes did not distinguish `I'm home` / `I'm at home` | Explain that both can describe someone's location; avoid the invented indoor/outdoor contrast | `content/seed_lexicon/a1_w01_nouns.yaml`, `a1_w01_core.yaml` |
| Be lesson 2 | Already covered the pair but did not explicitly explain interchangeability | Explain the contexts and clarify the adverbial use of `home` | `content/seed_lessons/a1_w01_l02_be.yaml` |

The class D1–D10 means a **semantic / functional teaching category**, not English regular/irregular conjugation. The fixed taxonomy ID meanings and palette are preserved.

### Reference for home

- Cambridge Grammar, *Prepositions: home*: https://dictionary.cambridge.org/us/grammar/british-grammar/prepositions-home
- Cambridge Dictionary blog, *Staying at home, going home or working from home* (22 July 2020): https://dictionaryblog.cambridge.org/2020/07/22/staying-at-home-going-home-or-working-from-home-using-the-word-home/
- Cambridge Grammar, *House or home?*: https://dictionary.cambridge.org/us/grammar/british-grammar/home

These sources establish `at home`, bare `home` after be/stay in American English, and `go home` without `to`. They do not establish a rule that bare `home` means "outside the house".

## Verification plan and limits

Source-level verification: read back modified files, check preservation of lexicon IDs and exact feature markers.

New regression tests: `tests/test_a1_usage_clarity.py` covers selected metadata, text explanations and dictionary HTTP pages. **Do not claim they pass until executed.**

Recommended commands in an environment with project dependencies:

```bash
uv run python manage.py load_content
uv run python manage.py audit_course
uv run python manage.py test tests.test_a1_usage_clarity
uv run python manage.py test tests --parallel auto
```

If frontend or templates change, inspect the dictionary and taxonomy pages using a browser and a 390 px viewport. Track PASS, FAIL and BLOCKED separately.

## Remaining work

A full A1 audit must separately inventory all 500 lexical units, 28 lessons, 14 weeks, 5 stories, poems, assessments and interaction data. Inspect each explanation and record direct evidence. Expand morphology classifications only after validating each verb. Do not infer regularity for every verb that lacks an `irregular` flag. Ask a qualified teacher to review genuinely disputed American-English usage. A green CI run cannot replace a human linguistic audit.
