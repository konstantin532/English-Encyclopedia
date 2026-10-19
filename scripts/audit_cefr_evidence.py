"""An evidence audit, NOT CEFR certification.

Read authored sense-level records, distinguish internal course level from CEFR,
reject unsupported 'verified' claims, and report pending human review.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEVELS = {"A1", "A2", "B1", "B2", "C1", "unverified"}
STATUSES = {"pending", "partial", "verified"}
UNCERTAIN = ("требует проверки", "не сверял", "значение отдельно не сверялось",
             "pending", "unverified")


def inspect(root=ROOT):
    counts = Counter()
    problems, warnings = [], []
    identifiers, senses = set(), set()
    files = sorted((root / "content" / "seed_lexicon").glob("*.yaml"))
    for path in files:
        try:
            pack = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (ValueError, yaml.YAMLError) as exc:
            problems.append(f"{path.name}: invalid YAML: {exc}")
            continue
        if not isinstance(pack, dict) or not isinstance(pack.get("units"), list):
            problems.append(f"{path.name}: missing units list")
            continue
        if pack.get("level") != "A1":
            continue
        for row in pack["units"]:
            counts["total"] += 1
            if not isinstance(row, dict):
                problems.append(f"{path.name}: unit must be an object")
                continue
            uid = row.get("uid")
            name = row.get("lemma")
            meaning = row.get("meaning")
            clazz = row.get("class")
            cefr = row.get("cefr", "unverified")
            status = row.get("verification_status", "pending")
            note = row.get("verification_note", "")
            if not all(isinstance(value, str) and value.strip() for value in (uid, name, meaning, clazz)):
                problems.append(f"{path.name}:{uid}: missing unit identity/meaning")
                continue
            if uid in identifiers:
                problems.append(f"{path.name}:{uid}: duplicate unit ID")
            identifiers.add(uid)
            key = (name.casefold().strip(), meaning.casefold().strip(), clazz)
            if key in senses:
                warnings.append(f"{uid}: duplicate lemma + sense + category")
            senses.add(key)
            if cefr not in LEVELS or status not in STATUSES:
                problems.append(f"{uid}: invalid cefr or verification status: {cefr}/{status}")
                continue
            counts["status_" + status] += 1
            counts["cefr_" + cefr] += 1
            if status == "verified":
                if cefr == "unverified" or not isinstance(note, str) or not note.strip() or any(
                    marker in note.casefold() for marker in UNCERTAIN
                ):
                    problems.append(f"{uid}: verified claim lacks a sense-specific, unqualified source note")
            elif status == "partial":
                if not isinstance(note, str) or not note.strip():
                    warnings.append(f"{uid}: partial status without evidence note")
                if cefr == "unverified":
                    warnings.append(f"{uid}: partial source match with no CEFR level")
            elif cefr != "unverified":
                warnings.append(f"{uid}: suggested {cefr} without verified source")
            if not str(row.get("ipa_us", "")).strip():
                warnings.append(f"{uid}: no American IPA")
    return {"counts": dict(counts), "errors": problems, "warnings": warnings,
            "sense_level_verified": counts["status_verified"],
            "interpretation": "Oxford lemma+POS matches are PARTIAL, not sense-level CEFR certification"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Reject structurally invalid or misleading verified labels")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = inspect()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("A1 lexicon evidence:", report["counts"])
        print("Sense-level verified:", report["sense_level_verified"])
        for message in report["errors"]:
            print("ERROR:", message)
        for message in report["warnings"][:20]:
            print("REVIEW:", message)
        print("Unresolved evidence items:", len(report["warnings"]))
    return int(args.strict and bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
