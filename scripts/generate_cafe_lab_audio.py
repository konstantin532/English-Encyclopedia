"""Generate genuine three-speed two-character audio for the isolated A1 café lab.

    uv sync --group audio
    uv run --group audio python scripts/generate_cafe_lab_audio.py
    uv run --group audio python scripts/generate_cafe_lab_audio.py --engine test

Kokoro output: static/audio/cafe-lab/ (can be served after deployment).
Test-tone output: static/audio/cafe-lab-test/ (NEVER selected by the website).
The original week 3 audio and learning content remain unchanged.
"""
import argparse
import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from apps.core.cafe_lab import CAFE_DIALOGUE  # noqa: E402

spec = importlib.util.spec_from_file_location("generate_story_audio", ROOT / "scripts" / "generate_story_audio.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engine", choices=("kokoro", "test"), default="kokoro")
    parser.add_argument("--models", type=Path, default=gen.MODELS)
    args = parser.parse_args(argv)
    voices = yaml.safe_load((ROOT / "content" / "manifests" / "voices.yaml").read_text(encoding="utf-8"))
    if args.engine == "kokoro":
        engine = gen.KokoroEngine(args.models)
        folder = gen.OUT / "cafe-lab"
    else:
        engine = gen.TestEngine()
        folder = gen.OUT / "cafe-lab-test"
    if folder.is_symlink():
        parser.error("Output directory must not be a symlink")
    script = [{"speaker": line["speaker"], "text": line["text"]} for line in CAFE_DIALOGUE]
    rendered = gen.render(engine, "cafe-lab", script, voices["roles"], voices, folder, "A1")
    print(f"{engine.name}: {len(script)} lines, "
          + ", ".join(f"{tempo} {data['seconds']}s" for tempo, data in rendered.items()))
    print(f"Output: {folder}")


if __name__ == "__main__":
    main()
