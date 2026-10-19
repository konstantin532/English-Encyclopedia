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


class AudioInstallationIntegrityTests(SimpleTestCase):
    """A failed or incomplete audio release must never damage working tracks."""

    def make_archive(self, root, full=False):
        import hashlib
        from tests.test_audio_recovery import write_audio_bundle
        from scripts.audio_readiness import expected_manifests

        source = root / "source"
        folders = ([p.parent.relative_to(source / "static/audio").as_posix()
                    for p in expected_manifests(source)]
                   if full else ["stories/s01"])
        for folder in folders:
            write_audio_bundle(source, folder)
        zipped = root / "release.zip"
        with zipfile.ZipFile(zipped, "w") as archive:
            for file in sorted((source / "static/audio").rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(source).as_posix())
        return zipped.read_bytes(), hashlib.sha256(zipped.read_bytes()).hexdigest()

    def install_bytes(self, root, content, digest):
        import io
        from unittest import mock

        with mock.patch.object(installer.urllib.request, "urlopen",
                               return_value=io.BytesIO(content)):
            return installer.install(root=root, environ={
                "A1_AUDIO_ARCHIVE_URL": "https://audio.invalid/release.zip",
                "A1_AUDIO_ARCHIVE_SHA256": digest,
            })

    def test_rejects_invalid_last_archive_entry_without_partial_extract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            zipped = root / "mixed.zip"
            with zipfile.ZipFile(zipped, "w") as archive:
                archive.writestr("static/audio/stories/s01/valid.wav", b"RIFF" + bytes(4) + b"WAVE")
                archive.writestr("static/audio/../../bad.txt", b"bad")
            with self.assertRaisesMessage(ValueError, "Недопустимый путь"):
                installer.safe_unpack(zipped, root)
            self.assertFalse((root / "static/audio/stories/s01/valid.wav").exists())

    def test_rejects_case_insensitive_duplicate_archive_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            zipped = root / "duplicate.zip"
            with zipfile.ZipFile(zipped, "w") as archive:
                archive.writestr("static/audio/stories/s01/speech.wav", b"one")
                archive.writestr("static/audio/stories/s01/SPEECH.wav", b"two")
            with self.assertRaisesMessage(ValueError, "Повторный путь"):
                installer.safe_unpack(zipped, root)
            self.assertFalse((root / "static/audio/stories/s01/speech.wav").exists())

    def test_incomplete_valid_archive_cannot_replace_existing_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            live = root / "static/audio"
            live.mkdir(parents=True)
            (live / "working.mp3").write_bytes(b"existing-valid-content")
            content, digest = self.make_archive(root)
            with self.assertRaisesMessage(ValueError, "неполон"):
                self.install_bytes(root, content, digest)
            self.assertEqual((live / "working.mp3").read_bytes(), b"existing-valid-content")
            self.assertFalse((live / "stories/s01/manifest.json").exists())
            self.assertFalse(list(root.glob(".a1-audio-stage-*")))

    def test_full_release_replaces_old_audio_only_after_preflight(self):
        from scripts.audio_readiness import check_audio

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            live = root / "static/audio"
            live.mkdir(parents=True)
            (live / "old-test-tone.txt").write_text("stale", encoding="utf-8")
            content, digest = self.make_archive(root, full=True)
            self.assertTrue(self.install_bytes(root, content, digest))
            self.assertFalse((live / "old-test-tone.txt").exists())
            self.assertEqual(check_audio(root)["files_present"], 33)
            self.assertFalse(list(root.glob(".a1-audio-stage-*")))

    def test_failed_directory_swap_restores_old_audio(self):
        from unittest import mock

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            live = root / "static/audio"
            live.mkdir(parents=True)
            (live / "working.mp3").write_bytes(b"keep-old")
            content, digest = self.make_archive(root, full=True)
            replace = installer.os.replace
            calls = []

            def fail_on_second_move(source, destination):
                calls.append((source, destination))
                if len(calls) == 2:
                    raise OSError("injected disk failure")
                return replace(source, destination)

            import io
            with mock.patch.object(installer.os, "replace", side_effect=fail_on_second_move):
                with mock.patch.object(installer.urllib.request, "urlopen",
                                       return_value=io.BytesIO(content)):
                    with self.assertRaisesMessage(OSError, "injected disk failure"):
                        installer.install(root=root, environ={
                            "A1_AUDIO_ARCHIVE_URL": "https://audio.invalid/release.zip",
                            "A1_AUDIO_ARCHIVE_SHA256": digest,
                        })
            self.assertEqual(len(calls), 3, "move old, failed move new, rollback old")
            self.assertEqual((live / "working.mp3").read_bytes(), b"keep-old")
            self.assertFalse((live / "stories/s01/manifest.json").exists())
            self.assertFalse(list(root.glob(".a1-audio-stage-*")))
