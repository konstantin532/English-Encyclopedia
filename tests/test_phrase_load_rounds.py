"""Тренировка фраз: нагрузка по стажу, раунды по 10, живые сокращения, потолок длины."""
import random
from datetime import timedelta

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.drills.models import Exercise
from apps.learning import memory, phrase_practice
from apps.learning.models import ExerciseAttempt, UnitProgress
from apps.learning.phrase_checker import normalize
from apps.learning.phrase_engine import engine
from apps.learning.phrase_engine.spoken import spoken
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content


class SpokenFormTests(SimpleTestCase):
    CASES = [
        ("I am Tom.", "I'm Tom."),
        ("Yes, I am.", "Yes, I am."),                      # в конце фразы не сокращают
        ("I am not busy.", "I'm not busy."),
        ("He is not at home.", "He isn't at home."),
        ("There is not an apple in my box.", "There isn't an apple in my box."),
        ("There is an apple in the box.", "There's an apple in the box."),
        ("You do not play the guitar.", "You don't play the guitar."),
        ("Do not open the door.", "Don't open the door."),
        ("They did not knock.", "They didn't knock."),
        ("I cannot sleep.", "I can't sleep."),
        ("What is your name?", "What's your name?"),
        ("Where is it?", "Where is it?"),                  # перед местоимением не сокращают
        ("Where is my phone?", "Where's my phone?"),
        ("If it rains, we will stay at home.", "If it rains, we'll stay at home."),
        ("It will not rain.", "It won't rain."),
        ("Is it big?", "Is it big?"),
        ("Mia drinks coffee.", "Mia drinks coffee."),
    ]

    def test_american_contractions(self):
        for full, live in self.CASES:
            with self.subTest(full=full):
                self.assertEqual(spoken(full), live)

    def test_checker_accepts_both_forms(self):
        for full, live in self.CASES:
            with self.subTest(full=full):
                self.assertEqual(normalize(live), normalize(full))


class LoadSettingsTests(SimpleTestCase):
    def test_daily_load_grows_with_months_of_study(self):
        self.assertEqual(memory.daily_range(0), (10, 30))
        self.assertEqual(memory.daily_range(29), (10, 30))
        self.assertEqual(memory.daily_range(30), (30, 80))
        self.assertEqual(memory.daily_range(89), (30, 80))
        self.assertEqual(memory.daily_range(90), (80, 160))
        self.assertEqual(memory.daily_range(500), (80, 160))

    def test_round_size_and_length_caps(self):
        self.assertEqual(memory.round_size(), 10)
        self.assertEqual(memory.max_words((0, 1)), 5)
        self.assertEqual(memory.max_words((0, 4)), 5)
        self.assertEqual(memory.max_words((0, 5)), 7)
        self.assertEqual(memory.max_words((0, 14)), 7)
        self.assertEqual(memory.max_words((1, 1)), 9)
        self.assertEqual(memory.max_words((2, 3)), 11)


class GeneratorLimitsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_repeated_noun_is_detected(self):
        ctx, _, _ = engine.build_cached("t", (0, 14))
        self.assertTrue(engine.repeats_noun(["my", "mother", "have", "a", "mother"], ctx.U))
        self.assertFalse(engine.repeats_noun(["my", "mother", "have", "a", "brother"], ctx.U))

    def test_phrases_respect_level_cap_and_never_repeat_a_noun(self):
        rng = random.Random(28)
        for pos in ((0, 1), (0, 6), (0, 14), (1, 16)):
            ctx, fams, index = engine.build_cached("t", pos)
            cap = memory.max_words(pos)
            targets = sorted({it.unit.lemma for rows in fams.values() for r in rows for pool, _ in r.slots
                              for it in pool if it.unit is not None and phrase_practice.is_content(ctx.U.get(it.unit.lemma))})
            for target in targets[::4]:
                ph = engine.make_phrase(ctx, fams, target, rng, frozenset(), index, max_words=cap)
                with self.subTest(pos=pos, target=target):
                    self.assertIsNotNone(ph, "слово осталось без фраз")
                    self.assertLessEqual(engine.spoken_length(ph.text), cap, ph.text)
                    self.assertFalse(engine.repeats_noun(ph.lemmas, ctx.U), ph.text)

    def test_learner_sees_contracted_cards(self):
        ctx, _, index = engine.build_cached("t", (0, 14))
        text = "I am not busy."
        phrase = engine.Phrase(text, "F01", "be + прилагательное", "neg", "busy",
                               engine.lemmas_for(text, index, ctx.U, "busy"), [text])
        item = phrase_practice._item_payload(ctx, phrase, "full", random.Random(1), 1, 10, puzzle=True)
        self.assertEqual(sorted(item["bank"]), sorted(["I'm", "not", "busy"]))
        self.assertEqual(item["accepted"], [text])  # проверка — по полной форме, принимает обе


class DailyLoadPlanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.words = list(LexicalUnit.objects.filter(unit_type="word", internal_level__code="A1"))
        cls.exercise = Exercise.objects.first()

    def learner(self, days):
        user = User.objects.create_user(email=f"load-{days}@example.test", password="password")
        UnitProgress.objects.bulk_create([UnitProgress(user=user, unit=u) for u in self.words])
        if days is not None:
            attempt = ExerciseAttempt.objects.create(user=user, exercise=self.exercise, answer="x", is_correct=True)
            ExerciseAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now() - timedelta(days=days))
        return user

    def test_days_learning_counts_from_first_exercise(self):
        self.assertEqual(phrase_practice.days_learning(self.learner(None)), 0)
        self.assertEqual(phrase_practice.days_learning(self.learner(45)), 45)

    def test_plan_size_follows_months_of_study(self):
        for days in (3, 45, 120):
            lo, hi = memory.daily_range(days)
            plan = phrase_practice.plan_day(self.learner(days))
            with self.subTest(days=days):
                self.assertGreaterEqual(len(plan["queue"]), lo)
                self.assertLessEqual(len(plan["queue"]), hi)


@override_settings(EE_PHRASE_MEMORY_ENABLED=True)
class RoundViewTests(TestCase):
    url = "/learning/phrases/"

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(email="rounds@example.test", password="password")
        self.client.force_login(self.user)
        units = LexicalUnit.objects.filter(unit_type="word", internal_level__code="A1")
        UnitProgress.objects.bulk_create([UnitProgress(user=self.user, unit=u) for u in units])

    def state(self):
        return self.client.session[phrase_practice.SESSION_KEY]

    def answer_one(self):
        self.client.get(self.url)
        item = self.state()["item"]
        self.client.post(self.url, {"action": "check", "item": item["id"], "answer": item["accepted"][0]})
        self.client.post(self.url, {"action": "next"})

    def test_break_after_ten_then_more_or_stop(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Раунд 1 · фраза 1 из 10")
        for _ in range(10):
            self.answer_one()
        r = self.client.get(self.url)
        self.assertContains(r, "data-phrase-round-break")
        self.assertContains(r, "Раунд 1 готов")
        self.assertContains(r, "Верно 10 из 10.")
        self.assertNotContains(r, 'name="answer"')

        self.client.post(self.url, {"action": "stop"})
        r = self.client.get(self.url)
        self.assertContains(r, "data-phrase-paused")
        self.assertContains(r, "Сегодня сделано 10 фраз")

        self.client.post(self.url, {"action": "more"})
        r = self.client.get(self.url)
        self.assertContains(r, "Раунд 2 · фраза 1 из")
        self.assertContains(r, 'name="answer"')

    def test_full_form_answer_is_correct_and_sample_is_contracted(self):
        for _ in range(30):
            self.client.get(self.url)
            item = self.state()["item"]
            full = item["accepted"][0]
            self.client.post(self.url, {"action": "check", "item": item["id"], "answer": full})
            result = self.state()["item"]["result"]
            self.assertTrue(result["correct"], full)
            self.assertEqual(result["sample"], spoken(full))
            if spoken(full) != full:
                return
            self.client.post(self.url, {"action": "next"})
            if self.state().get("round_break"):
                self.client.post(self.url, {"action": "more"})
        self.skipTest("за 30 фраз не попалось фразы с сокращением")
