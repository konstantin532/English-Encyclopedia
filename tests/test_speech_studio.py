"""Речевая мастерская встроена в основные уроки, стихи и недели."""
from django.test import TestCase
from django.urls import reverse

from apps.lessons.models import Lesson
from apps.poems.models import Poem
from tests.runner import ensure_content


class SpeechStudioIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_six_oral_situations_in_each_a1_lesson(self):
        for n in range(1, 27):
            with self.subTest(lesson=n):
                lesson = Lesson.objects.get(level__code="A1", order=n)
                response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-speech-kind="lesson"')
                self.assertContains(response, "Речевая мастерская")
                self.assertContains(response, 'data-speech-task-source', count=6)
                self.assertContains(response, 'data-speech-entry', count=6)
                self.assertContains(response, "speech-studio.js")

    def test_week_twisters_have_oral_trainer_and_no_claim_to_grade_voice(self):
        for n in (1, 5, 10, 14):
            with self.subTest(week=n):
                response = self.client.get(reverse("curriculum:week", args=["a1", n]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-speech-kind="twister"')
                self.assertContains(response, 'data-speech-entry')
                self.assertContains(response, "speech-studio.js")
                self.assertContains(response, "на сервер не отправляется")
                self.assertContains(response, "не выполняется")

    def test_published_poems_have_line_by_line_trainer(self):
        poems = Poem.objects.filter(level__code="A1", is_published=True).order_by("number")
        self.assertGreaterEqual(poems.count(), 1)
        for poem in poems:
            with self.subTest(poem=poem.number):
                response = self.client.get(reverse("stories:poem", args=[poem.number]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-speech-kind="poem"')
                self.assertContains(response, "speech-studio.js")
                line_count = len([line for line in poem.body.splitlines() if line.strip()])
                self.assertContains(response, 'data-speech-entry', count=line_count)
                self.assertContains(response, 'data-speech-accent', count=line_count)

    def test_tongue_twister_1_keeps_short_phonetic_target(self):
        from pathlib import Path
        import yaml
        from apps.taxonomy.markup import strip_markup

        root = Path(__file__).resolve().parents[1]
        week1 = yaml.safe_load((root / "content/seed_weeks/a1_w01.yaml").read_text(encoding="utf-8"))
        twister = week1["twister"]
        self.assertLessEqual(len(strip_markup(twister["text"]).split()), 8)
        self.assertIn("this", strip_markup(twister["text"]).lower())
        self.assertIn("house", strip_markup(twister["text"]).lower())
        self.assertGreaterEqual(len(twister["warmup"]), 4)

    def test_amE_twister_guidance_does_not_treat_t_and_l_as_absolutes(self):
        from pathlib import Path
        import yaml

        root = Path(__file__).resolve().parents[1] / "content" / "seed_weeks"
        week9 = yaml.safe_load((root / "a1_w09.yaml").read_text(encoding="utf-8"))
        week13 = yaml.safe_load((root / "a1_w13.yaml").read_text(encoding="utf-8"))
        # Week 9 trains the American glides /oʊ/ and /aɪ/ (Open at nine, close at five).
        self.assertIn("«оу»", week9["twister"]["tip_ru"])
        self.assertIn("/oʊ/", week9["twister"]["goal_ru"])
        self.assertIn("Безударное can", week13["twister"]["tip_ru"])
        self.assertNotIn("почти не произносят", week13["twister"]["goal_ru"])
