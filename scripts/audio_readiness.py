"""Audit the presence of A1 audio files; not an assessment of pronunciation.

Default mode is a truthful diagnostic. --strict refuses missing or test-tone
artifacts before deploying a site claiming generated audio.
"""
import argparse
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPOS = ("very_slow", "slow", "natural")
REVIEW_CRITERIA = ("american_vowels", "word_stress", "pauses_and_intonation", "names_and_numbers")


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



def review_evidence_problem(data: dict, static: Path) -> str | None:
    """Check a human attestation is complete and bound to THESE audio bytes.

    This is integrity/provenance validation, never acoustic certification.
    A reviewer must still actually listen and complete the rubric.
    """
    review = data.get("human_review")
    if not isinstance(review, dict) or review.get("method") != "manual-listening":
        return "verified=true без подтверждения ручного прослушивания"
    reviewer, reviewed = review.get("reviewer"), review.get("review_date")
    if (not isinstance(reviewer, str) or not reviewer.strip()
            or len(reviewer.strip()) > 120 or not isinstance(reviewed, str)):
        return "не указаны автор и дата проверки голоса"
    try:
        if date.fromisoformat(reviewed).isoformat() != reviewed:
            return "дата прослушивания должна быть YYYY-MM-DD"
    except ValueError:
        return "неверная дата прослушивания"
    tracks = review.get("tracks")
    if not isinstance(tracks, dict) or set(tracks) != set(TEMPOS):
        return "ручная проверка должна охватывать все три скорости"
    for tempo in TEMPOS:
        record = tracks[tempo]
        if not isinstance(record, dict):
            return f"неверная запись прослушивания {tempo}"
        if any(record.get(field) != "pass" for field in REVIEW_CRITERIA):
            return f"неполная оценка произношения {tempo}"
        expected = record.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            return f"нет SHA256 проверенной дорожки {tempo}"
        track = (static / data[tempo]["file"]).resolve()
        with track.open("rb") as file:
            digest = hashlib.file_digest(file, "sha256").hexdigest()
        if digest != expected:
            return f"дорожка {tempo} изменена после ручной проверки"
    return None


def validate_manifest(data: dict, static: Path) -> str | None:
    """Returns a reason to refuse this bundle. Checks existence, not spoken quality."""
    if not isinstance(data, dict) or data.get("engine") != "kokoro" or not str(data.get("model", "")).startswith("kokoro-v"):
        return "проверочный тон или неизвестный движок"
    static = static.resolve()
    timeline_lengths = set()
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
        # The player's highlight() calls .findIndex() on each timeline:
        # valid sound with missing timestamps makes interactive text unusable.
        times = entry.get("timings")
        if not isinstance(times, list) or not times:
            return f"нет таймингов реплик {tempo}"
        seconds = entry.get("seconds")
        if (type(seconds) not in (int, float) or not math.isfinite(seconds)
                or seconds <= 0):
            return f"неверная длительность дорожки {tempo}"
        previous_end = 0.0
        for index, segment in enumerate(times):
            if (not isinstance(segment, dict) or type(segment.get("line")) is not int
                    or segment["line"] != index):
                return f"неверный номер реплики {tempo}/{index}"
            start, end = segment.get("start"), segment.get("end")
            if (type(start) not in (int, float) or type(end) not in (int, float)
                    or not math.isfinite(start) or not math.isfinite(end)
                    or start < previous_end or end <= start or end > seconds + 0.15):
                return f"неверные тайминги реплики {tempo}/{index}"
            previous_end = end
        timeline_lengths.add(len(times))
    if len(timeline_lengths) != 1:
        return "разное количество реплик между скоростями"
    if data.get("verified") is True:
        return review_evidence_problem(data, static)
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
    parser.add_argument("--require-reviewed", action="store_true",
                        help="Reject structurally valid Kokoro tracks without complete manual review")
    args = parser.parse_args()
    result = check_audio()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int((args.strict and bool(result["missing"] or result["invalid"]))
               or (args.require_reviewed and bool(result["missing"] or result["invalid"]
                                                  or result["unreviewed"])))


if __name__ == "__main__":
    raise SystemExit(main())
