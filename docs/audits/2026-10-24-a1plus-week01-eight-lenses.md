# A1+ Week 1 — focused editorial review (eight analytical lenses)

**Base:** `main` at `8ebdd44b8f037ef04b143e75aeef2e4c70c2395e`.  
**Scope:** `a1p_w01_l01_present_continuous.yaml`, `a1p_w01_l02_video_call.yaml`.  
**Overlap check:** open PR #105 does not modify these lesson files (checked 2026-10-24).

This is one assistant systematically applying eight review perspectives, **not**
eight independent humans or separately running AI agents. The review does not
certify learner comprehension, native-speaker frequency, or the whole course.

## 1. Original issue → learner consequence → targeted change

| Material | Before | Why it matters | After |
|---|---|---|---|
| Present Continuous, practice 2 | «Она прямо сейчас пишет письмо», but only the version without `now` / `right now` and the corresponding contraction was accepted | The time qualifier explicitly invited by the Russian prompt could cause a correct answer to be marked wrong | Accept `She is writing a letter right now.` / `She's writing a letter now.` and other corresponding forms |
| Present Continuous, practice 4 | «Мы сейчас убираем кухню», but answers with `now` were not listed | Same mismatch between natural paraphrase and checking key | Accept full/contraction + `now` / `right now`; keep old accepted answers |
| Video call, layer 2 | Etymological detour about *video*, *camera*, *miss* | The paragraph did not help distinguish two easily confused communicative goals on a call | Contrast `Can you hear me?` (audibility) and `Are you listening to me?` (attention); explain `hear` vs `listen to` and `I'm hearing you` nuance |

The new explanation follows the earlier Present Continuous lesson rather
than introducing an unrelated grammar topic. Existing story characters, other
layers, exercises, unit IDs and markers are unchanged.

## 2. Eight lenses and independent challenges

1. **ELT Materials Writer:** Replace the less immediately useful digression with a call-specific meaning contrast; retain the simple dialogue context.
2. **Applied Linguist:** `hear` describes sound reaching the ears; `listen to` describes directed attention. `I can hear you` is appropriate for checking a call. `I'm hearing you` is *not* claimed to be impossible in all senses.
3. **Corpus Linguist:** No corpus sampling was performed; do **not** claim a measured frequency advantage or native-speaker survey.
4. **SLA Researcher:** Contrasting related expressions may help transfer; this is a hypothesis requiring real learners, not demonstrated learning gain.
5. **Psycholinguist:** Keep the contrast close to the call and avoid lengthy terminology; cognitive-load reduction is an editorial judgment, not measured.
6. **Instructional Designer:** Accept answers that correctly preserve time meaning, and test the actual check endpoint with positive and negative examples.
7. **Popular Science Writer:** Explain the distinction through a concrete question: “Does the sound reach me?” vs “Is the person paying attention?”
8. **Philologist:** Prefer natural, short Russian explanations; avoid deriving modern usage rules from speculative word-history analogies.

**Skeptical-teacher challenge:** Is the contrast independently assessed?
Not yet: existing six exercise slots cover audibility but not a new
free-response `hear` versus `listen` transfer task. Adding one requires
a broader lesson-design review to preserve pacing and scoring.

## 3. Evidence and checks

- Cambridge Grammar Today, [Hear or listen (to)?](https://dictionary.cambridge.org/us/grammar/british-grammar/hear-or-listen): hearing as event, listening as attentive action, `can hear` on a call and `listen to` with an object.
- Cambridge Grammar Today, [Present continuous](https://dictionary.cambridge.org/dictionary/english/present-continuous): ongoing situations and short forms.
- New `tests/test_a1plus_week01_editorial.py` checks content and the API's accepted/rejected answers.

**Environment limits:** The connected GitHub API permits reading and updating
files, but local cloning/testing is unavailable in this execution environment
(no network DNS for `github.com`). Accordingly, the following are **BLOCKED**
until a runner executes them:

```bash
uv run python manage.py test tests.test_a1plus_week01_editorial
uv run python manage.py load_content
uv run python manage.py audit_course
uv run python manage.py test tests --parallel auto
```

GitHub Actions status must be read independently; this document does not
claim a successful CI run. Real learner testing, speech playback and
390-pixel browser checks remain unverified.

## 4. Quality gate snapshot

- **Change isolation / PR overlap:** PASS (checked filenames of PR #105).
- **Linguistic rule basis:** supported by cited grammar references.
- **Static presence of approved variants:** verified in proposed file text.
- **Runtime answer checking / content import / all Django tests:** BLOCKED.
- **Human comprehension and natural audio:** BLOCKED.

**Remaining scope:** 58 other lessons not touched, plus the rest of these
two lessons and their connected weeks, dialogue, translations and audio. Do
not mark them as editorially accepted on the basis of this pilot.
