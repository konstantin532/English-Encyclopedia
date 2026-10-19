"""Review-gate fixtures test provenance, not whether synthetic audio sounds natural."""
import copy
import csv
import json
import tempfile
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase

from scripts.approve_audio_review import approve
from scripts.audio_readiness import check_audio, expected_manifests, validate_manifest, TEMPOS
from scripts.audio_review_sheet import HEADERS, rows
from tests.test_audio_recovery import write_audio_bundle


class AudioHumanReviewGateTests(SimpleTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for manifest in expected_manifests(self.root):
            folder = manifest.parent.relative_to(self.root / "static/audio").as_posix()
            write_audio_bundle(self.root, folder)
        self.sheet = self.root / "audio-review.csv"
        self.original = list(rows(self.root))
        self.assertEqual(len(self.original), 99)
        self.data = [dict(row) for row in self.original]
        self.approve_fields()

    def approve_fields(self):
        for row in self.data:
            row.update(
                reviewer="Qualified reviewer", review_date=date.today().isoformat(),
                american_vowels="pass", word_stress="pass",
                pauses_and_intonation="pass", names_and_numbers="pass",
                manual_approved="yes",
            )

    def write_sheet(self):
        with self.sheet.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, HEADERS)
            writer.writeheader()
            writer.writerows(self.data)

    def first_manifest(self):
        return next(expected_manifests(self.root))

    def test_full_explicit_review_promotes_all_99_tracks_and_is_verifiable(self):
        self.write_sheet()
        self.assertEqual(approve(self.root, self.sheet, dry_run=True), 33)
        self.assertEqual(check_audio(self.root)["unreviewed"].__len__(), 33)
        self.assertFalse(json.loads(self.first_manifest().read_text())["verified"])
        self.assertEqual(approve(self.root, self.sheet), 33)
        audit = check_audio(self.root)
        self.assertEqual(audit["files_present"], 33)
        self.assertEqual(audit["unreviewed"], [])
        updated = json.loads(self.first_manifest().read_text())
        self.assertEqual(updated["human_review"]["method"], "manual-listening")
        self.assertEqual(set(updated["human_review"]["tracks"]), set(TEMPOS))
        self.assertIsNone(validate_manifest(updated, self.root / "static"))

    def test_direct_verified_flag_without_record_is_not_accepted(self):
        m = self.first_manifest()
        data = json.loads(m.read_text())
        data["verified"] = True
        self.assertIn("без подтверждения", validate_manifest(data, self.root / "static"))

    def test_changed_audio_after_approval_loses_verified_status(self):
        self.write_sheet()
        approve(self.root, self.sheet)
        manifest = self.first_manifest()
        data = json.loads(manifest.read_text())
        audio = self.root / "static" / data["natural"]["file"]
        with audio.open("ab") as f:
            f.write(b"tamper")
        self.assertIn("изменена", validate_manifest(data, self.root / "static"))
        self.assertEqual(len(check_audio(self.root)["invalid"]), 1)

    def test_modified_source_audio_before_review_is_rejected_without_publishing(self):
        self.write_sheet()
        first = self.first_manifest()
        original = first.read_bytes()
        data = json.loads(first.read_text())
        target = self.root / "static" / data["slow"]["file"]
        with target.open("ab") as f:
            f.write(b"different-track")
        with self.assertRaisesMessage(ValueError, "изменён после экспорта"):
            approve(self.root, self.sheet)
        self.assertEqual(first.read_bytes(), original)
        self.assertFalse(json.loads(first.read_text())["verified"])

    def test_all_or_nothing_for_invalid_review_rows(self):
        self.write_sheet()
        initial = {m: m.read_bytes() for m in expected_manifests(self.root)}
        invalids = [
            ("missing-row", lambda d: d.pop()),
            ("duplicate-row", lambda d: d.append(copy.deepcopy(d[0]))),
            ("not-approved", lambda d: d[98].update(manual_approved="")),
            ("failed-stress", lambda d: d[98].update(word_stress="fail")),
            ("missing-reviewer", lambda d: d[98].update(reviewer="")),
            ("wrong-date", lambda d: d[98].update(review_date="19/10/2026")),
            ("wrong-sha", lambda d: d[98].update(sha256="0" * 64)),
            ("different-bundle-reviewer", lambda d: d[0].update(reviewer="Another person")),
            ("fake-track", lambda d: d[0].update(tempo="fake")),
        ]
        for name, corrupt in invalids:
            with self.subTest(case=name):
                self.data = [dict(row) for row in self.original]
                self.approve_fields()
                corrupt(self.data)
                self.write_sheet()
                with self.assertRaises(ValueError):
                    approve(self.root, self.sheet)
                self.assertTrue(all(m.read_bytes() == original for m, original in initial.items()))
        self.assertEqual(len(check_audio(self.root)["unreviewed"]), 33)


    def test_release_packaging_requires_complete_human_approval(self):
        from scripts.package_audio_archive import package_audio
        from zipfile import ZipFile

        release = self.root / "approved-audio.zip"
        with self.assertRaisesMessage(ValueError, "непроверенный архив"):
            package_audio(self.root, release, require_reviewed=True)
        self.assertFalse(release.exists())
        self.write_sheet()
        approve(self.root, self.sheet)
        package_audio(self.root, release, require_reviewed=True)
        with ZipFile(release) as archive:
            names = archive.namelist()
        self.assertEqual(sum(x.endswith("/manifest.json") for x in names), 33)
        self.assertTrue(all(x.startswith("static/audio/") for x in names))
