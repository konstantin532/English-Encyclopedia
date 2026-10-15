import hashlib
import importlib
import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from apps.curriculum.models import TongueTwister, WeekScene
from apps.stories.models import Story


class AudioManifestRecoveryTests(TestCase):
    def test_test_tones_are_not_published_as_speech(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("stories/s01", "weeks/a1-w01", "twisters/t001"):
                path = root / "static/audio" / folder / "manifest.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"engine": "test", "model": "test-tone",
                                           "natural": {"file": "tone.wav"}}), encoding="utf-8")
            with override_settings(BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
            self.assertEqual(Story.objects.get(number=1).audio, {})
            self.assertEqual(WeekScene.objects.get(week__level__code="A1", week__number=1).audio, {})
            self.assertEqual(TongueTwister.objects.get(number=1).audio, {})

    def test_real_speech_manifest_is_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {"engine": "kokoro", "natural": {"file": "speech.wav"}}
            for folder in ("stories/s01", "weeks/a1-w01", "twisters/t001"):
                path = root / "static/audio" / folder / "manifest.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(manifest), encoding="utf-8")
            with override_settings(BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
            self.assertEqual(Story.objects.get(number=1).audio, manifest)
            self.assertEqual(WeekScene.objects.get(week__level__code="A1", week__number=1).audio, manifest)
            self.assertEqual(TongueTwister.objects.get(number=1).audio, manifest)


class ModelDownloadRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.prepare = importlib.import_module("scripts.prepare_audio_models")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "source.bin"
        self.source.write_bytes(b"complete-model")
        self.destination = self.root / "models/model.onnx"
        self.digest = hashlib.sha256(b"complete-model").hexdigest()

    def ensure(self, size=14, digest=None):
        self.prepare.ensure_asset(self.destination, self.source.as_uri(), size, digest or self.digest)

    def test_partial_existing_file_is_replaced(self):
        self.destination.parent.mkdir()
        self.destination.write_bytes(b"partial")
        self.ensure()
        self.assertEqual(self.destination.read_bytes(), b"complete-model")

    def test_same_size_corruption_is_replaced(self):
        self.destination.parent.mkdir()
        self.destination.write_bytes(b"x" * 14)
        self.ensure()
        self.assertEqual(self.destination.read_bytes(), b"complete-model")

    def test_valid_file_is_reused_without_network(self):
        self.destination.parent.mkdir()
        self.destination.write_bytes(b"complete-model")
        self.source.unlink()
        self.ensure()
        self.assertEqual(self.destination.read_bytes(), b"complete-model")

    def test_short_download_never_replaces_existing_file(self):
        self.destination.parent.mkdir()
        self.destination.write_bytes(b"old")
        with self.assertRaises(ValueError):
            self.ensure(size=15)
        self.assertEqual(self.destination.read_bytes(), b"old")
        self.assertFalse(list(self.destination.parent.glob("*.part")))

    def test_wrong_checksum_is_not_installed(self):
        with self.assertRaises(ValueError):
            self.ensure(digest="0" * 64)
        self.assertFalse(self.destination.exists())
        self.assertFalse(list(self.destination.parent.glob("*.part")))

    def test_network_failure_preserves_existing_file(self):
        self.destination.parent.mkdir()
        self.destination.write_bytes(b"old")
        self.source.unlink()
        with self.assertRaises(OSError):
            self.ensure()
        self.assertEqual(self.destination.read_bytes(), b"old")
