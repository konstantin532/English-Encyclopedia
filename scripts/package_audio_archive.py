"""Package generated audio with the static/audio prefix required by Render."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def package_audio(root: Path, output: Path):
    audio = (root / "static/audio").resolve()
    if output.resolve().is_relative_to(audio):
        raise ValueError("Аудиоархив должен находиться вне static/audio")
    files = sorted(path for path in audio.rglob("*") if path.is_file())
    if not files:
        raise ValueError("Нет сгенерированных аудиофайлов")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root.resolve()).as_posix())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package_audio(Path.cwd(), args.output)


if __name__ == "__main__":
    main()
