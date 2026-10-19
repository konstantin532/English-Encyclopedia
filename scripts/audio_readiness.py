"""Audit the presence of A1 audio files; not an assessment of pronunciation.

Default mode is a truthful diagnostic. --strict refuses missing or test-tone
artifacts before deploying a site claiming generated audio.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPOS = ("very_slow", "slow", "natural")


def expected_manifests(root: Path):
    audio = root / "static" / "audio"
    for i in range(1, 6):
        yield audio / "stories" / f"s{i:02d}" / "manifest.json"
    for i in range(1, 15):
        yield audio / "weeks" / f"a1-w{i:02d}" / "manifest.json"
    for i in range(1, 15):
        yield audio / "twisters" / f"t{i:03d}" / "manifest.json"


def plausible_audio_header(path: Path) -> bool:
    """A signature check, not a decoder or human pronunciation review."""
    with path.open("rb") as track:
        header = track.read(12)
    if path.suffix.lower() == ".wav":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    if path.suffix.lower() == ".mp3":
        return header.startswith(b"ID3") or (
            len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
        )
    return False


def validate_manifest(data: dict, static: Path) -> str | None:
    """Returns a reason to refuse this bundle. Checks existence, not spoken quality."""
    if not isinstance(data, dict) or data.get("engine") != "kokoro" or not str(data.get("model", "")).startswith("kokoro-v"):
        return "проверочный тон или неизвестный движок"
    static = static.resolve()
    for tempo in TEMPOS:
        entry = data.get(tempo)
        path = entry.get("file") if isinstance(entry, dict) else None
        if not isinstance(path, str) or not path.strip():
            return f"отсутствует дорожка {tempo}"
        rel = Path(path)
        candidate = (static / rel).resolve()
        if (rel.is_absolute() or not candidate.is_relative_to(static)
                or not candidate.is_file() or not candidate.stat().st_size):
            return f"нет файла дорожки {tempo} или путь вне static"
        if not plausible_audio_header(candidate):
            return f"дорожка {tempo} не похожа на WAV/MP3"
    return None


def check_audio(root: Path = ROOT) -> dict:
    static = (root / "static").resolve()
    missing, invalid, unreviewed, present = [], [], [], []
    for manifest in expected_manifests(root):
        label = str(manifest.relative_to(root))
        if not manifest.is_file():
            missing.append(label)
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            issue = validate_manifest(data, static)
            if issue:
                raise ValueError(issue)
            present.append(label)
            if data.get("verified") is not True:
                unreviewed.append(label)
        except (ValueError, OSError) as exc:
            invalid.append(f"{label}: {exc}")
    return {"expected": 33, "files_present": len(present), "missing": missing,
            "invalid": invalid, "unreviewed": unreviewed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = check_audio()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(args.strict and bool(result["missing"] or result["invalid"]))


if __name__ == "__main__":
    raise SystemExit(main())
