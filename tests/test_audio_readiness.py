"""Audio file inventory is not an acoustic or CEFR validation."""
import importlib.util
import json
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase

MODULE = Path(__file__).resolve().parents[1] / "scripts/audio_readiness.py"
spec = importlib.util.spec_from_file_location("audio_readiness", MODULE)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class AudioReadinessTests(SimpleTestCase):
    def test_empty_directory_reports_all_missing(self):
        with TemporaryDirectory() as tmp:
            result = checker.check_audio(Path(tmp))
            self.assertEqual(result["expected"], 33)
            self.assertEqual(len(result["missing"]), 33)
            self.assertEqual(result["files_present"], 0)

    def test_fake_tone_not_counted_as_ready(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp) / "static/audio/stories/s01"
            folder.mkdir(parents=True)
            (folder / "manifest.json").write_text(
                json.dumps({"engine": "test", "model": "test-tone"}), encoding="utf-8")
            result = checker.check_audio(Path(tmp))
            self.assertEqual(result["files_present"], 0)
            self.assertEqual(len(result["invalid"]), 1)

    def test_kokoro_files_without_human_review_are_marked(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp) / "static/audio/stories/s01"
            folder.mkdir(parents=True)
            tempos = {}
            for tempo in checker.TEMPOS:
                name = f"voice_{tempo}.wav"
                with wave.open(str(folder / name), "wb") as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(24000)
                    audio.writeframes(bytes(960))
                tempos[tempo] = {"file": f"audio/stories/s01/{name}"}
            (folder / "manifest.json").write_text(
                json.dumps({"engine": "kokoro", "model": "kokoro-v1.0",
                            "verified": False, **tempos}), encoding="utf-8")
            result = checker.check_audio(Path(tmp))
            self.assertEqual(result["files_present"], 1)
            self.assertEqual(len(result["unreviewed"]), 1)

    def test_invalid_wav_is_detected_even_when_file_exists(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp) / "static/audio/stories/s01"
            folder.mkdir(parents=True)
            tempos = {}
            for tempo in checker.TEMPOS:
                name = f"voice_{tempo}.wav"
                (folder / name).write_bytes(b"not actually an audio track")
                tempos[tempo] = {"file": f"audio/stories/s01/{name}"}
            (folder / "manifest.json").write_text(
                json.dumps({"engine": "kokoro", "model": "kokoro-v1.0", **tempos}),
                encoding="utf-8")
            result = checker.check_audio(Path(tmp))
            self.assertEqual(result["files_present"], 0)
            self.assertTrue(any("WAV/MP3" in issue for issue in result["invalid"]))

    def test_manifest_validator_refuses_missing_and_unsafe_tracks(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIn("движок", checker.validate_manifest({"engine":"test"}, root))
            self.assertIn("дорожка", checker.validate_manifest({"engine":"kokoro","model":"kokoro-v1.0"}, root))
            self.assertIn("вне static", checker.validate_manifest({
                "engine":"kokoro", "model":"kokoro-v1.0",
                "very_slow":{"file":"../not-audio.wav"},
                "slow":{"file":"audio/ok.mp3"},
                "natural":{"file":"audio/ok.mp3"},
            }, root))

    def test_loader_refuses_invalid_audio_manifest(self):
        from unittest import mock
        from apps.core.management.commands.load_content import Command
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "static/audio/stories/s01"
            folder.mkdir(parents=True)
            (folder / "manifest.json").write_text(json.dumps({"engine":"kokoro", "model":"kokoro-v1.0",
                "slow":{"file":"audio/stories/s01/missing.wav"}}), encoding="utf-8")
            with mock.patch("apps.core.management.commands.load_content.settings.BASE_DIR", root):
                self.assertEqual(Command()._audio_manifest("stories", "s01"), {})
