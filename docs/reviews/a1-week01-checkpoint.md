> Продолжение после согласования: [итог всех 28 уроков](a1-plain-language-complete.md). Семь проблем, перечисленных ниже на историческом этапе, устранены; общий тест проходит.

# A1 plain language — week-one review checkpoint

Branch: codex/a1-plain-language-week01-20261027
Base:341f2538 (depends on unmerged lesson-core simplification; no merge to main).

Scope for this checkpoint: only lessons1–2 and their guide text. Existing vocabulary IDs, English word inventory, exercise/practice counts, UIDs, answer keys, accepted variants and options are preserved. No lexicon files, models or migrations changed. Shared renderer adds a safe closed Для любопытных paragraph. Shared speech task template no longer adds a duplicate period after a complete scene sentence.

Verification:29 affected lightweight tests PASS in0.672s. Original vocabulary/answer invariants separately compared with HEAD and PASS. The global rendered-text check for all28 A1 lessons is implemented and intentionally has no skips or baseline exceptions. It currently reports7 remaining problems outside week one: T2 in a1-determiners-a-the-this-my; T3 in a1-family-possession; ASCII ellipsis in a1-have-like-can-do, a1-cafe-order, a1-family-photo, a1-where-is-prepositions, a1-what-hurts. These remain for the next course-wide editing stage after the requested week-one diff review.

Browser verification for this checkpoint:BLOCKED by failed browser session/tab binding. The two lessons were safely updated in the isolated preview database without deletes; exercise IDs and answers unchanged. Original F: checkout/database untouched.

Full patch before this note: a1-week01-plain-language.diff.
