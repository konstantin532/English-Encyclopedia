# Editorial pilot — Stage 0

> **For agentic workers:** Use superpowers:executing-plans; this plan implements the user-approved astra-redesign-prompt.md Stage 0 only.

**Goal:** Make week A1/3 and a1-cafe-order reviewable as an illustrated editorial edition.
**Architecture:** Server-side scope flag; reusable chapter, dialogue, sidenote and glossary templates; a scoped system SCSS module emitted by existing editorial-world.scss in ee-polish. Pilot opts out of the older educational-reading surface; other pages remain identical. Native details work without JS; a small progressive enhancement opens notes on wide screens and collapses them on mobile.
**Tech Stack:** Existing Django 5.2, Sass, vanilla JS, existing fonts and illustrations.
**Spec:** User attachment astra-redesign-prompt.md, approved for execution in chat.

## Global constraints
Only Stage 0; no sitewide rollout or merge. Do not edit learning YAML, markers or motion policy. Preserve all exercises, navigation, original text and translations. Reuse existing painted week 3 artwork: the photo claim is stale on d88ff74. No additional CSS entry point or layer. Theme consolidation and Markdown rendering belong to later stages.

## Review focus
Scope leakage into other weeks/lessons; lost learning content or markup; duplicate/displaced dialogue translation; notes hidden without JavaScript; horizontal overflow at 360px and reader enlargement.

## Baseline
main d88ff746480bb3692246db7df11469879a1180eb. Separate checkout and local database. Open PR140 is unrelated. pnpm check:css PASS; 172 UI tests PASS. 20 viewport screenshots plus dialogue/reading details recorded before changes. System dark preference currently leaves data-theme=light. All 14 catalogue covers load after lazy images are requested.

## Tasks
- [x] 1. Add rendered-response regression tests for page scope, image-before-title, structured glossary, unchanged educational data and escaped sidenotes; verify RED.
- [x] 2. Implement scoped context in apps/{curriculum,lessons}/views.py and reusable components in templates/components/editorial_*.html; preserve existing nonpilot branches. Verify targeted Django tests.
- [x] 3. Add system/_editorial.scss through editorial-world.scss, and responsive native sidenotes; compile/check CSS and run UI tests.
- [x] 4. Browser verification at 1440/1280/390/360, both system themes, keyboard, reduced motion and forced colors; compare baseline and pilot screenshots, structural metrics, and local LCP samples.
- [x] 5. Run fast and full Django suites; independent review, one branch/PR and report. Stop for owner review before Stage 1.

Pre-flight: context flag is editorial_pilot on both views, matching template and style scope data-editorial-pilot. Sidenote JS only loads on the two pilot routes.

Completion checkpoint: Stage 0 implementation and browser acceptance complete. Chromium CI passed 16 combinations plus keyboard/no-JS/forced-colors/reader-size checks; paired LCP medians are recorded in docs/qa/editorial-pilot.md and ci-summary.json. Local full suite passed 1161 tests (8 skipped). Fast-suite concurrency flake and unavailable production/audio checks remain explicitly documented. Two compiled CSS comment differences corrected after CI. Final overall CI is visible in PR141. Stop for owner review; no merge or Stage 1 authorization assumed.
