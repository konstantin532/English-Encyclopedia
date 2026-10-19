# English Encyclopedia — The Living Language Atlas
## Art direction / A1 illustrated chapters (first implementation)
The governing educational premise is **«Не зубри английский. Пойми его».**

### Visual language
- **Editorial paper:** warm cream, subtle sage and deep green, muted brass.
- **Illustrated continuity:** a local authored SVG series for A1 weeks 1–14, drawn in one coherent flat-cinematic editorial language with layered light, urban or domestic settings, and restrained botanical motifs.
- **Returning cast:** Anna has auburn hair and a deep green coat; Tom has short dark hair and a blue-grey coat; Mia has honey-blonde hair, a muted caramel top and a pale café apron; Box is a sandy-coloured cat. These are original *stylized vector interpretations*, not verified photorealistic character portraits. Their details should be refined against any owner-provided established character images before treating them as canonical likenesses.
- **One layout, varied atmosphere:** the catalogue uses the same covers cropped into existing cards; week pages use full illustrations. Assets contain no essential text; title, objectives and interactions stay accessible HTML.
- **Important exception:** the previously existing `static/img/studio/cafe-morning.webp` remains the week 3 hero image. The new week 3 SVG is only used for the catalogue thumbnail until art direction is reviewed.

### Scene sequence (grounded in content/manifests/weeks_plan.yaml)
| A1 week | Scene / visual motif |
|---|---|
| 01 | Neighbour introduction / front door / Anna and Tom |
| 02 | New home / interior window / Box the cat |
| 03 | Ordering at a café / café counter / Mia |
| 04 | Family in a photograph / framed portrait |
| 05 | Neighbourhood shop / awning and window |
| 06 | Daily routine / wall clock / home |
| 07 | Jobs and occupations / desk and computer / Tom |
| 08 | Asking for directions / city junction / signpost |
| 09 | Phone and messages / mobile screen and speech bubbles |
| 10 | Weekend and hobbies / green park |
| 11 | Doctor's appointment / quiet clinic |
| 12 | Post office / letter and counter |
| 13 | Language courses / classroom chalkboard |
| 14 | Bus trip / transit bus and city background |

The illustrations are intentionally descriptive rather than a direct depiction of every episode. Specific actions, mystery details and character canon should be validated against scripts before any additional narrative illustrations are commissioned.

### Speaker portraits
Local vector likenesses `atlas-portrait-anna.svg`, `atlas-portrait-tom.svg`, and `atlas-portrait-barista.svg` reuse the existing 30×34 CSS speaker badge. The role identifier for Mia in the café is `barista`, so the illustration maps to `.speaker-barista::before`; the screen-reader-visible speaker names remain text. The original initials appear in Windows forced-colors mode. These are provisional stylized interpretations and should be aligned with any prior established character images before acceptance.

### Interactive visual linguistics
On the homepage, the existing `I'm home.` example now progressively enhances to three focusable buttons:
- **I:** subject, the person being talked about.
- **'m:** contraction of `am`, a form of `be` linking the subject to its location.
- **home:** place expressed without `at` in this construction.

The semantic marker spans and their colours are **not changed**. The example renders and explains itself with JavaScript disabled; JavaScript upgrades static role labels only at startup. Keyboard control is native; explanations use `aria-live=polite`. Decorative opacity animation is permitted only with full motion and never required to read the answer.

### Engineering
- Source styles are added to the *existing* `static/scss/editorial-world.scss`, not another competing override file. CSS `static/css/editorial-world.css` must always be regenerated with `pnpm build:css` and verified with `pnpm check:css`.
- All asset URLs are supplied by Django's `static()` so `collectstatic` and hashed storage can resolve them.
- Catalogue art is absolutely positioned and does not change intrinsic card layout; responsive gradients preserve contrast.
- Non-A1 levels retain their previous cover fallback.
- `static/js/atlas-language.js` is pedagogical interaction rather than another general-purpose motion system. Existing GSAP motion controls still own intro animations.
- Tests cover all fourteen assets, address mapping, HTML links, explanatory roles and accessible controls.

### Review required before merge
- Real browser screenshots of home, A1 catalogue and a week at 1440×900, 1280×800, 390×844 and 360×800.
- Keyboard focus and announcement checks; talkback/Android checks where available.
- Confirm all images load with `collectstatic` and that no content overflows or is covered by overlaid art.
- If the illustrated characters differ from owner's previous artwork, prefer the established character reference rather than merging divergent portraits.

### Scope / truth in delivery
This PR implements the three-screen artistic prototype **and all fourteen local vector covers**. It does **not** claim final painted cinematic character illustrations, perfect portrait identity, a complete art bible for every recurring environment, browser screenshots, or exhaustive redesign of all course screens. Those are separate review and expansion tasks after the new direction is assessed on actual screenshots.

### Subsequent verified checkpoint
See [narrative and art bible](atlas-art-bible.md) and [real browser QA evidence](../qa/living-atlas-browser-review.md) for the follow-up that corrects four cafe settings, adds the cartographic frontispiece and verifies unchanged geometry.
