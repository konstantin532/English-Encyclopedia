"""Archive safety tests: supply content, never certify a synthetic voice."""
import importlib.util
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_audio", ROOT / "deploy/install_audio_archive.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class AudioArchiveTests(SimpleTestCase):
    def test_missing_configuration_is_safe_text_only(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(installer.install(root=Path(folder), environ={}))

    def test_requires_https_and_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesMessage(ValueError, "оба параметра"):
                installer.install(root=Path(folder), environ={"A1_AUDIO_ARCHIVE_URL":"https://example.com/file.zip"})
            with self.assertRaisesMessage(ValueError, "HTTPS"):
                installer.install(root=Path(folder), environ={"A1_AUDIO_ARCHIVE_URL":"http://example.com/file.zip",
                                                              "A1_AUDIO_ARCHIVE_SHA256":"0"*64})

    def test_does_not_extract_parent_paths_or_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "audio.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("static/audio/../../bad.txt", "bad")
            with self.assertRaisesMessage(ValueError, "Недопустимый путь"):
                installer.safe_unpack(archive, root)
            self.assertFalse((root / "bad.txt").exists())

    def test_extracts_only_static_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "audio.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("static/audio/stories/s01/test.wav", b"RIFF"+bytes(4)+b"WAVE")
            self.assertEqual(installer.safe_unpack(archive, root), 1)
            self.assertTrue((root / "static/audio/stories/s01/test.wav").exists())
