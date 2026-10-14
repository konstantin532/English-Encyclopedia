from django.core.management import call_command
from django.test import TestCase

from apps.curriculum.models import TongueTwister, Week, WeekScene
from apps.publishing.audit import run_audit
from apps.stories.models import Story

VALID = [
    {"speaker": "tom", "emotion": "happy", "text": "[J3]Good[/] [S7]morning[/]! [T8]I[/] [D1]am[/] [S1]Tom[/]."},
    {"speaker": "anna", "text": "[J3]Good[/] [S7]morning[/], [S1]Tom[/]! [T8]I[/] [D1]am[/] [S1]Anna[/]."},
    {"speaker": "tom", "emotion": "surprised", "text": "[D1]Is[/] [T8]it[/] [T1]a[/] [J2]new[/] [S2]house[/]?"},
    {"speaker": "anna", "text": "[O4]Yes[/], [T8]it[/] [D1]is[/]. [T8]It[/] [D1]is[/] [J1]big[/]."},
    {"speaker": "tom", "text": "[T8]It[/] [D1]is[/] [J3]nice[/], [S1]Anna[/]!"},
    {"speaker": "anna", "text": "[T2]This[/] [D1]is[/] [T3]my[/] [S2]book[/]. [T8]I[/] [D1]am[/] [J4]busy[/], [S1]Tom[/]."},
    {"speaker": "tom", "emotion": "tired", "text": "[T8]I[/] [D1]am[/] [J4]busy[/] [P1]at[/] [S2]home[/]."},
    {"speaker": "anna", "text": "[O4]No[/], [T8]it[/] [D1]is[/] [X1]not[/] [T3]my[/] [S2]phone[/]."},
]


class WeekAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def setUp(self):
        self.week = Week.objects.get(level__code="A1", number=1)
        self.scene = WeekScene.objects.create(week=self.week, can_do_ru="Я смогу представиться.",
                                              mission_ru="Скажите имя вслух.", script=[dict(l) for l in VALID])

    def errors(self, needle=""):
        return [e for e in run_audit().errors if needle in e]

    def warnings(self, needle=""):
        return [w for w in run_audit().warnings if needle in w]

    def test_valid_scene_passes(self):
        self.assertEqual(self.errors("Неделя A1-1"), [])
        self.assertEqual(self.errors(), [])

    def test_missing_parts(self):
        self.scene.can_do_ru = ""
        self.scene.mission_ru = ""
        self.scene.save()
        self.assertTrue(self.errors("Неделя A1-1: нет цели"))
        self.assertTrue(self.errors("Неделя A1-1: нет задания в жизнь"))

    def test_unknown_word_in_dialogue(self):
        self.scene.script[0]["text"] += " [S6]elephant[/]"
        self.scene.save()
        self.assertTrue(self.errors("незнакомые слова в диалоге: elephant"))

    def test_grammar_marker_missing(self):
        self.week.grammar_markers = ["J1"]
        self.week.save()
        self.assertTrue(self.errors("маркер J1 встречается 1 раз, нужно не меньше 2"))

    def test_category_marker_counts_any_class(self):
        self.week.grammar_markers = ["J"]
        self.week.save()
        self.assertEqual(self.errors("маркер J"), [])

    def test_marker_not_in_registry(self):
        self.week.grammar_markers = ["Z9"]
        self.week.save()
        self.assertTrue(self.errors("маркера Z9 нет в реестре"))

    def test_lesson_without_dialogue_example(self):
        self.scene.script = [l for l in self.scene.script if "[T2]This[/]" not in l["text"] and "morning" not in l["text"]]
        self.scene.save()
        self.assertTrue(self.errors("в уроке a1-nouns-first-words нет примера из диалога недели"))

    def test_bad_emotion_and_speaker(self):
        self.scene.script[0]["emotion"] = "furious"
        self.scene.script[1]["speaker"] = "nobody"
        self.scene.save()
        self.assertTrue(self.errors("реплика 1: неизвестная эмоция furious"))
        self.assertTrue(self.errors("реплика 2: роли nobody нет в voices.yaml"))

    def test_dialogue_length_a1(self):
        self.scene.script = self.scene.script[:5]
        self.scene.save()
        self.assertTrue(self.errors("реплик 5, норма 6–10"))

    def test_story_first_line_needs_music(self):
        story = Story.objects.get(number=1)
        self.assertEqual(self.errors("История 1"), [])
        story.script[0].pop("music", None)
        story.save()
        self.assertTrue(self.errors("История 1: у первой реплики нет music"))
        story.script[0]["music"] = "disco"
        story.save()
        self.assertTrue(self.errors("История 1, реплика 1: неизвестное настроение disco"))

    def test_spheres_warning_until_plan_complete(self):
        self.assertEqual(self.warnings("в плане нет сфер"), [])
        Week.objects.filter(level__code="A1", number=14).update(sphere="")
        self.assertTrue(self.warnings("A1: в плане нет сфер: travel"))

    def test_chunks_warning(self):
        self.assertTrue(self.warnings("Неделя A1-1: готовых фраз 0, нужно 5–8"))

    def test_twister_rules(self):
        TongueTwister.objects.create(number=2, week=self.week, series="fast", source="folk",
                                     text="[T2]This[/] [D1]is[/] [T3]my[/] [S2]book[/].")
        self.assertTrue(self.errors("Скороговорка 2: номер должен быть 1"))
        self.assertTrue(self.errors("Скороговорка 2: серия fast, для уровня A1 нужна sounds"))
        self.assertTrue(self.errors("Скороговорка 2: у народной скороговорки нет source_note"))

    def test_sounds_twister_words(self):
        TongueTwister.objects.create(number=1, week=self.week, series="sounds", source="original",
                                     text="[T2]This[/] [S6]elephant[/].")
        self.assertTrue(self.errors("Скороговорка 1: незнакомые слова: elephant"))
        self.assertTrue(self.errors("Скороговорка 1: слов 2, для серии sounds нужно 3–8"))

    def test_missing_twister_is_warning(self):
        self.assertTrue(self.warnings("Неделя A1-1: нет скороговорки недели"))
