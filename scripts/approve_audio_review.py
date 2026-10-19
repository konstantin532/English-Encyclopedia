"""Promote 33 Kokoro bundles only after human review of all 99 tracks.

The reviewer must listen and manually fill the CSV created by
scripts.audio_review_sheet. This code verifies completeness and SHA256
integrity; it cannot independently judge pronunciation or reviewer identity.
"""
import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from scripts.audio_readiness import (
    ROOT, TEMPOS, REVIEW_CRITERIA, expected_manifests, validate_manifest,
)
from scripts.audio_review_sheet import HEADERS


def _read_review_date(value):
    try:
        if date.fromisoformat(value).isoformat() == value:
            return value
    except (TypeError, ValueError):
        pass
    raise ValueError("review_date должен быть датой YYYY-MM-DD")


def prepare_approvals(root: Path, sheet: Path) -> dict[Path, dict]:
    """Validate the *entire* sheet before changing any manifest."""
    root = root.resolve()
    manifest_data = {}
    expected_rows = {}

    for manifest in expected_manifests(root):
        if not manifest.is_file():
            raise ValueError(f"Нет комплекта: {manifest.relative_to(root)}")
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError(f"Повреждён манифест {manifest}: {exc}") from exc
        problem = validate_manifest(data, root / "static")
        if problem:
            raise ValueError(f"Комплект {manifest.name} не готов: {problem}")
        label = manifest.relative_to(root).as_posix()
        manifest_data[label] = (manifest, data)
        for tempo in TEMPOS:
            file = data[tempo]["file"]
            with (root / "static" / file).open("rb") as track:
                digest = hashlib.file_digest(track, "sha256").hexdigest()
            expected_rows[(label, tempo)] = (file, digest)

    with sheet.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if not reader.fieldnames or not set(HEADERS).issubset(reader.fieldnames):
            raise ValueError("Неверные колонки таблицы прослушивания")
        actual_rows = {}
        for row in reader:
            key = (row.get("bundle"), row.get("tempo"))
            if key not in expected_rows:
                raise ValueError(f"Лишняя или неизвестная аудиодорожка: {key}")
            if key in actual_rows:
                raise ValueError(f"Дублирующаяся аудиодорожка: {key}")
            file, digest = expected_rows[key]
            if (row.get("automated_structure_ok") != "yes"
                    or row.get("file") != file or row.get("sha256") != digest):
                raise ValueError(f"Файл изменён после экспорта таблицы: {key}")
            if row.get("manual_approved", "").strip().lower() != "yes":
                raise ValueError(f"Нет явного одобрения прослушивания: {key}")
            for criterion in REVIEW_CRITERIA:
                if row.get(criterion, "").strip().lower() != "pass":
                    raise ValueError(f"Не пройдено {criterion}: {key}")
            reviewer = row.get("reviewer", "").strip()
            if not reviewer or len(reviewer) > 120:
                raise ValueError(f"Не указан автор проверки: {key}")
            reviewed = _read_review_date(row.get("review_date"))
            actual_rows[key] = {
                "reviewer": reviewer, "review_date": reviewed, "sha256": digest,
                **{criterion: "pass" for criterion in REVIEW_CRITERIA},
            }

    absent = sorted(set(expected_rows) - set(actual_rows))
    if absent:
        raise ValueError(f"Не прослушано {len(absent)} дорожек; первая: {absent[0]}")
    if len(actual_rows) != 33 * len(TEMPOS):
        raise ValueError(f"Ожидалось 99 проверенных дорожек, найдено {len(actual_rows)}")

    approved = {}
    for label, (manifest, data) in manifest_data.items():
        records = [actual_rows[(label, tempo)] for tempo in TEMPOS]
        names = {row["reviewer"] for row in records}
        dates = {row["review_date"] for row in records}
        if len(names) != 1 or len(dates) != 1:
            raise ValueError(f"У комплекта {label} разные авторы или даты: оформите одобрение отдельно")
        data["verified"] = True
        data["human_review"] = {
            "method": "manual-listening",
            "reviewer": records[0]["reviewer"],
            "review_date": records[0]["review_date"],
            "tracks": {
                tempo: {
                    "sha256": actual_rows[(label, tempo)]["sha256"],
                    **{criterion: "pass" for criterion in REVIEW_CRITERIA},
                }
                for tempo in TEMPOS
            },
        }
        problem = validate_manifest(data, root / "static")
        if problem:
            raise ValueError(f"Не получилось подтвердить {label}: {problem}")
        approved[manifest] = data
    return approved


def approve(root: Path, sheet: Path, *, dry_run: bool = False) -> int:
    approvals = prepare_approvals(root, sheet)
    if not dry_run:
        for manifest, data in approvals.items():
            # One-file atomic replacement; no modifications occur until the
            # entire 99-track sheet has passed validation.
            pending = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=manifest.parent,
                    prefix=".reviewed-", suffix=".json", delete=False,
                ) as stream:
                    pending = Path(stream.name)
                    json.dump(data, stream, ensure_ascii=False, indent=2)
                os.replace(pending, manifest)
            finally:
                if pending is not None:
                    pending.unlink(missing_ok=True)
    return len(approvals)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, required=True, help="Заполненная человеком таблица CSV")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--dry-run", action="store_true",
                        help="Только проверить 99 записей без изменения манифестов")
    args = parser.parse_args(argv)
    try:
        count = approve(args.root, args.sheet, dry_run=args.dry_run)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Не удалось подтвердить аудио: {exc}\n")
    print(f"{count} аудиокомплектов прошли документированную ручную проверку "
          f"({'без изменений' if args.dry_run else 'манифесты обновлены'}). "
          "Само прослушивание не выполняется программой.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
