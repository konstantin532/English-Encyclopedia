from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.stories.models import Story


def manifest(with_music: bool) -> dict:
    out = {"verified": False, "ambience": None, "ambience_gain_db": -30}
    for tempo in ("very_slow", "slow", "natural"):
        entry = {"file": f"audio/stories/s01/voice_{tempo}.mp3", "timings": [{"line": 0, "start": 0.4, "end": 1.0}],
                 "seconds": 2.0}
        if with_music:
            entry["music"] = f"audio/stories/s01/music_{tempo}.mp3"
            entry["music_gain_db"] = -30 if tempo == "very_slow" else -26
        out[tempo] = entry
    return out


class StoryPlayerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def page(self):
        return self.client.get(reverse("stories:detail", args=[1])).content.decode()

    def test_story_page_has_music_and_emotions(self):
        story = Story.objects.get(number=1)
        story.audio = manifest(True)
        story.script[2]["emotion"] = "surprised"
        story.save()
        html = self.page()
        self.assertIn('data-music-slow="/static/audio/stories/s01/music_slow.mp3"', html)
        self.assertIn('data-music-db-very_slow="-30"', html)
        self.assertIn("data-music-vol", html)
        self.assertIn('<span class="emotion"> · удивлённо</span>', html)

    def test_story_page_without_music_has_no_slider(self):
        story = Story.objects.get(number=1)
        story.audio = manifest(False)
        story.save()
        html = self.page()
        self.assertNotIn("data-music-vol", html)
        self.assertNotIn("data-music-slow", html)
        self.assertIn("data-story-player", html)

    def test_listen_modes_and_translation(self):
        story = Story.objects.get(number=1)
        story.script[0]["ru"] = "Меня зовут Анна."
        story.save()
        html = self.page()
        for value in ("hidden", "text", "marked"):
            self.assertIn(f'name="listen" value="{value}"', html)
        self.assertIn('<span class="line-ru" lang="ru">Меня зовут Анна.</span>', html)
