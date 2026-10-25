# A1 Noun Bookpage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local, single-lesson reading-hierarchy pilot preserving every explanation and existing depth semantics.
**Architecture:** Conditional template scope and a separate SCSS entry in the established CSS layers; existing depth controller gains pilot-only factual feedback. No lesson content or progress logic changes.
**Tech Stack:** Django templates, vanilla JavaScript, Sass, Node test runner.
**Spec:** `docs/superpowers/specs/2026-10-25-a1-noun-bookpage.md`

## Global Constraints
- Pilot slug: `a1-nouns-first-words`; no catalog/sidebar/header/outer geometry changes.
- Preserve full explanatory content, marker palette, fonts and existing mode labels/membership.
- Local edits only; no publication. User explicitly requested proceeding, so no further design-question gate.

## Review Focus
- Other lessons must not receive the pilot stylesheet or feedback.
- Repeated mode switches and hidden-layer hash links must remain reversible.
- No-JS or incomplete markup must preserve every explanation.
- Reader font sizing, narrow screens, keyboard focus and reduced motion must remain usable.
- Summary/practice must not be described as hidden by depth switching.

### Task 1: Pilot presentation scope
**Files:** `templates/lessons/detail.html`, new `static/scss/lesson-bookpage.scss`, generated `static/css/lesson-bookpage.css`, `tests/test_a1_learning_route.py`.
**Interfaces:** conditional `[data-lesson-bookpage]` wrapper; no changed content interface.
- [x] Add failing Django tests for pilot-only wrapper/style and intact annotated lesson bodies.
- [x] Run targeted tests; confirm expected missing-scope failure.
- [x] Add conditional wrapper/style and scoped typography/surfaces, preserving outer layout.
- [x] Build CSS; run targeted Django and CSS checks.

### Task 2: Pilot depth feedback
**Files:** `static/js/a1-learning-route.js`, `tests/js/a1-learning-route.test.cjs`.
**Interfaces:** detect `[data-lesson-bookpage]`; existing modes/layers unchanged.
- [x] Add failing tests for pilot counts (4/7, 6/7, 7/7), exact hidden steps, unchanged non-pilot feedback, repeated switching and hash restore.
- [x] Run test to confirm missing factual feedback failure.
- [x] Implement pilot-only feedback; preserve fallback and all mode semantics.
- [x] Run all JS, full Django, CSS checks and diff checks.
- [x] Attempt desktop/mobile browser screenshots and keyboard/reduced-motion/contrast checks; record actual block rather than inferred success.
- [x] Obtain independent diff review; fix verified important findings with regression tests.

## Evidence / ledger
- Baseline: main `2a35c0409d9b76521c3ecd1bcfaf3c032deb6f9a`, verified with git ls-remote; only open PR124 is unrelated.
- Baseline JS: 124/124 PASS. Independent local clone `lesson-design-pilot`, branch `feat/a1-noun-bookpage`; other worker files untouched.
- Browser launch BLOCKED: sandbox socket() Operation not permitted; reviewed escalation fails bwrap on denied sessions mount. No bypass attempted.
- Ruling: local-only work remains uncommitted until parent review/publication direction; no automatic commit/push from generic skill steps.

- Task 1: scoped rendering tests RED (missing pilot wrapper) → GREEN (4 Django tests); every original annotated layer is present.
- Task 2: depth counts/deeplink feedback and speech pair tests RED (3 expected failures) → GREEN; shared mode membership unchanged.
- Independent reviewer found a font-family assignment change conflicting with preservation requirement. Regression test RED → removed all pilot font-family overrides → GREEN. Final JS: 130/130, CSS check: 18/18, diff check: clean.
- Ruling: include pilot-scoped speech foreground/background pair as source-evidenced candidate, as authorized by parent. Actual computed contrast and symptom resolution are not verified.
- Browser reachability: same-shell runserver/curl returns HTTP200; separate-shell/CUA localhost routes report connection refused. No supported cross-session browser route established. Desktop/mobile screenshots, keyboard, 200% zoom and reduced-motion visual checks BLOCKED, not PASS.

- Final full Django: 923 tests, OK (skipped=2), 244.198 seconds; SQLite only. `manage.py check` PASS. No content/backend/base layout files changed.

- Publication authorization received after local verification: separate branch and draft PR permitted. No rollout, merge or auto-merge. Main remains 2a35c04; no product-code changes since final tests.
