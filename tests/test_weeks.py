from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.curriculum.models import TongueTwister, Week, WeekScene
from apps.learning.models import WeekGoal


class WeekModelTests(TestCase):
    def test_scene_twister_goal(self):
        week = Week.objects.get(level__code="A1", number=1)
        scene = WeekScene.objects.create(week=week, can_do_ru="Я смогу…", mission_ru="…", script=[])
        TongueTwister.objects.create(number=1, week=week, series="sounds", text="[T2]This[/]", source="original")
        user = User.objects.create_user("u@example.com", "s3cret-pass-123")
        WeekGoal.objects.create(user=user, week=week, status="done")
        week.refresh_from_db()
        self.assertEqual(week.scene, scene)
        self.assertEqual(week.twister.number, 1)
        self.assertEqual(week.global_number, 1)
        self.assertEqual(Week.objects.get(level__code="A1+", number=1).global_number, 15)
        with self.assertRaises(IntegrityError):
            WeekGoal.objects.create(user=user, week=week, status="not_yet")


import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.stories.script import build_lines

SAMPLE_WEEK = """level: A1
week: 1
can_do_ru: "Я смогу представиться."
mission_ru: "Скажите своё имя вслух три раза."
ambience: morning_home
chunks: []
script:
  - speaker: tom
    text: "[S7]Good morning[/]! [T8]I[/] [D1]am[/] [S1]Tom[/]."
    emotion: happy
    ru: "Доброе утро! Я Том."
  - speaker: anna
    text: "[T8]I[/] [D1]am[/] [S1]Anna[/]."
  - speaker: tom
    text: "[D1]Is[/] [T2]this[/] [T3]your[/] [S2]house[/]?"
  - speaker: anna
    text: "[O4]Yes[/]. [T8]It[/] [D1]is[/] [J2]new[/]."
  - speaker: tom
    text: "[T8]It[/] [D1]is[/] [J3]nice[/]!"
    emotion: excited
  - speaker: anna
    text: "[O2]Thank you[/], [S1]Tom[/]."
twister:
  number: 1
  series: sounds
  text: "[T2]This[/] [D1]is[/] [T2]this[/]."
  ipa: "/ðɪs ɪz ðɪs/"
  focus_sounds: [dh]
  source: original
"""


class WeekLoaderTests(TestCase):
    @contextmanager
    def content_with_week(self, text):
        tmp = Path(tempfile.mkdtemp())
        try:
            root = tmp / "content"
            shutil.copytree(settings.CONTENT_DIR, root)
            (root / "seed_weeks").mkdir(exist_ok=True)
            for path in (root / "seed_weeks").glob("*.yaml"):
                path.unlink()
            (root / "seed_weeks" / "a1_w01.yaml").write_text(text, encoding="utf-8")
            with override_settings(CONTENT_DIR=root, BASE_DIR=tmp):
                yield root
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_plan_fills_weeks(self):
        call_command("load_content", verbosity=0)
        w = Week.objects.get(level__code="A1", number=8)
        self.assertEqual((w.sphere, w.grammar_markers), ("city", ["P1", "A6"]))
        self.assertEqual(w.situation_ru, "Как пройти?")

    def test_week_file_loads_idempotently(self):
        with self.content_with_week(SAMPLE_WEEK):
            call_command("load_content", verbosity=0)
            call_command("load_content", verbosity=0)
        scene = WeekScene.objects.get(week__level__code="A1", week__number=1)
        self.assertEqual(len(scene.script), 6)
        self.assertEqual(scene.can_do_ru, "Я смогу представиться.")
        self.assertEqual(TongueTwister.objects.get(number=1).week, scene.week)
        self.assertEqual(WeekScene.objects.count(), 1)
        self.assertEqual(scene.audio, {})

    def test_unknown_speaker_rejected(self):
        with self.content_with_week(SAMPLE_WEEK.replace("speaker: tom", "speaker: nobody", 1)):
            with self.assertRaisesMessage(CommandError, "nobody"):
                call_command("load_content", verbosity=0)

    def test_unknown_chunk_rejected(self):
        with self.content_with_week(SAMPLE_WEEK.replace("chunks: []", "chunks: [LX-99999]")):
            with self.assertRaisesMessage(CommandError, "LX-99999"):
                call_command("load_content", verbosity=0)

    def test_build_lines_emotion_label(self):
        lines, speakers = build_lines([{"speaker": "tom", "text": "Hi", "emotion": "surprised"},
                                       {"speaker": "anna", "text": "Hi", "ru": "Привет"}])
        self.assertEqual((lines[0]["name"], lines[0]["emotion_ru"], lines[1]["emotion_ru"]), ("Том", "удивлённо", ""))
        self.assertEqual((lines[1]["ru"], lines[1]["kind"], lines[1]["emotion"]), ("Привет", "speech", "neutral"))
        self.assertEqual([s["id"] for s in speakers], ["tom", "anna"])


