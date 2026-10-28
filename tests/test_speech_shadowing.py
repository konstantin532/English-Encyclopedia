"""Audio-guided training exposes only available files and does not claim that TTS was reviewed."""
from apps.poems.models import Poem
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from apps.curriculum.models import TongueTwister, WeekScene
from tests.runner import ensure_content


class SpeechAudioScaffoldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def full_trainer(self, twister):
        return render_to_string("components/twister_trainer.html", {
            "twister": twister, "user": AnonymousUser(), "week_mode": False,
        })

    def test_week_without_recording_has_clear_fallback_and_does_not_fabricate_audio(self):
        twister = TongueTwister.objects.get(number=1)
        twister.audio = {}
        twister.save(update_fields=["audio"])
        page = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Озвучка скороговорки ещё не записана. Ориентируйтесь на транскрипцию и подсказку ниже.")
        self.assertNotContains(page, "data-twister-player")
        self.assertNotContains(page, "data-twister-src=")
        self.assertNotContains(page, "data-speech-reference-player")
        self.assertContains(page, "data-speech-recorder", count=1)
        self.assertContains(page, "speech-studio.js")
        full = self.full_trainer(twister)
        self.assertIn("Озвучка для этой скороговорки ещё не подготовлена", full)
        self.assertNotIn("data-speech-reference-player", full)

    def test_available_but_unverified_recordings_display_provenance(self):
        twister = TongueTwister.objects.get(number=1)
        twister.audio = {
            "engine": "kokoro", "verified": False,
            "very_slow": {"file": "audio/twisters/t001/voice_very_slow.mp3"},
            "slow": {"file": "audio/twisters/t001/voice_slow.mp3"},
            "natural": {"file": "audio/twisters/t001/voice_natural.mp3"},
        }
        twister.save(update_fields=["audio"])
        WeekScene.objects.filter(week=twister.week).update(audio=twister.audio)
        page = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertContains(page, "data-twister-player", count=1)
        self.assertContains(page, 'src="/static/audio/twisters/t001/voice_very_slow.mp3"')
        self.assertContains(page, "data-twister-src=", count=3)
        for speed in ("very_slow", "slow", "natural"):
            self.assertContains(page, f'data-twister-src="/static/audio/twisters/t001/voice_{speed}.mp3"')
        self.assertContains(page, "Голоса созданы нейросетью.", count=1)
        self.assertNotContains(page, "data-speech-reference-player")
        full = self.full_trainer(twister)
        self.assertIn("data-speech-reference-player", full)
        self.assertIn('data-reference-verified="false"', full)
        self.assertIn("Запись синтезирована и ещё не проверена преподавателем.", full)
        self.assertIn('data-reference-natural="/static/audio/twisters/t001/voice_natural.mp3"', full)
        self.assertIn('data-reference-slow="/static/audio/twisters/t001/voice_slow.mp3"', full)

    def test_poetry_provides_author_annotated_stress_prompts(self):
        for number in range(1, 8):
            with self.subTest(number=number):
                page = self.client.get(reverse("stories:poem", args=[number]))
                self.assertEqual(page.status_code, 200)
                self.assertContains(page, "speech-stress.js")
                # One annotated stress prompt per poem line, whatever the poem length.
                lines = len([l for l in Poem.objects.get(number=number).body.splitlines() if l.strip()])
                self.assertGreaterEqual(lines, 12)
                self.assertContains(page, "data-stress-entry", count=lines)
                self.assertContains(page, "data-stress-plain=", count=lines)
                self.assertContains(page, "data-stress-model=", count=lines)
                self.assertContains(page, "текстовая тренировка внимания к ритму")

    def test_reviewed_reference_is_marked_verified_not_automatically_scored(self):
        twister = TongueTwister.objects.get(number=1)
        twister.audio = {
            "engine": "kokoro", "verified": True,
            "very_slow": {"file": "audio/twisters/t001/voice_very_slow.mp3"},
            "slow": {"file": "audio/twisters/t001/voice_slow.mp3"},
            "natural": {"file": "audio/twisters/t001/voice_natural.mp3"},
        }
        twister.save(update_fields=["audio"])
        page = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertContains(page, "data-twister-player", count=1)
        self.assertContains(page, "data-speech-recorder", count=1)
        self.assertContains(page, "Запись не отправляется на сервер.", count=1)
        self.assertNotContains(page, "data-speech-grades")
        self.assertNotContains(page, "data-speech-reference-player")
        self.assertNotContains(page, "Запись синтезирована и ещё не проверена преподавателем")
        full = self.full_trainer(twister)
        self.assertIn('data-reference-verified="true"', full)
        self.assertNotIn("Запись синтезирована и ещё не проверена преподавателем", full)
        self.assertIn("<strong>насколько самостоятельно получилось</strong>", full)
        self.assertIn("Запись не отправляется на сервер.", full)
