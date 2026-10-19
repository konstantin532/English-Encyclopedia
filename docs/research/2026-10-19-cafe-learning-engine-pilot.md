# A1 Learning Engine — café information-gap vertical pilot

Date: 2026-10-19. Built on current `main`, not the obsolete experimental branch. No change to the 28 core lessons, audio files, A1 vocabulary, or existing independent/teacher assessment semantics.

## What is actually implemented

- Opt-in, authenticated, server-directed `/learning/cafe-mission/` behind a link from the existing `/lab/cafe/` laboratory. Existing voice playback, exercises and microphone-local recording are untouched.
- **Actual information gap (small controlled domain):** the learner is told to request one tea or coffee; available stock is selected on the server (two scenarios) and is *not* disclosed in the page before the interaction. A café worker reveals unavailability, waits for a request for alternatives, offers genuine alternatives, then intentionally asks if the order was for **two** portions. The learner has to correct the misunderstanding for the scenario to finish. The response path depends on the student's message and the server state, rather than a transcript of fixed prerecorded turns.
- **Editorial, interpretable skill map:** `cafe.order_one` → `cafe.ask_options` → `cafe.choose` → `cafe.repair`; each with the learner-facing `Я могу…` target. This is the minimum demonstrable graph, not a claim that skill mastery is psychometrically calibrated.
- **Bounded diagnostic feedback:** a clearly recognized `two` instead of `one` can trigger an authored contrast. Other unrecognized English is explicitly **not marked incorrect**. The limited English parser recognises some A1 phrasing, not all reasonable responses. This is not a full natural-language conversation model.
- **Fading/assistance provenance:** three optional hints are logged; if opened, an attempt cannot be saved as unaided solely by choosing “no help” at the end. Use a separate self-report of external assistance.
- **Persistence and human validation:** the final, opt-in attempt is stored in existing `IndependentAttempt` with the prompt snapshot, accepted learner turns, full dialogue trace, source/version, observed task acts and help count. It remains `self_reported` / `unreviewed` until a teacher reviews it. This does not update CEFR, `UnitProgress`, `MistakeReview` or `SpeechPracticeProgress`. The ordinary staff review form can inspect the original situation and rubric.
- **Delayed transfer:** existing `transfer_pilot` now includes one baseline, one new context at day 7, and one different context at day 30 for `a1-cafe-order`. Reuses existing idempotency, due-time logic, teacher review and uniqueness constraint, not a second scheduler. Models are concealed before answers. A logically mismatched reference example for week 2 was corrected.

## Safeguards and explicit limits

No automatic English grade or “mastery” based on a parser match. No sound-production diagnosis. No inventory secret is stored in the client-visible HTML; state is in the authenticated session. No transcript is saved until the learner explicitly selects “Save”, and no audio is uploaded. Prompt learners to enter only fictional information. A session is linked to the logged-in account and restarted for a different user.

A constrained multi-turn information-gap task is **not** equivalent to genuine human-to-human negotiation or arbitrary free English. Requests outside the supported A1 forms receive a neutral retry and must not be used as negative skill evidence. A narrow parser can miss correct English: teacher review remains essential.

The independent review pilot records *self-reported* assistance; it does not prove an unaided setting. For longitudinal data, the 7-day stage is closed on day 14; attempts performed later than day 7 and before that cutoff are explicitly time-stamped and flagged if more than one day late. A missed stage is not manufactured as a successful retention measurement. The day-30 stage may be overdue; its actual and planned times must be inspected and treated as measurement deviation. These observational pilot tasks are not randomized, calibrated instruments, or proof of learning gains.

## How to verify

```sh
uv sync --frozen
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test tests.test_cafe_mission tests.test_cafe_lab tests.test_a1_transfer_retention_pilot
uv run pytest -q
node --test tests/js/*.test.cjs
uv run python manage.py collectstatic --noinput
```

