import importlib.util
from pathlib import Path

import yaml
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.curriculum.models import Week, WeekScene
from apps.lessons.models import Lesson
from apps.publishing.audit import run_audit
from apps.stories.models import Story
from tests.test_audit_weeks import VALID
from tests.runner import ensure_content

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("gen_spoken", ROOT / "scripts" / "generate_story_audio.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)
VOICES = yaml.safe_load((ROOT / "content/manifests/voices.yaml").read_text(encoding="utf-8"))

SPOKEN = "“[O4]No[/], [T8]it[/][D1]'s[/] [X1]not[/] [T3]my[/] [S2]box[/].”"


class SpokenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.week = Week.objects.get(level__code="A1", number=1)
        WeekScene.objects.filter(week=self.week).delete()
        self.scene = WeekScene.objects.create(week=self.week, can_do_ru="Я смогу…", mission_ru="…",
                                              script=[dict(l) for l in VALID])

    def errors(self, needle):
        return [e for e in run_audit().errors if needle in e]

    def test_spoken_variant_on_story_page(self):
        story = Story.objects.get(number=1)
        story.script[3]["spoken"] = SPOKEN
        story.save()
        html = self.client.get(reverse("stories:detail", args=[1])).content.decode()
        self.assertIn('name="speech" value="spoken"', html)
        self.assertIn('class="line-spoken"', html)
        self.assertIn("полностью:", html)

    def test_no_switch_without_spoken(self):
        story = Story.objects.get(number=1)
        for line in story.script:
            line.pop("spoken", None)
        story.save()
        html = self.client.get(reverse("stories:detail", args=[1])).content.decode()
        self.assertNotIn('name="speech"', html)

    def test_natural_tempo_reads_spoken(self):
        script = [{"speaker": "anna", "text": "No, it is not my box, it is not my box at all.", "spoken": "No."}]
        _, slow = gen.build_track(gen.TestEngine(), script, VOICES["roles"], 1.0, 1.0, VOICES["emotions"])
        _, natural = gen.build_track(gen.TestEngine(), script, VOICES["roles"], 1.0, 1.0, VOICES["emotions"], spoken=True)
        self.assertLess(natural[0]["end"] - natural[0]["start"], (slow[0]["end"] - slow[0]["start"]) / 2)

    def test_audit_spoken_same_as_text(self):
        self.scene.script[7]["spoken"] = self.scene.script[7]["text"]
        self.scene.save()
        self.assertTrue(self.errors("Неделя A1-1, реплика 8: spoken совпадает с text"))

    def test_audit_blend_forbidden_on_a1(self):
        self.scene.script[6]["spoken"] = "[T8]I[/][D1]'m[/] [D1]gonna[/] [S2]home[/]."
        self.scene.save()
        self.assertTrue(self.errors("Неделя A1-1, реплика 7: слияние gonna рано для уровня A1"))

    def test_audit_unknown_word_in_spoken(self):
        self.scene.script[7]["spoken"] = "[O4]No[/], [T8]it[/][D1]'s[/] [S6]elephant[/]."
        self.scene.save()
        self.assertTrue(self.errors("Неделя A1-1, реплика 8: незнакомые слова в spoken: elephant"))

    def test_contraction_without_spoken_warns(self):
        warnings = [w for w in run_audit().warnings if "Неделя A1-1, реплика 4: можно сократить" in w]
        self.assertTrue(warnings)
        self.assertIn("it is", warnings[0])
        self.scene.script[3]["spoken"] = "[O4]Yes[/], [T8]it[/] [D1]is[/]. [T8]It[/][D1]'s[/] [J1]big[/]."
        self.scene.save()
        self.assertFalse([w for w in run_audit().warnings if "Неделя A1-1, реплика 4: можно сократить" in w])

    def test_lesson_contractions_block(self):
        lesson = Lesson.objects.get(slug="a1-verb-be")
        lesson.contractions = [{"full": "I am", "short": "I'm", "ipa": "/aɪm/", "note_ru": "am теряет гласную"}]
        lesson.save()
        r = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
        self.assertContains(r, 'id="contractions"')
        self.assertContains(r, "I&#x27;m")
        self.assertContains(r, 'class="ru-tr"')
        lesson.contractions = [{"full": "I'm", "short": "Im", "ipa": "/aɪm/", "note_ru": ""}]
        lesson.save()
        self.assertTrue(self.errors("a1-verb-be: «Как сокращают», пара 1: в short нет апострофа"))
        self.assertTrue(self.errors("a1-verb-be: «Как сокращают», пара 1: в full не должно быть апострофа"))

    def test_short_affirmative_answer_does_not_request_contraction(self):
        self.scene.script[3] = {"speaker": "anna", "text": "[O4]Yes[/], [T8]I[/] [D1]am[/]."}
        self.scene.save()
        self.assertFalse([w for w in run_audit().warnings if "Неделя A1-1, реплика 4: можно сократить" in w])
        self.scene.script[3]["text"] += " [T8]I[/] [D1]am[/] [S1]Anna[/]."
        self.scene.save()
        self.assertTrue([w for w in run_audit().warnings if "Неделя A1-1, реплика 4: можно сократить i am" in w])
