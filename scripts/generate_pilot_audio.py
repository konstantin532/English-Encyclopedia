"""Озвучка контрольного пакета пилота A1 (docs/pilots/a1-four-weeks/assessment.yaml).

Запуск:
    uv run python scripts/generate_pilot_audio.py --output static/audio/pilot-a1
    uv run python scripts/generate_pilot_audio.py --engine test --output static/audio/pilot-a1   # тоны, без модели

Пишет только в static/audio/pilot-a1/ (папки w01…w04, pre, post, delayed с manifest.json),
учебные weeks/, stories/ и twisters/ не трогает. Использует render() основного генератора без изменений.
Тестовый движок даёт тоны: это проверка конвейера, а не произношения.
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("generate_story_audio", HERE / "generate_story_audio.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

PACKAGE = HERE.parent / "docs" / "pilots" / "a1-four-weeks" / "assessment.yaml"


def allowed_root() -> Path:
    """Разрешённая папка без перехода по ссылкам: подмена pilot-a1 ссылкой на weeks/ не должна сработать."""
    return Path(os.path.abspath(gen.ROOT / "static" / "audio" / "pilot-a1"))


def refuse_symlinks(path: Path, root: Path) -> None:
    """Ни сама папка, ни один шаг от неё до pilot-a1 (включительно) не может быть символической ссылкой."""
    step = path
    while True:
        if step.is_symlink():
            sys.exit(f"Отказ: {step} — символическая ссылка; запись разрешена только в настоящую папку {root}")
        if step == root or step.parent == step:
            return
        step = step.parent


def checked_output(path: str) -> Path:
    """Папка вывода — только pilot-a1 или её подпапка; проверка до любой записи."""
    root, out = allowed_root(), Path(os.path.abspath(path))
    if out != root and root not in out.parents:
        sys.exit(f"--output должен быть внутри {root}, получено {out}")
    refuse_symlinks(out, root)
    return out


def entries(data: dict):
    for entry in data.get("weekly", []) + data.get("forms", []):
        yield entry["id"], entry["script"]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=["kokoro", "test"], default="kokoro")
    ap.add_argument("--output", required=True, help="папка внутри static/audio/pilot-a1")
    ap.add_argument("--models", type=Path, default=gen.MODELS)
    args = ap.parse_args(argv)
    out = checked_output(args.output)
    data = yaml.safe_load(PACKAGE.read_text(encoding="utf-8"))
    voices = yaml.safe_load((HERE.parent / "content" / "manifests" / "voices.yaml").read_text(encoding="utf-8"))
    engine = gen.KokoroEngine(args.models) if args.engine == "kokoro" else gen.TestEngine()
    for entry_id, script in entries(data):
        refuse_symlinks(out / entry_id, allowed_root())
        rendered = gen.render(engine, f"проба {entry_id}", script, voices["roles"], voices, out / entry_id, data["level"])
        print(f"Проба {entry_id}: " + ", ".join(f"{k} {v['seconds']} с" for k, v in rendered.items()))


if __name__ == "__main__":
    main()
