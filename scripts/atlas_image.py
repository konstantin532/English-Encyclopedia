"""Make site-sized WebP files from a generated illustration.

    uv run --with pillow python scripts/atlas_image.py SOURCE KEY [--portrait] [--focus-y 0.5]

Covers  -> static/img/atlas/KEY-1536.webp (1536x864) and KEY-800.webp (800x450), 16:9.
Portrait -> static/img/atlas/KEY.webp (420x420).
The crop is centred horizontally; --focus-y chooses the vertical centre (0 top .. 1 bottom).
See .agents/skills/ee-illustration/SKILL.md.
"""
import argparse
from pathlib import Path

from PIL import Image

ATLAS = Path(__file__).resolve().parents[1] / "static" / "img" / "atlas"
COVER_SIZES = ((1536, 864), (800, 450))
PORTRAIT_SIZE = (420, 420)
QUALITY = 82
COVER_BUDGET = 250 * 1024


def crop_to_ratio(image, ratio, focus_y=0.5):
    width, height = image.size
    if width / height > ratio:
        new_width = round(height * ratio)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = round(width / ratio)
    top = round((height - new_height) * min(max(focus_y, 0.0), 1.0))
    return image.crop((0, top, width, top + new_height))


def save(image, size, path):
    image.resize(size, Image.LANCZOS).save(path, "WEBP", quality=QUALITY, method=6)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("key", help="e.g. a1-w12, s06, portrait-leo")
    parser.add_argument("--portrait", action="store_true")
    parser.add_argument("--focus-y", type=float, default=0.5)
    args = parser.parse_args()

    image = Image.open(args.source).convert("RGB")
    if args.portrait:
        written = [save(crop_to_ratio(image, 1.0, args.focus_y), PORTRAIT_SIZE, ATLAS / f"{args.key}.webp")]
    else:
        if image.width < COVER_SIZES[0][0]:
            raise SystemExit(f"Source is {image.width}px wide; covers need at least {COVER_SIZES[0][0]}px.")
        cover = crop_to_ratio(image, 16 / 9, args.focus_y)
        written = [save(cover, size, ATLAS / f"{args.key}-{size[0]}.webp") for size in COVER_SIZES]
    for path in written:
        kb = path.stat().st_size / 1024
        note = "  <- больше 250 КБ, уменьшите детализацию или качество" if path.name.endswith("-1536.webp") and kb * 1024 > COVER_BUDGET else ""
        print(f"{path.relative_to(ATLAS.parents[2])}: {Image.open(path).size[0]}x{Image.open(path).size[1]}, {kb:.0f} KB{note}")


if __name__ == "__main__":
    main()