Browser check at 390px and desktop: start from `/lab/cafe/` → `/learning/cafe-mission/`, finish each server inventory branch with/without help, test keyboard only and screen-reader announcements, visit `/learning/transfer-pilot/a1-cafe-order/`. Validate CSRF, stale tokens, repeated saves and concurrent requests in staging.

## Research support, not project outcome

External research supports relevant *mechanisms*, not the effectiveness of this exact implementation:

- Council of Europe, **CEFR Companion volume** (2020): interactional communicative activities and learner-facing can-do descriptors; https://www.coe.int/en/web/common-european-framework-reference-languages/cefr-companion-volume-and-its-language-versions
- Kim et al., **The Effects of Spaced Practice on Second Language Learning**, Language Learning (2022); meta-analysis of 48 experiments (N=3,411); https://doi.org/10.1111/lang.12479
- Uchihara, Karas & Thomson, **High-Variability Phonetic Training**, Studies in Second Language Acquisition (2025); supports *perception*, not automatic speaking mastery; https://doi.org/10.1017/S0272263125100879

Experimental protocol and literature caveats: [2026-10-19-learning-engine-study.md](2026-10-19-learning-engine-study.md). A future controlled study must compare equivalent active learning time, unseen form sets, independent blind expert judgements, confidence intervals, nonresponse and 7/30-day measurements. The project currently has **no human A/B results** from this pilot.

## Next honest increments

1. Human review of a sample of café transcripts to estimate false positives/negatives in the narrowly supported forms.
2. True versioned skill observations and item-bank links (after expert-authored taxonomy); avoid five premature data tables.
3. A pre-registered randomized or matched comparison with separate controls at baseline, 7 and 30 days.
4. A distinct multi-talker phonetic **perception** pilot for one contrast only when licensed, reviewable audio is available.


## Phonetic perception pilot — editorial and technical contract, not activated

**Choose one contrast:** General American /ɪ/ vs /i/ (for example `ship` / `sheep`). This is a receptive discrimination pilot; do not label it a diagnosis of the learner's production or speaking skills. The existing café audio has particular named synthetic voices, but has **not** been shown to satisfy a multi-talker, held-out-stimulus HVPT protocol. No pseudo-voice or `test-tone` should be introduced as audio evidence.

**Editorial/audio gates before building UI:**

1. Prepare a modest bank of natural, A1-comprehensible real words contrasting /ɪ/ and /i/, balanced by consonantal frame and checked for acoustic and semantic confounds. Keep word-pair IDs and dialect/accent metadata.
2. Acquire permission to store and distribute recordings; recruit/review at least three distinguishable General American voices and check accurate intended phoneme, natural stress, usable signal quality and no accidentally spoken answer label.
3. Split words and talkers by role: training and unseen held-out test material; seal test answer keys server-side. Archive source/license, SHA-256 digest and teacher review per asset.
4. Make each listening trial playable without microphone, keyboard-only and with a textual alternative clearly marked **not a listening assessment**. Keep visual context neutral; avoid English orthographic answer cues before the first response.
5. Log `speaker_id`, `stimulus_id`, training/test role, first response, correct/incorrect closed category, replay count, hint use and time. Keep *perception* separate from optional free oral practice and staff pronunciation ratings.

**Pre-release acceptance tests:** refuse missing, zero-byte, test-tone, swapped or altered assets; refuse repeated test stimuli in train; do not expose held-out audio keys or answers in HTML/JSON; shuffle choices without switching key; verify same user/session boundaries, CSRF and idempotency; keyboard navigation, screen reader announcements, slow loading/offline failure, narrow viewport, and audio-disabled fallback. An evaluation on **previously unheard voices and words** is necessary to measure generalization. Collect baseline and delayed +7/+30 measures before any effectiveness claim.

Reference: Uchihara et al. (2025) identifies perceptual improvement and some generalization/retention with substantial moderator variation. Its group-average effect does **not** establish that this application accelerates pronunciation or oral communication.
