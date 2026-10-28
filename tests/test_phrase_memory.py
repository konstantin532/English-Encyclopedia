"""Модуль «Память слов», генератор фраз, общая проверка ответов и страница тренировки."""
import random
import re
from datetime import datetime, timedelta, timezone as dt_tz
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts.models import User
from apps.learning import memory, phrase_practice
from apps.learning.models import PhraseStats, UnitProgress
from apps.learning.phrase_checker import check, normalize
from apps.learning.phrase_engine import engine, lexicon
from apps.learning.trainer_content import UNIT_UIDS as PILOT_UIDS
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content

T0 = datetime(2026, 3, 2, 9, 0, tzinfo=dt_tz.utc)


def fresh():
    return SimpleNamespace(memory_stability=None, memory_reviewed_at=None, memory_evidence={})


class MemoryMathTests(SimpleTestCase):
    def test_rating_is_recall_probability(self):
        p = fresh()
        memory.start(p, T0)
        self.assertAlmostEqual(memory.rating(p, T0), 79.0)  # ворота 3 дней / 2 семейств
        p.memory_evidence = {"days": ["a", "b", "c"], "families": ["x", "y"]}
        self.assertAlmostEqual(memory.rating(p, T0), 100.0)
        self.assertAlmostEqual(memory.rating(p, T0 + timedelta(days=1)), 90.0)
        self.assertAlmostEqual(memory.rating(p, T0 + timedelta(days=2)), 81.0)

    def test_growth_once_per_day_and_stronger_when_harder(self):
        p = fresh()
        memory.start(p, T0)
        memory.apply(p, correct=True, mode="independent", family="f1", now=T0 + timedelta(days=1))
        s1 = p.memory_stability
        self.assertGreater(s1, 2.0)
        for _ in range(5):  # зубрёжка в тот же день не растит прочность
            memory.apply(p, correct=True, mode="independent", family="f1", now=T0 + timedelta(days=1, hours=1))
        self.assertEqual(p.memory_stability, s1)
        q = fresh()
        memory.start(q, T0)
        memory.apply(q, correct=True, mode="full", family="f1", now=T0 + timedelta(days=1))
        self.assertLess(q.memory_stability, s1)  # с подсказкой рост слабее

    def test_mastery_needs_three_days_and_two_families(self):
        p = fresh()
        memory.start(p, T0)
        for d in range(3):
            memory.apply(p, correct=True, mode="independent", family="same", now=T0 + timedelta(days=d))
        self.assertLess(memory.rating(p, T0 + timedelta(days=2)), 80)
        memory.apply(p, correct=True, mode="transfer", family="other", now=T0 + timedelta(days=3))
        self.assertGreaterEqual(memory.rating(p, T0 + timedelta(days=3)), 80)

    def test_error_types_and_hint_after_three_errors(self):
        cfg = memory.config()
        for kind, mult in cfg["error_multiplier"].items():
            p = fresh()
            memory.start(p, T0)
            p.memory_stability = 10.0
            memory.apply(p, correct=False, error=kind, now=T0)
            self.assertAlmostEqual(p.memory_stability, max(cfg["min_stability_days"], 10.0 * mult))
        p = fresh()
        memory.start(p, T0)
        for _ in range(3):
            memory.apply(p, correct=False, error="wrong", now=T0)
        self.assertTrue(memory.needs_hint(p))
        self.assertEqual(memory.pick_mode(p, 95.0), "full")
        self.assertGreaterEqual(p.memory_stability, cfg["min_stability_days"])

    def test_learner_label_capped_by_days(self):
        p = fresh()
        memory.start(p, T0)
        memory.apply(p, correct=True, mode="full", family="f", now=T0)
        self.assertGreater(memory.rating(p, T0), 70)  # расписание: только что вспомнил
        self.assertEqual(memory.stage_name(memory.display_rating(p, T0)), "Неустойчивое")
        memory.apply(p, correct=True, mode="independent", family="g", now=T0 + timedelta(days=1))
        self.assertLessEqual(memory.display_rating(p, T0 + timedelta(days=1)), 69)

    def test_unknown_mode_or_error_rejected(self):
        p = fresh()
        with self.assertRaises(ValueError):
            memory.apply(p, correct=True, mode="magic")
        with self.assertRaises(ValueError):
            memory.apply(p, correct=False, error="nope")

    def test_stage_chance_and_strength_labels(self):
        self.assertEqual(memory.chance(10), 0.90)
        self.assertEqual(memory.chance(65), 0.45)
        self.assertEqual(memory.chance(99), 0.05)
        self.assertEqual(memory.stage_name(None), "Новое")
        self.assertEqual(memory.strength_step(1), 0)
        self.assertEqual(memory.strength_step(400), 8)

    def test_level_override_falls_back_to_common(self):
        self.assertEqual(memory.config("B2")["session"]["per_word_max"],
                         memory.config()["session"]["per_word_max"])


