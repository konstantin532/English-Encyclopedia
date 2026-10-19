"""Exercise the actual workflow archive and Render installer entrypoint offline."""
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml
from django.test import SimpleTestCase

from deploy.install_audio_archive import safe_unpack
from scripts.audio_readiness import check_audio, expected_manifests
from tests.test_audio_recovery import write_audio_bundle

ROOT = Path(__file__).resolve().parents[1]


class AudioDistributionTests(SimpleTestCase):
    def test_workflow_archive_can_be_unpacked_by_render(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/build-a1-audio.yml").read_text(encoding="utf-8"))
        step = next(step for step in workflow["jobs"]["kokoro-a1"]["steps"]
                    if step.get("name") == "Package generated audio and calculate immutable SHA-256")
        command = shlex.split(step["run"].splitlines()[0])
        command[0] = sys.executable
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_audio_bundle(root, "stories/s01")
            result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                    env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1"), timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with zipfile.ZipFile(root / "a1-generated-audio.zip") as archive:
                self.assertTrue(all(name.startswith("static/audio/") for name in archive.namelist()))
            self.assertEqual(safe_unpack(root / "a1-generated-audio.zip", root / "installed"), 4)

    def test_render_build_installs_complete_audio_without_project_on_pythonpath(self):
        build = (ROOT / "deploy/render-build.sh").read_text(encoding="utf-8")
        command = shlex.split(next(line for line in build.splitlines() if "install_audio_archive" in line))
        command[0] = sys.executable
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout, source, hooks = root / "checkout", root / "source", root / "hooks"
            for relative in ("deploy/install_audio_archive.py", "scripts/audio_readiness.py"):
                target = checkout / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            for path in expected_manifests(source):
                write_audio_bundle(source, path.parent.relative_to(source / "static/audio").as_posix())
            zipped = root / "audio.zip"
            with zipfile.ZipFile(zipped, "w") as archive:
                for path in sorted((source / "static/audio").rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(source).as_posix())
            hooks.mkdir()
            # Substitute only the HTTPS transport; execute the real installer,
            # archive extraction and 33-bundle validation in a fresh interpreter.
            (hooks / "sitecustomize.py").write_text(
                "import io, os, pathlib, urllib.request\n"
                "urllib.request.urlopen = lambda *a, **k: io.BytesIO("
                "pathlib.Path(os.environ['MOCK_AUDIO_ZIP']).read_bytes())\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=str(hooks), PYTHONUTF8="1", MOCK_AUDIO_ZIP=str(zipped),
                       A1_AUDIO_ARCHIVE_URL="https://audio.invalid/a1.zip",
                       A1_AUDIO_ARCHIVE_SHA256=hashlib.sha256(zipped.read_bytes()).hexdigest())
            result = subprocess.run(command, cwd=checkout, env=env, capture_output=True, text=True,
                                    encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("33 real Kokoro bundles", result.stdout)
            self.assertEqual(check_audio(checkout)["files_present"], 33)
