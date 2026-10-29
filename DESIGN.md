# DESIGN.md — English Encyclopedia

Read this before ANY visual or UI work. It is the single source of truth for how the site looks and moves.
Applies to Codex and Claude equally.

## 1. Direction in one sentence
A living editorial atlas of American English: the calm authority of a great printed encyclopedia,
with the warmth of an illustrated story world (Anna, Tom, Mia, small American towns) and
interaction that feels crafted, not templated.

Reference mood: a beautifully set book + a museum exhibition website + a quiet film title sequence.
NOT: a SaaS landing page, a kids' app, a crypto dashboard, a generic "AI website".

## 2. The anti-generic rules (hard bans)
AI agents drift toward the statistical average of the web. These are the average. Never ship them:
- Inter / Roboto / Arial / system-ui as the display or body face.
- Purple/blue gradients on white, glassmorphism cards, neon glows, gradient text headlines.
- Hero = big centered heading + subtitle + two buttons + floating blobs.
- Three identical feature cards in a row with an icon on top.
- Rounded-2xl everything, shadows on everything, emoji as icons.
- Animations that exist only to move (fade-up on every block, parallax for no reason).
- Stock "smiling students with laptops" imagery.
If your first idea is one of these, throw it away and make the second, more specific idea.

## 3. Typography — the main tool
- Display/headings: a serif with character (e.g. Fraunces, Newsreader, Source Serif 4, Literata). Use optical sizes; tight leading on large sizes.
- Body (Russian explanations): a highly legible serif or humanist sans with full Cyrillic (Literata, PT Serif, Source Serif 4, IBM Plex Sans).
- English learning material is set slightly differently from Russian explanation text (e.g. italic serif or a distinct weight) so the learner always sees which language is which.
- Use real typographic detail: small caps for labels, old-style numerals in prose, proper quotes «» for Russian and “ ” for English, non-breaking spaces before dashes, hanging punctuation where possible.
- Measure: 60–72 characters per line for reading text. Never full-width paragraphs.
- Every font must cover Cyrillic. Check before choosing.

## 4. Color
- Paper, ink, and one or two accents — like a printed atlas.
- Base: warm off-white paper (not #FFF), deep ink (not #000). Dark mode = night reading, warm and low-contrast-glare, not pure black.
- Accent: the existing green of the audio player; one secondary accent at most (e.g. faded map red or ochre).
- Part-of-speech markers stay subtle: 0.75px lines, ~80% color strength, never louder than the text.
- All colors live as SCSS tokens / CSS custom properties. No hardcoded hex in components.
- Contrast: WCAG AA minimum for all text.

## 5. Layout
- Editorial grid: asymmetric columns, generous margins, marginalia (side notes, glosses, word hints in the margin like a scholarly book).
- Let some elements break the grid on purpose (a large illustration, a pull quote) — one per screen, not everywhere.
- Rhythm comes from a spacing scale (4/8-based tokens), not from random paddings.
- Mobile first: the margin notes collapse into tap-to-open glosses; nothing scrolls horizontally.

## 6. Signature moments (what makes it memorable)
Pick a few and execute them perfectly instead of many done halfway:
- Week cover: a full-bleed illustrated "chapter opening" with chapter number, title and a one-line story hook, like a book chapter.
- Route ("Ваш маршрут"): drawn as a path on a small map, steps as places in town.
- Word hover/tap: a gloss card that unfolds like an encyclopedia entry (word, sound, form links like went → go).
- Story pages: a reading mode with drop cap, character color hints for dialogue, and the audio player synced to the line being read.
- Progress: stamps or pins on the atlas map instead of generic progress bars.

## 7. Motion
- Purpose first: motion explains (where something came from, what changed), never decorates.
- Feel: paper and ink — unfold, slide like a page, ink fills in. Easing soft (ease-out / custom cubic-bezier), durations 180–450ms.
- GSAP for orchestrated sequences (chapter openings, route drawing); CSS for small state changes.
- Always respect `prefers-reduced-motion`: replace movement with instant or opacity-only changes.
- No scroll-jacking. Ever.

## 8. Imagery
- Consistent illustrated world: same palette, same line style, same light across all weeks.
- Characters Anna, Tom, Mia look the same everywhere.
- No copied art, no recognizable characters from other works.

## 9. Quality bar (check before saying "done")
- Open the page at 375px, 768px, 1440px and look at it. Screenshot if tools allow.
- Ask: would this look out of place in a gallery of award-winning editorial sites? If it looks like "a website", keep going.
- Check: fonts loaded with Cyrillic, contrast AA, keyboard focus visible, reduced-motion works, no layout shift on load, Lighthouse performance not worse than before.
- Name one specific design decision you made and why. If you can't, the design is generic.