class CheckerTests(SimpleTestCase):
    index = {"she": ["she"], "drinks": ["drink"], "drink": ["drink"], "coffee": ["coffee"],
             "the": ["the"], "umbrella": ["umbrella"], "is": ["be"], "in": ["in"], "my": ["my"],
             "bag": ["bag"], "tea": ["tea"], "very": ["very"]}
    units = {"the": SimpleNamespace(cls="T1"), "be": SimpleNamespace(cls="D1"), "in": SimpleNamespace(cls="P1"),
             "my": SimpleNamespace(cls="T3"), "drink": SimpleNamespace(cls="D2"), "coffee": SimpleNamespace(cls="S3"),
             "umbrella": SimpleNamespace(cls="S2"), "bag": SimpleNamespace(cls="S2"), "she": SimpleNamespace(cls="T8")}

    def run_check(self, answer, sample="She drinks coffee.", lemmas=("she", "drink", "coffee"), extra=()):
        return check(answer, [sample, *extra], list(lemmas), self.index, self.units)

    def test_normalization_and_contractions(self):
        self.assertEqual(normalize("I'm here, OK?"), ["i", "am", "here", "ok"])
        self.assertEqual(normalize("She doesn’t"), ["she", "does", "not"])
        self.assertEqual(normalize("I can not"), ["i", "cannot"])
        self.assertTrue(self.run_check("she drinks coffee").correct)
        r = check("The umbrella's in my bag", ["The umbrella is in my bag."],
                  ["the", "umbrella", "be", "in", "my", "bag"], self.index, self.units)
        self.assertFalse(r.correct)  # 's после существительного не разворачивается — честно не засчитано

    def test_alternative_order_accepted(self):
        r = check("We will swim if it is sunny", ["If it is sunny, we will swim.", "We will swim if it is sunny."],
                  [], {}, {})
        self.assertEqual(r.status, "correct_alt")

    def test_form_error_is_attributed_to_the_word(self):
        r = self.run_check("She drink coffee.")
        self.assertEqual((r.kind, r.memory_error, r.lemma, r.confidence), ("form", "form", "drink", "high"))

    def test_typo_order_missing_extra_empty(self):
        r = self.run_check("She drinks cofee.")
        self.assertEqual((r.kind, r.lemma), ("typo", "coffee"))
        r = self.run_check("Coffee she drinks.")
        self.assertEqual((r.kind, r.lemma), ("order", None))
        r = self.run_check("She coffee.")
        self.assertEqual((r.kind, r.lemma), ("missing", "drink"))
        r = self.run_check("She drinks very coffee.")
        self.assertEqual((r.kind, r.lemma), ("extra", None))
        r = self.run_check("   ")
        self.assertEqual((r.kind, r.memory_error), ("empty", "dontknow"))

    def test_different_sentence_is_unsure_and_not_blamed_on_a_word(self):
        r = check("I am fine", ["Eat dinner, please."], ["eat", "dinner", "please"], {"i": ["I"], "am": ["be"],
                  "fine": ["fine"], "eat": ["eat"], "dinner": ["dinner"], "please": ["please"]}, {})
        self.assertEqual((r.status, r.lemma, r.memory_error), ("unsure", None, ""))

    def test_unknown_word_is_unsure_not_wrong(self):
        r = self.run_check("She drinks espresso.")
        self.assertEqual(r.status, "unsure")
        self.assertEqual(r.memory_error, "")

    def test_wrong_word_and_only_first_error_reported(self):
        r = self.run_check("She drinks tea.")
        self.assertEqual((r.kind, r.memory_error, r.lemma), ("wrong", "wrong", "coffee"))
        r = self.run_check("She drink tea.")  # две ошибки: сообщаем первую
        self.assertEqual((r.kind, r.lemma, r.confidence), ("form", "drink", "medium"))


class GeneratorOnCourseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        lexicon.clear_cache()
        engine.build_cached.cache_clear()

    def test_markup_matches_dictionary(self):
        units, problems = lexicon.load("t")
        self.assertEqual(list(problems), [])
        unmarked = [u.uid for u in units.values() if u.level in ("A1", "A1+") and not u.marked]
        self.assertEqual(unmarked, [], "у каждого слова A1/A1+ должна быть разметка")

    def test_new_levels_need_no_code(self):
        units, _ = lexicon.load("t")
        orders = {u.level: u.level_order for u in units.values()}
        self.assertEqual(orders["A1"], 1)
        self.assertEqual(orders["A1+"], 2)  # позиция — из Level.order, не из списка в коде

    def test_targeted_phrase_contains_target_and_maps_tokens(self):
        ctx, fams, index = engine.build_cached("t", (0, 14))
        rng = random.Random(3)
        for target in ("coffee", "umbrella", "drink", "teacher", "cold"):
            ph = engine.make_phrase(ctx, fams, target, rng, frozenset(), index)
            self.assertIsNotNone(ph, target)
            self.assertIn(target, ph.lemmas, ph.text)
            self.assertEqual(len(ph.lemmas), len(engine.tokenize(ph.text)))
            self.assertTrue(check(ph.text, ph.accepted, ph.lemmas, index, ctx.U).correct)

    def test_grammar_invariants_on_random_phrases(self):
        ctx, fams, _ = engine.build_cached("t", (1, 16))
        rng = random.Random(20261027)
        vowel = re.compile(r"\ba ([aeiou]\w*)", re.I)
        for fid, rows in fams.items():
            for s in engine.sample(rows, 40, rng):
                self.assertRegex(s, r"^[A-Z].*[.?]$", s)
                self.assertNotIn("  ", s)
                self.assertNotRegex(s, r"\bThere are an? \b", s)
                if fid not in engine.SOME_OK_IN_QUESTIONS:
                    self.assertFalse(s.endswith("?") and " some " in s, s)
                    self.assertNotRegex(s, r"\b(do|does|did) not \w+ some\b", s)
                for m in vowel.finditer(s):
                    word = m.group(1).lower()
                    if word in ctx.U and ctx.U[word].ipa and not ctx.U[word].ipa.strip("/ˈˌ").startswith(("j", "w")):
                        self.fail(f"«a {word}» вместо «an»: {s}")

    def test_a1_never_uses_a1_plus_words(self):
        ctx, fams, index = engine.build_cached("t", (0, 14))
        rng = random.Random(1)
        for rows in fams.values():
            for s in engine.sample(rows, 15, rng):
                for lem in engine.lemmas_for(s, index, ctx.U):
                    if lem and lem in ctx.U:
                        self.assertLessEqual(ctx.U[lem].pos, (0, 14), f"{lem} в «{s}»")


class RegisterHookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(email="memory-hook@example.test", password="password")
        self.unit = LexicalUnit.objects.get(lemma="coffee")

    def test_disabled_flag_writes_nothing(self):
        p = UnitProgress.objects.create(user=self.user, unit=self.unit)
        p.register(True, "lesson#1")
        self.assertIsNone(p.memory_stability)
        self.assertEqual(p.memory_evidence, {})

    @override_settings(EE_PHRASE_MEMORY_ENABLED=True)
    def test_enabled_flag_keeps_legacy_schedule(self):
        a = UnitProgress.objects.create(user=self.user, unit=self.unit)
        a.register(True, "lesson-x#1")
        with override_settings(EE_PHRASE_MEMORY_ENABLED=False):
            other = User.objects.create_user(email="memory-hook-2@example.test", password="password")
            b = UnitProgress.objects.create(user=other, unit=self.unit)
            b.register(True, "lesson-x#1")
        self.assertEqual((a.stage, a.status, a.correct_count), (b.stage, b.status, b.correct_count))
        self.assertIsNotNone(a.memory_stability)
        self.assertIn("lesson:lesson-x", a.memory_evidence["families"])


