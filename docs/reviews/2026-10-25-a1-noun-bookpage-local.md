# Local A1 noun book-page pilot — review record

## Baseline and scope

Base main: `2a35c0409d9b76521c3ecd1bcfaf3c032deb6f9a`, checked with remote HEAD/main. Local branch `feat/a1-noun-bookpage`. Only open PR observed was unrelated #124; it was not changed. Initial work was local-only. The user subsequently explicitly authorized publishing this reviewed pilot as a separate branch and draft PR; merge, auto-merge and deployment remain unauthorized.

User authorized local edits after discussion. Book-page is our chosen default, not approval to change reading-mode meaning. Scope is the `a1-nouns-first-words` lesson only.

## Changes

- Conditional template wrapper and stylesheet: calmer reading surfaces, larger space between sections, subordinate instructions, more distinct examples. Outer grid, catalog/sidebar, main title, existing font-family assignments and lesson content unchanged.
- Existing modes still show layers 1/3/5/7, 1/2/3/4/5/7 and all seven respectively. Pilot-only live feedback names visible counts and hidden steps, and says that the quick summary and practice do not change.
- Active depth and speech states use paired text/background colors plus underline/weight, without removing keyboard focus styling.

## Speech contrast evidence and limitation

`legacy/_app.scss` in `ee-base` assigns the active speech button a pale foreground and dark background. `legacy/_studio.scss` in later `ee-studio` assigns `.btn-quiet` a pale surface background without replacing that selected foreground. Pilot `ee-polish` owns both properties together. This source-level conflict motivates the candidate fix; no measured computed colors or browser-confirmed fix is claimed. Other pages retain their current styles; a course-wide fix is outside this pilot.

## Verification

- Baseline Node tests: 124/124 PASS.
- Test-first scoped Django rendering: expected missing-wrapper failure, then 4/4 PASS. Includes every original annotated layer and unchanged controls.
- Test-first feedback/cascade contract: three expected failures, then PASS.
- Independent read-only review: one font-family preservation issue; regression RED→GREEN after removing the family overrides. No other substantial diff issue reported.
- Final Node suite: 130/130 PASS. CSS source/generated consistency: 18 stylesheets PASS. `git diff --check`: PASS.
- Full Django suite: `.venv/bin/python manage.py test tests --parallel auto --noinput` → 923 tests, OK (skipped=2), 244.198 seconds. SQLite run; this does not verify PostgreSQL. Output contains the baseline missing `staticfiles/` warning and expected test diagnostics; no failed tests.
- `manage.py check`: PASS. No changes under `content/`, `apps/`, base template or foundation stylesheet.

## Browser QA: BLOCKED

Headless Chromium in the default sandbox fails on `socket() Operation not permitted`; reviewed escalation fails during bwrap setup on the denied sessions mount. No access or workaround for that path was attempted. Normal cloud CUA localhost navigation also cannot reach the app. A same-shell server/curl check returns HTTP200, but separate shell/CUA sessions report connection refused.

Therefore before/after desktop and 390px screenshots, real keyboard traversal, 200% zoom, reduced-motion visual behavior and computed contrast are not verified. Unit tests are not substitutes for these checks. Do not call the pilot visually polished or publication-ready until reviewed in a browser.
