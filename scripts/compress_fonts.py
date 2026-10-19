from pathlib import Path
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parents[1] / "static/fonts"
for source in root.glob("*.ttf"):
    font = TTFont(source, recalcTimestamp=False)
    before = set(font.getBestCmap())
    font.flavor = "woff2"
    target = source.with_suffix(".woff2")
    font.save(target)
    restored = TTFont(target)
    assert set(restored.getBestCmap()) == before
    print(
        source.name,
        source.stat().st_size,
        "->",
        target.stat().st_size,
        "glyph-map preserved",
        len(before),
    )
