"""Проверки экспериментального урока: маршруты, безопасность методов и изоляция."""
from django.test import TestCase
from django.urls import reverse


class CafeLabTests(TestCase):
    def test_lab_is_accessible_to_guest(self):
        url = reverse("core:cafe_lab")
        self.assertEqual(url, "/lab/cafe/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/cafe_lab.html")
        self.assertContains(response, "Мия не расслышала заказ")
        self.assertContains(response, 'data-cafe-lab')
        self.assertContains(response, 'data-built-sentence')
        self.assertContains(response, 'data-listen-check')
        self.assertContains(response, 'data-free-answer')
        self.assertContains(response, 'data-recorder')
        self.assertContains(response, 'data-transfer-answer')

    def test_lab_has_six_accessible_steps(self):
        response = self.client.get(reverse("core:cafe_lab"))
        for target in (
            'id="cafe-listen"', 'id="cafe-meaning"', 'id="cafe-change"',
            'id="cafe-check"', 'id="cafe-speak"', 'id="cafe-transfer"',
        ):
            self.assertContains(response, target)
        self.assertContains(response, 'aria-live="polite"')

    def test_lab_is_read_only(self):
        response = self.client.post(reverse("core:cafe_lab"), {"answer": "b"})
        self.assertEqual(response.status_code, 405)

    def test_main_course_has_link_to_lab(self):
        response = self.client.get(reverse("lessons:detail", kwargs={"slug": "a1-cafe-order"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("core:cafe_lab"))

    def test_unrelated_lesson_does_not_show_lab_link(self):
        response = self.client.get(reverse("lessons:detail", kwargs={"slug": "a1-nouns-first-words"}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="cafe-lab-invite"')

    def test_dialogue_lines_render_from_shared_source(self):
        from apps.core.cafe_lab import CAFE_DIALOGUE
        response = self.client.get(reverse("core:cafe_lab"))
        for index, line in enumerate(CAFE_DIALOGUE):
            self.assertContains(response, f'data-dialogue-line="{index}"')
            self.assertContains(response, line["text"])
        self.assertContains(response, 'id="cafe-audio-manifest"')

    def test_missing_audio_shows_null_and_browser_fallback(self):
        from apps.core.cafe_lab import safe_audio_manifest
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(safe_audio_manifest(Path(directory)))

    def test_reject_test_tone_and_invalid_files(self):
        import json
        import tempfile
        from pathlib import Path
        from apps.core.cafe_lab import safe_audio_manifest, CAFE_DIALOGUE

        with tempfile.TemporaryDirectory() as temporary:
            static = Path(temporary)
            folder = static / "audio" / "cafe-lab"
            folder.mkdir(parents=True)
            timeline = [{"line": i, "start": i + 0.1, "end": i + 0.9}
                        for i in range(len(CAFE_DIALOGUE))]
            tracks = {}
            for tempo in ("very_slow", "slow", "natural"):
                relative = f"audio/cafe-lab/voice_{tempo}.mp3"
                (static / relative).write_bytes(b"placeholder-audio" * 100)
                tracks[tempo] = {"file": relative, "seconds": 7.0, "timings": timeline}
            manifest = {"engine": "test", "model": "test-tone",
                        "voices": {"mia": "af_bella", "tom": "am_michael"}, **tracks}
            destination = folder / "manifest.json"
            destination.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertIsNone(safe_audio_manifest(static))
            manifest.update(engine="kokoro", model="kokoro-v1.0")
            destination.write_text(json.dumps(manifest), encoding="utf-8")
            valid = safe_audio_manifest(static)
            self.assertIsNotNone(valid)
            self.assertEqual(valid["tracks"]["slow"]["url"], "/static/audio/cafe-lab/voice_slow.mp3")
            manifest["slow"]["file"] = "audio/cafe-lab/../other.mp3"
            destination.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertIsNone(safe_audio_manifest(static))
            manifest["slow"]["file"] = "audio/cafe-lab/voice_slow.mp3"
            manifest["slow"]["timings"] = [{"line": 0, "start": 0, "end": 999}]
            destination.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertIsNone(safe_audio_manifest(static))
            manifest["slow"]["timings"] = timeline
            manifest["voices"]["mia"] = "unexpected-voice"
            destination.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertIsNone(safe_audio_manifest(static))

    def test_reject_symlinked_audio(self):
        import json
        import tempfile
        from pathlib import Path
        from apps.core.cafe_lab import safe_audio_manifest, CAFE_DIALOGUE

        with tempfile.TemporaryDirectory() as temporary:
            static = Path(temporary) / "static"
            folder = static / "audio" / "cafe-lab"
            folder.mkdir(parents=True)
            outside = Path(temporary) / "outside.mp3"
            outside.write_bytes(b"placeholder" * 300)
            tracks = {}
            for tempo in ("very_slow", "slow", "natural"):
                relative = f"audio/cafe-lab/voice_{tempo}.mp3"
                destination = static / relative
                try:
                    if tempo == "slow":
                        destination.symlink_to(outside)
                    else:
                        destination.write_bytes(b"placeholder" * 300)
                except (OSError, NotImplementedError):
                    self.skipTest("Symlink creation not supported")
                tracks[tempo] = {"file": relative, "seconds": 8,
                                 "timings": [{"line": i, "start": i + .1, "end": i + .9}
                                             for i in range(len(CAFE_DIALOGUE))]}
            (folder / "manifest.json").write_text(json.dumps({
                "engine": "kokoro", "model": "kokoro-v1.0",
                "voices": {"mia": "af_bella", "tom": "am_michael"}, **tracks
            }), encoding="utf-8")
            self.assertIsNone(safe_audio_manifest(static))
