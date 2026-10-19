# Living Language Cinema — motion direction and quality record

**Date:** 2026-10-19. **Base:** latest main. **Branch:** feature/living-language-cinema-20261019.

## Audit

English Encyclopedia currently has **14 weeks and 28 lessons in A1**, not 28 weeks.
Shared chrome: templates/base.html and templates/components/{sidebar,header,footer}.html.
Week/lesson/dialogue/drill content comes from templates/{curriculum,lessons,components}.
Pre-existing local GSAP: static/vendor/gsap/gsap.min.js.
Pre-existing motion: studio-arrive keyframe on week heroes; wave-breathe on
playing audio; hover transforms on buttons/cards/sidebar; local GSAP for drill
feedback; reduced-motion rules distributed through accessibility.css,
studio.css, and cinematic-studio.css. None is replaced with a competing library.

Existing authoritative state signals: server response controls drill success;
aria-pressed controls real selection and playback; data-line plus actual audio
timings controls spoken-line highlighting; aria-current denotes route or mission;
hidden and details[open] indicate disclosure. The motion layer NEVER awards
grades, saves progress, creates fake speech assessment, or changes the audio.

**Branch choice:** AGENTS.md names situation-weeks, which was 181 commits
behind main when checked. This isolated UI task starts a new feature branch from
current main rather than reverting recent project fixes. Main is untouched.

## Motion direction research

| Candidate | Distinctive character | Typography and transitions | Reading, mobile and cost |
| --- | --- | --- | --- |
| A. Editorial Orchestra | Premium annotated journal, ink rails, paced scene titles | Layered editorial threshold and light chapter accents | Quiet reading; low-medium implementation cost; **selected** |
| B. Semantic Constellation | Morphology relations and moving semantic connectors | Anchored word connectors and dynamic diagrams | Education-oriented only with genuine linguistic mappings; potentially high layout cost |
| C. Living Theatre | Theatre spotlights and strong scene perspective | Dramatic actor portraits, sweeping chapter transitions | Expensive on Android and intrusive during long text; rejected as global language |

A is the main direction, retaining the genuine, grounded semantic emphasis of B
only for existing markup and audio timelines.

### Seven verbs of motion

| Verb | Meaning | Motion / durations | Repetition and Minimal |
| --- | --- | --- | --- |
| Reveal | New information | Opacity and 0–7px; 180–480ms, enter easing | Once per visible card; static in Minimal |
| Connect | Existing semantic relation | Decorative underline/rail, 180–280ms | Only genuine current route, never fabricate grammar |
| Respond | Direct user action | 0.985-to-1 control press, ≤180ms | Tap/click, no interception; static selected state in Minimal |
| Progress | Navigation across real lesson steps | Current marker and underline, 180–280ms | No fake progress meter, no forced scroll |
| Focus | Selected word or playing line | Rail, small portrait scale 1.035, 180–280ms | No auto-focus, no moving text |
| Transition | Reading between chapters | Opacity and ≤8px, ≤480ms | Signature only in Full, never loop |
| Resolve | Real answer feedback | Opacity and ≤5px, ≤200ms | Text status always visible in Minimal |

Ease tokens: enter cubic-bezier(.22,1,.36,1);
exit cubic-bezier(.4,0,1,1); emphasis cubic-bezier(.2,.8,.2,1).
Never use red flashes or punitive shake. No animation of page width/height.

## Signature patterns

1. **Editorial Threshold** — intro title, lead, hero composition in paced order.
2. **Chapter Rail** — gold ink marker on current sidebar page, no repositioning.
3. **Knowledge Thread** — current reading subsection linked to the existing toc.
4. **Sentence Grammar** — gentle neutral highlight of authentic class-marked words.
5. **Dialogue Baton** — emphasis follows real timed audio line and existing speaker.
6. **Resolution Ink** — feedback appears after actual server or exercise state.
7. **Journey Tile** — existing week/lesson/word cards receive brief thread accent.

## Engineering ownership

- static/js/motion-system.js — three-mode policy, boot, GSAP reuse, scene/card
  entrances, route IntersectionObserver, per-feedback MutationObserver, controls.
- static/css/motion-system.css — tokens, patterns, touch behavior and global
  manual+OS reduced-motion failsafes.
- templates/base.html — CSS and JS wired to shared chrome; mode preloaded early
  so a saved preference is used before display.
- templates/components/header.html and footer.html — two synced selects,
  desktop header and mobile footer to avoid narrow-header overflow.
- static/js/learning-player.js — calls the shared resolution API; shows an
  authentic pending state and blocks duplicate concurrent submit/reveal requests.
- tests/js/motion-system.test.cjs and tests/test_motion_system.py — preferences,
  OS restriction, fallback, source structure and grading contract.

The source HTML does not hide content for animation. If GSAP, IntersectionObserver
or the new runtime is unavailable, page information remains readable.

## User event registry and acceptance surfaces

Every event below maps to real selectors or state signals in the audited
templates and scripts. **This list combines existing effects and added effects;
it is not a claim of 51 independently bespoke animations.** Minimal uses
readable native/static feedback without decorative motion.

