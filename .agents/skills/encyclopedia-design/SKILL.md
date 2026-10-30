---
name: encyclopedia-design
description: Use for any UI, page, component or animation work in English Encyclopedia. Forces the project's editorial-atlas design direction and blocks generic "AI-looking" design. Requests to improve or redesign how the site looks go to design-pipeline first, which calls this skill as stage 0.
---

# Encyclopedia design workflow

## Before writing code
1. Read `DESIGN.md` in the repo root. It overrides your defaults.
2. Look at the existing page/component and the SCSS tokens. Reuse tokens; do not invent new colors or spacings.
3. Write a 5-line design brief in your reply:
   - Purpose of this screen for a Russian-speaking learner
   - The one signature moment on this screen
   - Type choices (display / body / English material)
   - Layout idea (which grid, what breaks the grid)
   - Motion idea (what it explains) + reduced-motion fallback
4. Name the generic version you are NOT doing (e.g. "not a centered hero with two buttons").

## While building
- Semantic HTML first, then SCSS with tokens, then JS/GSAP.
- Progressive enhancement: the page works without JS.
- Russian UI text for learners; English only for learning material.
- One focused change per task. No unrelated restyling.

## Before saying "done"
- Check at 375 / 768 / 1440 px. Take screenshots if a browser tool is available and look at them critically.
- Run the visual checklist from `DESIGN.md` section 9.
- Run related tests and `python manage.py check`.
- In the summary: what changed, the signature decision and why, what you verified, what you could not verify.

## Self-critique pass
After the first version, do one honest critique round:
"What here looks like every other AI-made site?" — fix the worst one or two things, then stop.