from django.urls import reverse
from tests.test_audit_weeks import VALID


class WeekPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)
        cls.week = Week.objects.get(level__code="A1", number=1)
        WeekScene.objects.filter(week=cls.week).delete()
        TongueTwister.objects.filter(week=cls.week).delete()
        WeekScene.objects.create(week=cls.week, can_do_ru="Я смогу представиться.", mission_ru="Скажите своё имя.", script=VALID)
        TongueTwister.objects.create(number=1, week=cls.week, series="sounds", text="[T2]This[/] [D1]is[/] [T2]this[/].", ipa="/ðɪs ɪz ðɪs/", source="original")

    def test_week_without_scene_is_200(self):
        # Все 14 недель A1 наполнены; неделя без сцены — первая неделя A1+.
        response = self.client.get(reverse("curriculum:week", args=["a1-plus", 1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неделя готовится")

    def test_week_with_scene_shows_blocks(self):
        response = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        html = response.content.decode()
        ids = [f'id="{block}"' for block in ("goal", "dialogue", "lessons", "chunks", "role", "twister", "mission")]
        self.assertEqual(response.status_code, 200)
        for item in ids:
            self.assertIn(item, html)
        self.assertEqual([html.index(item) for item in ids], sorted(html.index(item) for item in ids))
        self.assertContains(response, "Озвучка этой недели ещё не записана")
        self.assertNotContains(response, "generate_audio.bat")

    def test_level_lists_weeks(self):
        response = self.client.get(reverse("curriculum:level", args=["a1"]))
        for number in range(1, 15):
            self.assertContains(response, reverse("curriculum:week", args=["a1", number]))
        self.assertContains(response, "Знакомство и люди")
        # Все недели A1 наполнены — ни одной «готовится» на уровне A1.
        self.assertNotContains(response, "готовится")

    def test_guest_goal_redirects_to_login(self):
        response = self.client.post(reverse("learning:week_goal", args=[self.week.pk]), {"status": "done"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
        self.assertFalse(WeekGoal.objects.exists())

    def test_learner_goal_saved_and_bad_status_400(self):
        user = User.objects.create_user("goal@example.com", "s3cret-pass-123")
        self.client.force_login(user)
        url = reverse("learning:week_goal", args=[self.week.pk])
        response = self.client.post(url, {"status": "done"})
        self.assertRedirects(response, reverse("curriculum:week", args=["a1", 1]))
        self.assertEqual(WeekGoal.objects.get(user=user, week=self.week).status, "done")
        response = self.client.post(url, {"status": "not_yet"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(WeekGoal.objects.filter(user=user, week=self.week).count(), 1)
        self.assertEqual(WeekGoal.objects.get(user=user, week=self.week).status, "not_yet")
        self.assertEqual(self.client.post(url, {"status": "invalid"}).status_code, 400)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertContains(self.client.get(reverse("curriculum:week", args=["a1", 1])), 'name="csrfmiddlewaretoken"')

    def test_guest_sees_register_hint(self):
        response = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        self.assertContains(response, reverse("accounts:signup"))
        self.assertContains(response, "зарегистрируйтесь")

    def test_goal_is_personal_and_missing_week_is_404(self):
        first = User.objects.create_user("first@example.com", "s3cret-pass-123")
        second = User.objects.create_user("second@example.com", "s3cret-pass-123")
        WeekGoal.objects.create(user=first, week=self.week, status="done")
        self.client.force_login(second)
        self.client.post(reverse("learning:week_goal", args=[self.week.pk]), {"status": "not_yet"})
        self.assertEqual(WeekGoal.objects.get(user=first, week=self.week).status, "done")
        self.assertEqual(self.client.post(reverse("learning:week_goal", args=[999999]), {"status": "done"}).status_code, 404)

    def test_twister_has_russian_transcription_and_manual_override(self):
        response = self.client.get(reverse("curriculum:week", args=["a1", 1]))
        twister_html = response.content.decode().split('id="twister"', 1)[1].split('id="mission"', 1)[0]
        self.assertIn('class="ru-tr"', twister_html)
        twister = TongueTwister.objects.get(week=self.week)
        twister.ru = "мой ручной вариант"
        twister.save()
        self.assertContains(self.client.get(reverse("curriculum:week", args=["a1", 1])), "мой ручной вариант")

    def test_level_accepts_lesson_without_week(self):
        from apps.lessons.models import Lesson
        lesson = Lesson.objects.get(slug="a1-verb-be")
        lesson.week = None
        lesson.save()
        response = self.client.get(reverse("curriculum:level", args=["a1"]))
        self.assertContains(response, lesson.title)
        self.assertContains(response, reverse("lessons:detail", args=[lesson.slug]))


class SeedWeekContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", verbosity=0)

    def test_first_two_weeks_are_complete_and_audited(self):
        from apps.publishing.audit import run_audit, text_tokens
        for number in (1, 2):
            week = Week.objects.get(level__code="A1", number=number)
            scene = WeekScene.objects.get(week=week)
            self.assertTrue(scene.can_do_ru)
            self.assertTrue(scene.mission_ru)
            self.assertTrue(6 <= len(scene.script) <= 10)
            self.assertTrue(40 <= len(text_tokens(" ".join(line["text"] for line in scene.script))) <= 90)
            self.assertGreaterEqual(len({line["emotion"] for line in scene.script}), 3)
            self.assertTrue(all(line.get("ru") for line in scene.script))
            self.assertTrue(5 <= scene.chunks.count() <= 8)
            self.assertTrue(all(unit.unit_type == "phrase" and unit.cefr == "unverified" for unit in scene.chunks.all()))
            self.assertEqual(week.twister.source, "original")
            self.assertEqual(week.twister.series, "sounds")
        report = run_audit()
        self.assertEqual(report.errors, [])
        self.assertFalse([w for w in report.warnings if "Неделя A1-" in w or "можно сократить" in w])

    def test_lesson_contractions_are_loaded(self):
        from apps.lessons.models import Lesson
        pairs = Lesson.objects.get(slug="a1-verb-be").contractions
        self.assertEqual({p["short"] for p in pairs}, {"I'm", "you're", "it's", "isn't", "aren't"})
        for slug in ("a1-verb-be", "a1-determiners-a-the-this-my", "a1-have-like-can-do"):
            lesson = Lesson.objects.get(slug=slug)
            self.assertTrue(lesson.contractions)
            self.assertTrue(all(p["ipa"] and p["note_ru"] for p in lesson.contractions))

    def test_phrase_words_are_known_only_from_their_week(self):
        from apps.lexicon.models import LexicalUnit
        from apps.publishing.audit import known_vocabulary, vocab_until
        unit = LexicalUnit.objects.get(uid="LX-00001")
        unit.pk = None
        unit.uid = "LX-99999"
        unit.lemma = "A purple house"
        unit.forms = []
        unit.unit_type = "phrase"
        unit.week = Week.objects.get(level__code="A1", number=2)
        unit.save()
        self.assertNotIn("purple", vocab_until(unit.internal_level, 1))
        self.assertIn("purple", vocab_until(unit.internal_level, 2))
        self.assertIn("purple", known_vocabulary())