| ID | Actual event | Visual purpose / mechanism | Check |
| ---: | --- | --- | --- |
| 01 | Home heading mounts | Editorial type threshold | Screenshot |
| 02 | Home lead mounts | Subordinate type rhythm | Screenshot |
| 03 | Hero kicker mounts | Chapter entry sequence | Screenshot |
| 04 | Hero title mounts | Editorial focal point | Screenshot |
| 05 | Hero description mounts | Text before next action | Screenshot |
| 06 | Hero primary action mounts | Action arrives after explanation | Screenshot |
| 07 | Hero art mounts | Scene completes after text | Screenshot |
| 08 | Phrase role labels mount | Staggered linguistic structure | Screenshot |
| 09 | Hero action clicked | Micro press | Touch/keyboard |
| 10 | Current sidebar page | Chapter Rail | Screenshot |
| 11 | Sidebar link clicked | Micro press, navigation not delayed | Touch/keyboard |
| 12 | Search focused | Responsive surface/border | Keyboard |
| 13 | Login form focused | Quiet edge and native focus ring | Keyboard |
| 14 | Primary button hovered | Existing concise transform | Mouse/touch |
| 15 | Week tile enters viewport | Journey Tile entrance | Scroll |
| 16 | Week tile hovered | Ink underline | Mouse |
| 17 | Week tile focused | Same ink underline with visible focus | Keyboard |
| 18 | Lesson tile enters viewport | Card reveal | Scroll |
| 19 | Lesson tile hovered | Ink thread and existing hover | Mouse |
| 20 | Lesson link focused | Focus-within thread | Keyboard |
| 21 | Dictionary tile enters viewport | Card reveal | Scroll |
| 22 | Dictionary tile hovered | Ink thread | Mouse |
| 23 | Story map item enters viewport | Gentle map reveal | Scroll |
| 24 | Home note enters viewport | Staggered note reveal | Scroll |
| 25 | A1 scenario panel enters viewport | Context scene reveal | Scroll |
| 26 | Speech studio enters viewport | Context scene reveal | Scroll |
| 27 | Week chapter heading mounts | Editorial type entry | Screenshot |
| 28 | Lesson or entry heading mounts | Editorial type entry | Screenshot |
| 29 | Lesson section enters reading area | Current toc link | Scroll |
| 30 | Week chapter enters reading area | Current route number | Scroll |
| 31 | Word marker hovered | Class-preserving neutral glow | Mouse |
| 32 | Word link focused | Same neutral glow and native focus ring | Keyboard |
| 33 | Drill option selected | Existing pressed visual response | Click |
| 34 | Builder word appended | Brief word placement | Click |
| 35 | Drill hint disclosed | Revealed hint content | Click |
| 36 | Answer sent to server | Real pending state, duplicate disabled | Slow network |
| 37 | Server confirms correct answer | Resolution Ink and true explanation | Result |
| 38 | Server identifies correction | Neutral, explanatory response | Result |
| 39 | Open response needs review | No premature incorrect claim | Result |
| 40 | Answer reveal returns | Actual server answer displayed | Network |
| 41 | Existing details block opened | Content entrance (Full/Balanced) | Keyboard |
| 42 | Play/pause audio | Real aria-pressed / control surface | Audio |
| 43 | Current dialogue line changes | Dialogue Baton from real timestamps | Audio |
| 44 | Speaker avatar becomes active | Subtle avatar emphasis | Audio |
| 45 | Playing audio wave indicator | Existing wave-breathe in Full only | Audio |
| 46 | Listening/speech mode selected | Quiet existing radio state | Keyboard |
| 47 | A1 mission tab selected | Current-step transition | Keyboard |
| 48 | Phonetic stress word selected | Existing pressed state | Keyboard |
| 49 | Stress or speech feedback updates | Existing text + resolution effect | Exercise |
| 50 | Intensity mode changes | Live synced preference | Node tests |
| 51 | OS reduce-motion preference changes | Enforced Minimal without auto-Full | Node tests |

## Benchmarks and non-negotiable regression gates

Targets, **not measured results**: 60 FPS on suitable devices, CLS ≤0.1,
INP ≤200ms with representative data, no significant baseline regression.
For animation use compositor-friendly transform/opacity, never alter width/height
of reading content, and avoid blanket will-change. The decorative SVG audio
wave does not claim to reflect amplitude measurements.

Research:
- WCAG 2.2 SC 2.3.3: https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions
- W3C CSS reduced motion: https://www.w3.org/WAI/WCAG22/Techniques/css/C39.html
- W3C JS reduced motion: https://www.w3.org/WAI/WCAG21/Techniques/client-side-script/SCR40
- Rendering pipeline: https://web.dev/articles/animations-overview

### Still required in actual browsers before production merge

- [ ] Before/after screenshots: home, weeks 1 and 14, lessons 1 and 28,
      story, poem, dictionary, dashboard, A1 practice and login.
- [ ] Compare at 360, 390, 430, 768, 1440, 1920 CSS px.
- [ ] Chrome Android, TalkBack, desktop Chrome/Firefox, Safari when possible.
- [ ] Network failure / repeated taps / audio pause, seeking and role-play.
- [ ] Mobile orientation, keyboard focus, no-JS, back/forward cache.
- [ ] Lighthouse traces and true CLS/INP/per-frame measurements.
- [ ] Node + Django test suite and audit per CLAUDE.md.

Automated source contracts are NOT evidence of browser rendering, FPS or WCAG
conformance. The unchecked rows are openly unverified until tested.

## Typography/Sass follow-up (2026-10-19)

Author motion CSS in static/scss/legacy/_motion-system.scss and new polish in static/scss/system/_motion.scss; static/css outputs are generated. See docs/ui/2026-10-19-design-system.md for layers, WOFF2 and actual browser evidence. Full intro is now session-scoped; unavailable sessionStorage skips decoration. Earlier unchecked device/trace gates remain unverified unless the follow-up explicitly records them.
