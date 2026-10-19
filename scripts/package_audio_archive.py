"""Package generated audio with the static/audio prefix required by Render."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def package_audio(root: Path, output: Path, *, require_reviewed: bool = False):
    if require_reviewed:
        # The Kokoro synthesis workflow must still be allowed to distribute
        # unreviewed audio for listening. Only the FINAL reviewed release
        # is required to pass this stronger gate.
        from scripts.audio_readiness import check_audio
        result = check_audio(root)
        if result["missing"] or result["invalid"] or result["unreviewed"]:
            raise ValueError(
                "Нельзя выпускать непроверенный архив: "
                f"отсутствуют {len(result['missing'])}, повреждены {len(result['invalid'])}, "
                f"не прослушаны {len(result['unreviewed'])} комплектов"
            )
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
    parser.add_argument("--require-reviewed", action="store_true",
                        help="Выпускать архив только после одобрения всех 99 дорожек")
    args = parser.parse_args()
    package_audio(Path.cwd(), args.output, require_reviewed=args.require_reviewed)


if __name__ == "__main__":
    main()
