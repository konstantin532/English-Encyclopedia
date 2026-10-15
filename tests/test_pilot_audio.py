import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("pilot_audio", ROOT / "scripts" / "generate_pilot_audio.py")
pilot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pilot)


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
