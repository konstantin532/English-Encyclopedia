import hashlib
import importlib
import json
import tempfile
import wave

import yaml
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings, tag

from apps.core.management.commands.load_content import Command
from apps.curriculum.models import TongueTwister, WeekScene
from apps.stories.models import Story
from scripts.audio_readiness import script_fingerprint, validate_manifest


AUDIO_FOLDERS = ("stories/s01", "weeks/a1-w01", "twisters/t001")


def write_audio_bundle(root, folder):
    """Structurally valid fixture, not synthesized speech or human approval."""
    directory = root / "static/audio" / folder
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"engine": "kokoro", "model": "kokoro-v1.0", "verified": False}
    lines = 1
    if folder.startswith("stories/"):
        source = Path(__file__).resolve().parents[1] / "content/seed_stories"
        seed = next(source.glob(folder.split("/")[-1] + "_*.yaml"))
        script = yaml.safe_load(seed.read_text(encoding="utf-8"))["script"]
        manifest["script_sha256"] = script_fingerprint(script)
        lines = len(script)
    for tempo in ("very_slow", "slow", "natural"):
        name = f"speech_{tempo}.wav"
        with wave.open(str(directory / name), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(bytes(960 * lines))
        manifest[tempo] = {
            "file": f"audio/{folder}/{name}", "seconds": round(0.02 * lines, 3),
            "timings": [{"line": i, "start": round(0.02 * i + 0.001, 3),
                         "end": round(0.02 * i + 0.018, 3)} for i in range(lines)],
        }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@tag("slow")
class AudioManifestRecoveryTests(TestCase):
    def assert_published_audio(self, manifests):
        self.assertEqual(Story.objects.get(number=1).audio, manifests["stories/s01"])
        self.assertEqual(WeekScene.objects.get(week__level__code="A1", week__number=1).audio,
                         manifests["weeks/a1-w01"])
        self.assertEqual(TongueTwister.objects.get(number=1).audio, manifests["twisters/t001"])

    def test_test_tones_are_not_published_as_speech(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in AUDIO_FOLDERS:
                manifest = write_audio_bundle(root, folder)
                manifest.update(engine="test", model="test-tone")
                path = root / "static/audio" / folder / "manifest.json"
                path.write_text(json.dumps(manifest), encoding="utf-8")
            with override_settings(BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
            self.assert_published_audio(dict.fromkeys(AUDIO_FOLDERS, {}))

    def test_valid_kokoro_bundle_is_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifests = {folder: write_audio_bundle(root, folder) for folder in AUDIO_FOLDERS}
            with override_settings(BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
            self.assert_published_audio(manifests)

    def test_story_audio_with_a_different_script_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_audio_bundle(root, "stories/s01")
            manifest["script_sha256"] = "0" * 64
            path = root / "static/audio/stories/s01/manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with override_settings(BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
            self.assertEqual(Story.objects.get(number=1).audio, {})

    def test_legacy_story_audio_without_a_script_signature_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_audio_bundle(root, "stories/s01")
            manifest.pop("script_sha256", None)
            path = root / "static/audio/stories/s01/manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with override_settings(BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
            self.assertEqual(Story.objects.get(number=1).audio, {})

    def test_reload_clears_audio_when_a_track_disappears(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifests = {folder: write_audio_bundle(root, folder) for folder in AUDIO_FOLDERS}
            with override_settings(BASE_DIR=root):
                call_command("load_content", stdout=StringIO())
                self.assert_published_audio(manifests)
                for manifest in manifests.values():
                    (root / "static" / manifest["natural"]["file"]).unlink()
                call_command("load_content", stdout=StringIO())
            self.assert_published_audio(dict.fromkeys(AUDIO_FOLDERS, {}))


class AudioBundleIntegrityTests(SimpleTestCase):
    def test_loader_refuses_incomplete_or_unsafe_bundles(self):
        for defect in ("model", "tempo", "missing", "empty", "header", "traversal", "absolute"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest = write_audio_bundle(root, "stories/s01")
                track = root / "static" / manifest["natural"]["file"]
                if defect == "model":
                    del manifest["model"]
                elif defect == "tempo":
                    del manifest["natural"]
                elif defect == "missing":
                    track.unlink()
                elif defect in ("empty", "header"):
                    track.write_bytes(b"" if defect == "empty" else b"not a WAV file")
                elif defect == "traversal":
                    (root / "outside.wav").write_bytes(track.read_bytes())
                    manifest["natural"]["file"] = "../outside.wav"
                else:
                    manifest["natural"]["file"] = str(track.resolve())
                (track.parent / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                output = StringIO()
                with override_settings(BASE_DIR=root):
                    self.assertEqual(Command(stdout=output)._audio_manifest("stories", "s01"), {})
                self.assertIn("Пропущен аудиокомплект s01", output.getvalue())


    def test_matching_audio_ignores_translation_and_annotation_edits(self):
        import copy

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = write_audio_bundle(root, "stories/s01")
            seed = Path(__file__).resolve().parents[1] / "content/seed_stories/s01_not_my_box.yaml"
            script = copy.deepcopy(yaml.safe_load(seed.read_text(encoding="utf-8"))["script"])
            script[0]["ru"] = "Уточнённый русский перевод, который не озвучивается."
            script[0]["text"] = script[0]["text"].replace("[S2]", "[S1]")
            self.assertIsNone(validate_manifest(data, root / "static", script=script))

    def test_same_length_audio_rejects_changed_words_roles_and_delivery(self):
        import copy

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = write_audio_bundle(root, "stories/s01")
            seed = Path(__file__).resolve().parents[1] / "content/seed_stories/s01_not_my_box.yaml"
            original = yaml.safe_load(seed.read_text(encoding="utf-8"))["script"]
            for field, value in (("text", "A different line."), ("spoken", "Another line."),
                                 ("speaker", "tom"), ("emotion", "sad"), ("music", "none")):
                with self.subTest(field=field):
                    script = copy.deepcopy(original)
                    script[0][field] = value
                    self.assertIn("сценарий", validate_manifest(data, root / "static", script=script))
            self.assertIn("сценарий", validate_manifest(data, root / "static", script=list(reversed(original))))

    def test_audio_needs_timings_for_every_source_line(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = write_audio_bundle(root, "stories/s01")
            seed = Path(__file__).resolve().parents[1] / "content/seed_stories/s01_not_my_box.yaml"
            script = yaml.safe_load(seed.read_text(encoding="utf-8"))["script"]
            for tempo in ("very_slow", "slow", "natural"):
                data[tempo]["timings"].pop()
            self.assertIn("число реплик", validate_manifest(data, root / "static", script=script))


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
