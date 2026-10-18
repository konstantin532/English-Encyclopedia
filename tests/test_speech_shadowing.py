"""Audio-guided training exposes only available files and does not claim that TTS was reviewed."""
from django.test import TestCase
from django.urls import reverse

from apps.curriculum.models import TongueTwister
from tests.runner import ensure_content


class SpeechAudioScaffoldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_week_without_recording_has_clear_fallback_and_does_not_fabricate_audio(self):
        twister = TongueTwister.objects.get(number=1)
        twister.audio = {}
        twister.save(update_fields=["audio"])
        page = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Озвучка для этой скороговорки ещё не подготовлена")
        self.assertNotContains(page, "data-speech-reference-player")
        self.assertContains(page, "speech-shadowing.js")

    def test_available_but_unverified_recordings_display_provenance(self):
        twister = TongueTwister.objects.get(number=1)
        twister.audio = {
            "engine": "kokoro", "verified": False,
            "slow": {"file": "audio/twisters/t001/voice_slow.mp3"},
            "natural": {"file": "audio/twisters/t001/voice_natural.mp3"},
        }
        twister.save(update_fields=["audio"])
        page = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertContains(page, "data-speech-reference-player")
        self.assertContains(page, 'data-reference-verified="false"')
        self.assertContains(page, "не проверена преподавателем")
        self.assertContains(page, "/static/audio/twisters/t001/voice_natural.mp3")
        self.assertContains(page, "/static/audio/twisters/t001/voice_slow.mp3")

    def test_reviewed_reference_is_marked_verified_not_automatically_scored(self):
        twister = TongueTwister.objects.get(number=1)
        twister.audio = {
            "engine": "kokoro", "verified": True,
            "slow": {"file": "audio/twisters/t001/voice_slow.mp3"},
            "natural": {"file": "audio/twisters/t001/voice_natural.mp3"},
        }
        twister.save(update_fields=["audio"])
        page = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertContains(page, 'data-reference-verified="true"')
        self.assertNotContains(page, "Запись синтезирована и ещё не проверена преподавателем")
        self.assertContains(page, "Это не проверка произношения")
