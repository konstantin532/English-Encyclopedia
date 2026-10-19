"""Export track hashes + blank human listening rubric without auto-approving audio."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from scripts.audio_readiness import ROOT, TEMPOS, expected_manifests, validate_manifest

HEADERS = ["bundle", "tempo", "file", "sha256", "automated_structure_ok",
           "reviewer", "review_date", "american_vowels", "word_stress",
           "pauses_and_intonation", "names_and_numbers", "notes", "manual_approved"]


def rows(root=ROOT):
    for manifest in expected_manifests(root):
        label = manifest.relative_to(root).as_posix()
        if not manifest.is_file():
            yield {"bundle": label, "automated_structure_ok": "missing"}
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            error = validate_manifest(data, root / "static")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            error = str(exc)
            data = {}
        if error:
            yield {"bundle": label, "automated_structure_ok": "invalid: " + error}
            continue
        for tempo in TEMPOS:
            path = root / "static" / data[tempo]["file"]
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            yield {"bundle": label, "tempo": tempo, "file": data[tempo]["file"],
                   "sha256": digest, "automated_structure_ok": "yes"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows())
    print("Created human listening worksheet:", args.output)


if __name__ == "__main__":
    main()
