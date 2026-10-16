import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase
from django.test import tag

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("pilot_audio", ROOT / "scripts" / "generate_pilot_audio.py")
pilot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pilot)


@tag("slow")  # намеренно ломает и перезагружает весь курс; полный прогон — перед слиянием
class PilotAudioTests(SimpleTestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "static" / "audio" / "pilot-a1").mkdir(parents=True)
        for name, value in (("ROOT", self.tmp), ("OUT", self.tmp / "static" / "audio")):
            p = mock.patch.object(pilot.gen, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.out = self.tmp / "static" / "audio" / "pilot-a1"

    def test_pilot_audio_files_and_timings(self):
        before = pilot.PACKAGE.read_text(encoding="utf-8")
        for _ in range(2):  # повторный запуск тоже работает
            pilot.main(["--engine", "test", "--output", str(self.out)])
        manifests = sorted(self.out.glob("*/manifest.json"))
        self.assertEqual([m.parent.name for m in manifests], sorted(["w01", "w02", "w03", "w04", "pre", "post", "delayed"]))
        for m in manifests:
            data = json.loads(m.read_text(encoding="utf-8"))
            self.assertFalse(data["verified"])
            for tempo in ("very_slow", "slow", "natural"):
                self.assertTrue((self.tmp / "static" / data[tempo]["file"]).exists())
                starts = [t["start"] for t in data[tempo]["timings"]]
                self.assertEqual(starts, sorted(starts))
                self.assertTrue(all(t["end"] > t["start"] for t in data[tempo]["timings"]))
        self.assertEqual(pilot.PACKAGE.read_text(encoding="utf-8"), before)

    def test_output_outside_pilot_folder_rejected(self):
        for bad in (self.tmp / "static" / "audio" / "weeks", self.out / ".." / "stories", self.tmp / "elsewhere"):
            with self.subTest(path=bad), self.assertRaises(SystemExit):
                pilot.main(["--engine", "test", "--output", str(bad)])
        self.assertFalse((self.tmp / "static" / "audio" / "weeks").exists())

    def test_output_is_required(self):
        with self.assertRaises(SystemExit):
            pilot.main(["--engine", "test"])


class PilotAudioPathSafetyTests(PilotAudioTests.__mro__[0]):
    def test_symlinked_root_rejected(self):
        weeks = self.tmp / "static" / "audio" / "weeks"
        weeks.mkdir()
        shutil.rmtree(self.out)
        self.out.symlink_to(weeks, target_is_directory=True)
        with self.assertRaises(SystemExit):
            pilot.main(["--engine", "test", "--output", str(self.out)])
        self.assertEqual(list(weeks.iterdir()), [])

    def test_symlinked_subfolder_rejected(self):
        weeks = self.tmp / "static" / "audio" / "weeks"
        weeks.mkdir()
        (self.out / "w01").symlink_to(weeks, target_is_directory=True)
        with self.assertRaises(SystemExit):
            pilot.main(["--engine", "test", "--output", str(self.out)])
        self.assertEqual(list(weeks.iterdir()), [])

    def test_prefix_trick_rejected(self):
        with self.assertRaises(SystemExit):
            pilot.main(["--engine", "test", "--output", str(self.tmp / "static" / "audio" / "pilot-a1-evil")])


class PilotEntryIdTests(PilotAudioTests.__mro__[0]):
    """Замечание P1 бота Codex в PR #4: имя разговора не должно выводить запись за pilot-a1."""

    def test_entry_id_cannot_escape_pilot_folder(self):
        weeks = self.tmp / "static" / "audio" / "weeks" / "a1-w01"
        weeks.mkdir(parents=True)
        for bad_id in ("../weeks/a1-w01", "/tmp/evil", "w01/../../weeks", ""):
            package = self.tmp / "package.yaml"
            package.write_text(
                "level: A1\nweekly:\n  - id: \"%s\"\n    max_week: 1\n    script:\n"
                "      - speaker: anna\n        text: \"[T8]I[/] [D1]am[/] [S1]Anna[/].\"\nforms: []\n" % bad_id,
                encoding="utf-8")
            with self.subTest(entry_id=bad_id), mock.patch.object(pilot, "PACKAGE", package):
                with self.assertRaises(SystemExit):
                    pilot.main(["--engine", "test", "--output", str(self.out)])
            self.assertEqual(list(weeks.iterdir()), [])
