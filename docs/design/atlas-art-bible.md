# Living Language Atlas — narrative and visual reference

## Status
Implementation checkpoint, not final visual acceptance. Based on main `7d27a5a` (PR #47); PRs #45 and #46 are merged and there were no open PRs when inspected. The inherited 14-cover series remains the starting point. This revision adds a vector frontispiece, corrects four cafe settings, adds chapter image descriptions, and makes phrase discovery independent of card height.

## Artistic vocabulary
The frontispiece is an imagined index of the course, not a geographic map: home, cafe, bus, open book, connecting paths, botanical forms, contour lines and a compass. Its architecture is drawn directly in SVG, with no external images or embedded learning text. It uses paper, sage, botanical ink and muted brass. The interactive phrase remains the central reading object. The existing grids and type sizes are not edited.

Quiet surfaces remain for lessons and practice. Editorial surfaces identify cards and navigation. Signature surfaces belong to home and chapter covers. Existing `editorial-world.scss` owns this revision; no new cascade layer or competing stylesheet is introduced. The inherited overlap between art-direction and editorial-world has not been fully consolidated in this checkpoint.

## Character reference
These are visual continuity rules for the existing vector interpretation, not new biographies. `content/manifests/characters.yaml` and weekly scripts own narrative facts.

| Character | Confirmed narrative | Existing vector identity | Continuity rule |
|---|---|---|---|
| Anna | Moved from Russia; teacher; Box is her cat | Auburn hair, green outerwear, rounded face | Reuse existing face and silhouette; no new age or appearance claims |
| Tom | Neighbor; works at home on a computer | Short dark hair, blue-grey outerwear | Reuse existing face and proportions |
| Mia / barista | Works at the corner cafe; rises at five | Existing cafe portrait, apron | Both role IDs describe the same character; do not invent a second face |
| Box | Anna's cat | Sandy coat in the existing SVG series | Preserve silhouette and coat; avoid revealing future mystery outcomes |
| Other speakers | Clerk, passerby, locksmith, doctor, postal worker, bus driver | No accepted portrait system | Keep existing text labels; do not invent portraits as completed work |

The photo-like cafe asset and vector portraits use different treatments. Its brunette barista differs from the vector treatment; this remains a real consistency limitation. The photo is preserved as requested, without claiming that the character identity has been reconciled.

## Environment and lighting rules
Use one repeated cafe architecture for recurring cafe scenes. Distinguish episodes with verified light and a small still-life, not new faces. Homes use framed windows and restrained wood tones; public interiors use clear counters and legible objects; streets use low-rise silhouettes and route lines. Maintain line weights and the same paper grain. Light temperature is art direction; time of day is factual only when the script confirms it.

The existing 1536×1024 cafe WebP was inspected directly: warm left-side sunlight, faces on the right, natural room depth and ample light space for copy on the left. It remains week 3's hero. It is not used as the new homepage background. The new SVG map keeps all learning text in HTML.

## Chapter audit
Primary sources: every `content/seed_weeks/a1_wNN.yaml`, especially `story_beat` and `script`. Listed objects describe the narrative; a cover may still be a thematic vignette rather than a literal frame. No inferred time is passed off as confirmed.

| Week | Confirmed speakers | Actual opening | Outcome / visual story object |
|---|---|---|---|
| 01 | tom, anna | Первое утро Анны в новом доме. На крыльце её встречает сосед. | Анна и Том познакомились: Том — сосед, Анна — из России. Анна очень занята переездом, и Том желает ей хорошего дня. |
| 02 | anna, tom, mia | Анна показывает Тому и Мие свой новый дом. | Гостям нравится дом. Только большая коробка — ничья: она не Анны и не Тома. |
| 03 | barista, tom, anna | Утро в небольшом кафе. Анна и Том заказывают завтрак. Кофемашина шумит, и бариста не всё слышит с первого раза. | Заказ принят: кофе, чай и большое печенье. На столе лежит маленькая семейная фотография — она не Анны и не Тома. Анна берёт фото с собой. |
| 04 | anna, mia, tom | На следующий день Анна и Том приходят к Мие с фотографией из кафе. Вдруг она знает эту семью? | Это семья Мии: маме сорок, папе пятьдесят, брату десять. Анна возвращает фото, и Мия очень рада. |
| 05 | clerk, anna, tom | Утро. Анна и Том идут в маленький магазин у дома. Нужно молоко, яблоки и корм для кота Box. | Корма для кошек нет, зато Box любит молоко. Анна и Том покупают молоко и шесть яблок. |
| 06 | mia, tom, anna | Box так и не вернулся домой. Утром Анна и Том заходят к Мие на работу — в кафе на углу. | Мия встаёт в пять и работает в кафе каждый день. А ещё каждое утро в семь сюда приходит большой кот и пьёт её молоко. |
| 07 | mia, anna, tom | Вечер в кафе на углу. Мия наконец спрашивает Анну, чем она занимается. А потом разговор заходит о соседе сверху. | Анна — учительница, Том работает дома за компьютером, Мия — бариста. А сосед сверху работает ночью, каждую ночь в десять. |
| 08 | tom, passerby, anna | Том хочет сделать копию старого ключа для Анны. Но где в городке мастерская по ключам? | Мастерская — рядом с банком, а банк — справа, рядом с кафе Мии. Мастер берёт старый ключ и обещает сделать копию. |
| 09 | locksmith, anna | Копия ключа почти готова. Анна звонит в мастерскую, чтобы оставить имя и номер для заказа. | Мастер записывает фамилию Анны по буквам — Belova — и её номер. Мастерская открывается в девять. |
| 10 | mia, anna, tom | Субботнее утро в кафе на углу. Мия спрашивает Анну и Тома, как они проводят выходные. | Анна по субботам читает, а в октябре по воскресеньям гуляет в парке в куртке. Том никогда не гуляет, зато играет на гитаре — и Box это нравится. Мия работает даже в воскресенье, с пяти утра. |
| 11 | doctor, tom | В понедельник утром у Тома болит голова. Анна отправляет его к врачу. | Голова болит не каждый день, зато болит спина, и Том плохо спит. Врач советует отдохнуть дома, пить воду и не сидеть ночью за компьютером. |
| 12 | postal, anna, tom | Анна несёт на почту письмо маме в Россию. Том идёт с ней и заодно хочет спросить про старый почтовый ящик. | Письмо уходит в Россию — марка стоит два доллара. А почтальон удивлён: в старый ящик у их калитки письма никогда не приходят. |
| 13 | mia, anna, tom | Вечер в кафе Мии. Том и Мия узнают, что Анна говорит по-русски. | Анна проведёт первый урок русского для Тома и Мии в субботу в десять. Том хочет понимать русскую музыку, а Мии нравятся русские буквы. |
| 14 | anna, busdriver, tom | После урока русского Анна и Том садятся в автобус до Park Street — это слова с обратной стороны старого фото. | Билет стоит два доллара, обратный автобус — в шесть. На Park Street правда есть маленькое фотоателье. Но сегодня суббота, и дверь закрыта. |

Weeks 6, 7, 10 and 13 now share the actual cafe setting instead of presenting the discussed topic as the location. Weeks 7 and 13 use cooler evening exteriors with warm interior materials, because evening is explicit. Week 6 adds the clock motif; week 10 adds a calendar; week 13 adds an open notebook. These small objects are editorial motifs, not assertions that those objects were present in the dialogue. Existing faces are unchanged.

## Asset and accessibility contract
- SVG is retained for vectors: small, resolution independent, no raster conversion required. The existing cafe asset remains WebP.
- Catalogue images are redundant with adjacent chapter titles and retain empty alt; chapter hero images have scene descriptions.
- The hero and catalogue use the existing object-fit/object-position rules. Their actual mobile crops require browser review; source coordinates alone are not proof of successful cropping.
- Phrase roles can be opened by word or caption; Enter/Space activate word controls and Escape closes the panel. Outside press, focus departure and resize dismiss it; scroll repositions the panel so mobile focus scrolling does not close it. Translation stays static.
- The explanation panel is fixed outside the card's layout. No educational marker colors or classifications change. GSAP only fades the panel in full motion; it is not required for the explanation.
- Without JavaScript, the phrase, translation and original role captions remain visible. No running animation is required to read the site.

## Browser acceptance evidence
Real Chromium comparisons now pass in GitHub Actions run [39329659244](https://github.com/konstantin532/English-Encyclopedia/actions/runs/39329659244), against main `7d27a5a`. All three demonstration screens were compared at 1440×900, 1280×800, 390×844 and 360×800. Maximum measured difference in the selected components' x/y/width/height was 0 px in every pair. The hero also retains its document-space bounds while discovery is open. All 14 chapter images load at 390 px; tested pages have no horizontal overflow or uncaught JS errors. No-JS homepage reading and full-motion discovery passed.

The first real run found a mobile focus-scroll dismissal bug, which was fixed. The second found a test-coordinate error (viewport y changes when a page scrolls), corrected to document coordinates. No app geometry rule was changed to make the test pass.

See [the QA report](../qa/living-atlas-browser-review.md) for screenshots, scope and limitations. The local browser limitation was overcome with hosted Chromium; it is no longer a blocker to the three-screen review.

## Remaining artistic scope
Full-scale redesign of every lesson, dictionary, trainer, progress and speech screen is not claimed by this checkpoint. Those screens continue to use the inherited editorial system. A richer multi-construction linguistic diagram system and reconciliation of photographic/vector character identities remain future work. Android/TalkBack, real audio playback (audio files are not in the checkout), exhaustive contrast analysis and performance measurements remain undone.
