# Lesson core simplification — implementation and verification

Date: 2026-10-27
Base: ac7f3f8427707a3a9c071801c7e8f238cfed1997
Branch: codex/simplify-lesson-core-20261027

## Approved scope

The user requests a clear end to the lesson, followed by one optional disclosure.
User clarification: preserve every existing exercise and translation; do not cap
lessons at four. The first nouns lesson already has four of each.
Keep seven layers, the upper minute card, all IDs, answers, progress services,
URLs, models and migrations. No merge into main.

## Approach

Use the existing shared Django lesson template and native details/summary.
Move independent checking, the speech studio, active situations and cafe extras
after a completion section. Hide the duplicate three-step block with a Django
comment; keep its old anchor on the upper card. Give the reusable speech controls
a lesson_mode flag so only lesson pages omit rhythm and spaced oral reviews.
Guard optional rhythm controls in JavaScript; retain the existing algorithm.
Keep the current exercise rendering loops, IDs and persistence code unchanged.
The completion section marks the end of the main material; it does not write or
replace server-side mastery/progress.

## Work and checks

- [x] Add database-free SimpleTestCase rendering tests; observe the expected failures.
- [x] Add a Node regression for speech initialization without rhythm controls.
- [x] Update lesson layout, optional speech controls and navigation.
- [x] Add scoped completion/disclosure styling and compile the touched stylesheet.
- [x] Run only affected template and JavaScript tests.
- [x] Use a separate preview server with an isolated database copy; verify the nouns
      lesson on desktop and at 375px, optional disclosure, speech controls, preserved
      anchors and next-lesson URL. Capture after screenshots matching before views.
- [x] Independent review; report changed files, checks and branch without merging.

## Review focus

Authenticated/anonymous rendering; no extras; no next lesson; lessons with more
than four exercises; other speech surfaces retain rhythm/reviews; direct links
into closed optional content; no horizontal overflow at 375px.

## Evidence

Implementation and verification completed. The original desktop/mobile screenshots were captured
from the unchanged local site before any product edits.

Verification: 8 database-free template tests PASS (0.043s), 6 speech-studio Node tests PASS; touched stylesheet matches Sass 1.105.2 output; git diff --check PASS. Browser: 1440x1000 and375x812, closed details,7 layers,4 exercises,4 translations, no horizontal overflow; keyboard disclosure, speech next fragment, legacy #spoken-coach reveal, and next lesson with5 exercises PASS; no console errors. Final heading is a lesson-end landmark and does not modify server progress. Screenshots captured before/after in conversation artifacts. No models, migrations, content records or progress endpoints changed.

Independent review: no blocking issues in supplied exact product patch. Scope: patch-only review; surrounding unchanged code was not inspected by the reviewer. Automated and browser results above were run by the primary agent.
