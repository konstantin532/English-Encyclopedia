# Typography and motion implementation plan

Goal: improve reading and expressive interaction without moving existing UI regions.
Architecture: existing Django templates and EnglishMotion runtime remain authoritative. Introduce modular Dart Sass with layered compatibility outputs at existing CSS URLs, a shared polish entrypoint, local WOFF2 font derivatives and reproducible build checks.
Spec: user attachment 197ed52d-50d3-4317-9283-52379d865f9b. Base68fd883b1cf416317984eb0daa71e0ef0f66502b, isolated clone feat/typography-motion-system.

Constraints: no content/IPA/CEFR changes, no main/production changes, no new tracking, semantic marker colours preserved, existing three motion modes retained.

Review focus: stylesheet ordering vs semantic markers; IPA diacritics and font fallback; keyboard/mobile widths; hidden content and reduced motion; cold-page fonts and repeat intro.

- [x] Capture home/week/lesson/words/story/poem/login baseline and audit.
- [x] Sass build: exact locked Dart Sass, deterministic build/check, layers, semantic maps/functions/mixins; compatibility CSS paths remain. Verify clean compile and drift failure.
- [x] Typography: readable Russian UI/body, editorial headings/English, dedicated IPA; local WOFF2 and existing OFL. Verify real strings and fallback in browser.
- [x] Refine visual states and coordinated motion, reuse EnglishMotion; test repeat entry, storage blocked and reduced motion behavior. No grading changes.
- [x] Improve public metadata safely; private routes noindex, canonical only with configured origin; test response.
- [x] Browser 320/390/768/1440, keyboard, motion modes, audio/exercises; report unsupported zoom/device checks honestly.
- [x] Full Django + Node + build drift + audit; independent final review; commit/push branch, PR, CI evidence.

Implementation proceeds under the user's full supplied implementation brief; routine implementation choices are made in-session.

Evidence: full598 Django OK338.811s; Node105 OK;28 viewport checks clean; real week1 MP3 and drill verified. Review fixed blocked Storage getter via RED/GREEN and pinned generated CSS LF via attributes. Native200%zoom, physical Android/TalkBack, field performance and human growth research remain unverified. Commit/PR/CI recorded in final report.