@override_settings(EE_PHRASE_MEMORY_ENABLED=True)
class PhrasePracticeViewTests(TestCase):
    url = "/learning/phrases/"

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(email="phrases@example.test", password="password")
        self.client.force_login(self.user)

    def give_progress(self, lemmas):
        for lem in lemmas:
            UnitProgress.objects.get_or_create(user=self.user, unit=LexicalUnit.objects.get(lemma=lem))

    def test_flag_off_is_not_found(self):
        with override_settings(EE_PHRASE_MEMORY_ENABLED=False):
            r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r["Cache-Control"], "private, no-store")

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_without_lessons_shows_start_hint(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Сначала — урок")

    def test_full_cycle_correct_answer_updates_memory_once(self):
        self.give_progress(["coffee", "tea", "water", "drink", "teacher", "book", "table", "cold", "big"])
        r = self.client.get(self.url)
        self.assertContains(r, "Составьте")
        item = self.client.session[phrase_practice.SESSION_KEY]["item"]
        payload = {"action": "check", "item": item["id"], "answer": item["accepted"][0]}
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        target = UnitProgress.objects.get(user=self.user, unit__lemma=item["target"])
        self.assertIsNotNone(target.memory_stability)
        snapshot = (target.memory_stability, target.memory_reviewed_at)
        self.client.post(self.url, payload)  # повтор того же запроса
        target.refresh_from_db()
        self.assertEqual((target.memory_stability, target.memory_reviewed_at), snapshot)
        r = self.client.get(self.url)
        self.assertContains(r, "Верно")
        self.client.post(self.url, {"action": "next"})
        nxt = self.client.session[phrase_practice.SESSION_KEY]
        self.client.get(self.url)
        nxt = self.client.session[phrase_practice.SESSION_KEY]["item"]
        self.assertNotEqual(nxt["id"], item["id"])

    def test_order_error_does_not_penalise_a_word(self):
        self.give_progress(["coffee", "tea", "drink", "teacher", "book", "table", "big"])
        self.client.get(self.url)
        item = self.client.session[phrase_practice.SESSION_KEY]["item"]
        words = item["accepted"][0].rstrip(".?").split()
        if len(words) < 2:
            self.skipTest("однословная фраза")
        swapped = " ".join(reversed(words))
        self.client.post(self.url, {"action": "check", "item": item["id"], "answer": swapped})
        res = self.client.session[phrase_practice.SESSION_KEY]["item"]["result"]
        if res["kind"] == "order":
            self.assertEqual(res["changes"], [])

    def test_pilot_units_are_never_targets_or_changed(self):
        pilot = list(LexicalUnit.objects.filter(uid__in=PILOT_UIDS))
        for unit in pilot:
            UnitProgress.objects.create(user=self.user, unit=unit, stage=2)
        self.give_progress(["coffee", "drink", "teacher", "water"])
        plan = phrase_practice.plan_day(self.user)
        pilot_lemmas = {u.lemma for u in pilot}
        self.assertFalse(pilot_lemmas & set(plan["queue"]))
        for _ in range(3):
            self.client.get(self.url)
            item = self.client.session[phrase_practice.SESSION_KEY].get("item")
            if not item:
                break
            self.client.post(self.url, {"action": "check", "item": item["id"], "answer": item["accepted"][0]})
            self.client.post(self.url, {"action": "next"})
        for p in UnitProgress.objects.filter(user=self.user, unit__uid__in=PILOT_UIDS):
            self.assertIsNone(p.memory_stability)
            self.assertEqual(p.stage, 2)

    def test_other_learner_progress_is_untouched(self):
        other = User.objects.create_user(email="phrases-other@example.test", password="password")
        unit = LexicalUnit.objects.get(lemma="coffee")
        theirs = UnitProgress.objects.create(user=other, unit=unit)
        self.give_progress(["coffee", "drink", "teacher", "water", "tea"])
        self.client.get(self.url)
        item = self.client.session[phrase_practice.SESSION_KEY]["item"]
        self.client.post(self.url, {"action": "check", "item": item["id"], "answer": item["accepted"][0]})
        theirs.refresh_from_db()
        self.assertIsNone(theirs.memory_stability)

    def test_dont_know_weakens_the_target_word(self):
        self.give_progress(["coffee", "drink", "teacher", "water", "tea"])
        self.client.get(self.url)
        item = self.client.session[phrase_practice.SESSION_KEY]["item"]
        self.client.post(self.url, {"action": "dont_know", "item": item["id"]})
        target = UnitProgress.objects.get(user=self.user, unit__lemma=item["target"])
        self.assertEqual(target.memory_stability, memory.config()["min_stability_days"])
        self.assertContains(self.client.get(self.url), "Образец")

    def test_word_bank_keeps_real_capitals_only(self):
        ctx, fams, index = engine.build_cached(phrase_practice.content_version(), (0, 14))
        ph = engine.Phrase("Watch TV on Mondays.", "F07", "x", "aff", "TV", ["watch", "TV", "on", "Monday"], [])
        item = phrase_practice._item_payload(ctx, ph, "partial", random.Random(1), 1, 1)
        self.assertEqual(sorted(item["bank"]), sorted(["watch", "TV", "on", "Mondays"]))
        ph = engine.Phrase("I like tea.", "F05", "x", "aff", "tea", ["I", "like", "tea"], [])
        item = phrase_practice._item_payload(ctx, ph, "partial", random.Random(1), 1, 1)
        self.assertIn("I", item["bank"])

    def test_forged_item_id_is_ignored(self):
        self.give_progress(["coffee", "drink", "teacher"])
        self.client.get(self.url)
        self.client.post(self.url, {"action": "check", "item": "forged", "answer": "x"})
        self.assertFalse(UnitProgress.objects.filter(user=self.user, memory_stability__isnull=False).exists())


class PuzzleShareTests(SimpleTestCase):
    def test_puzzle_share_follows_twelve_steps(self):
        steps = memory.config()["input"]["puzzle_steps"]
        self.assertEqual(len(steps), 14)  # старт + 12 ступеней + постоянная доля
        self.assertEqual(memory.puzzle_percent(0), 100)
        self.assertEqual(memory.puzzle_percent(2999), 100)
        self.assertLess(memory.puzzle_percent(3000), 100)
        self.assertEqual(memory.puzzle_percent(10000), 15)
        self.assertEqual(memory.puzzle_percent(50000), 15)
        shares = [memory.puzzle_percent(n) for n in range(0, 10001, 50)]
        self.assertEqual(shares, sorted(shares, reverse=True))
        self.assertEqual(memory.puzzle_step(2999), 0)
        self.assertEqual(memory.puzzle_step(10000), 13)

    def test_puzzle_grows_memory_less_than_independent(self):
        def grown(mode):
            p = fresh()
            memory.apply(p, correct=True, mode="independent", family="f", now=T0)
            memory.apply(p, correct=True, mode=mode, family="g", now=T0 + timedelta(days=3))
            return p.memory_stability
        self.assertLess(grown("puzzle"), grown("independent"))


@override_settings(EE_PHRASE_MEMORY_ENABLED=True)
class PuzzleInputViewTests(TestCase):
    url = "/learning/phrases/"

    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(email="puzzle@example.test", password="password")
        self.client.force_login(self.user)
        for lem in ["coffee", "tea", "water", "drink", "teacher", "book", "table", "cold", "big"]:
            UnitProgress.objects.get_or_create(user=self.user, unit=LexicalUnit.objects.get(lemma=lem))

    def test_beginner_always_gets_puzzle_and_counter_grows(self):
        r = self.client.get(self.url)
        item = self.client.session[phrase_practice.SESSION_KEY]["item"]
        self.assertEqual(item["input"], "puzzle")
        self.assertEqual(item["mode"], "puzzle")
        # карточки — в живой форме (I'm, don't): столько же, сколько слов видит ученик
        self.assertEqual(len(item["bank"]), engine.spoken_length(item["accepted"][0]))
        self.assertContains(r, "data-phrase-puzzle")
        self.assertContains(r, "пазлов сейчас: 100%")
        payload = {"action": "check", "item": item["id"], "answer": item["accepted"][0]}
        self.client.post(self.url, payload)
        self.client.post(self.url, payload)  # повтор не считается дважды
        self.assertEqual(PhraseStats.objects.get(user=self.user).correct_total, 1)

    def test_wrong_answer_does_not_count(self):
        self.client.get(self.url)
        item = self.client.session[phrase_practice.SESSION_KEY]["item"]
        self.client.post(self.url, {"action": "dont_know", "item": item["id"]})
        self.assertFalse(PhraseStats.objects.filter(user=self.user, correct_total__gt=0).exists())

    def test_experienced_learner_mostly_types(self):
        PhraseStats.objects.create(user=self.user, correct_total=20000)
        ctx, fams, index = engine.build_cached(phrase_practice.content_version(), (0, 14))
        ph = engine.Phrase("I like tea.", "F05", "x", "aff", "tea", ["I", "like", "tea"], [])
        share = memory.puzzle_percent(phrase_practice.correct_total(self.user))
        inputs = []
        for i in range(200):
            rng = random.Random(i)
            puzzle = rng.random() * 100 < share
            inputs.append(phrase_practice._item_payload(ctx, ph, "independent", rng, 1, 1, puzzle))
        puzzles = [it for it in inputs if it["input"] == "puzzle"]
        self.assertTrue(10 <= len(puzzles) <= 50)
        self.assertTrue(all(it["mode"] == "puzzle" and it["bank"] for it in puzzles))
        self.assertTrue(all(it["mode"] == "independent" and not it["bank"] for it in inputs if it["input"] == "typing"))
        self.assertContains(self.client.get(self.url), "пазлов сейчас: 15%")


class PhraseEntryLinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(email="phrases-link@example.test", password="password")
        self.client.force_login(self.user)

    def test_link_hidden_when_disabled(self):
        r = self.client.get("/learning/")
        self.assertNotContains(r, 'href="/learning/phrases/"')

    @override_settings(EE_PHRASE_MEMORY_ENABLED=True)
    def test_link_in_menu_and_dashboard_when_enabled(self):
        r = self.client.get("/learning/")
        self.assertContains(r, 'href="/learning/phrases/"', count=2)
        self.assertContains(r, "Начать тренировку")
