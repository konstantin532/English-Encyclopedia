"""Перевод с русского на английский: ученик сам строит фразу."""
import json

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.drills.models import PracticeItem, loose_normalize
from apps.lessons.models import Lesson
from apps.learning.mistake_review import variants_for
from apps.learning.models import MistakeReview, UnitProgress
from apps.publishing.audit import is_known, text_tokens, vocab_until
from tests.runner import ensure_content


class NormalizeTests(SimpleTestCase):
    def test_contractions_and_full_forms_are_equal(self):
        for short, full in [("I'm home.", "I am home"), ("It isn't my box!", "it is not my box"),
                            ("I don't know", "I do not know"), ("I can't sleep", "I cannot sleep"),
                            ("What’s your name?", "What is your name")]:
            self.assertEqual(loose_normalize(short), loose_normalize(full), short)

    def test_punctuation_and_case_do_not_matter(self):
        self.assertEqual(loose_normalize("Sorry?  Can you say it AGAIN, please?"),
                         loose_normalize("sorry can you say it again please"))

    def test_possessive_is_not_expanded(self):
        self.assertNotEqual(loose_normalize("Mia's brother"), loose_normalize("Mia is brother"))


class TranslationContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def lessons(self):
        return Lesson.objects.filter(level__code="A1", is_published=True).select_related("level", "week")

    def test_every_a1_lesson_has_four_translations(self):
        lessons = list(self.lessons())
        self.assertEqual(len(lessons), 28)
        for lesson in lessons:
            with self.subTest(lesson=lesson.slug):
                items = list(lesson.practice_items.all())
                self.assertEqual([i.order for i in items], [1, 2, 3, 4])
                self.assertTrue(all(i.kind == "translate" and i.prompt_ru and i.explanation_ru for i in items))

    def test_answers_use_only_vocabulary_known_by_the_lesson_week(self):
        for lesson in self.lessons():
            vocab = vocab_until(lesson.level, lesson.week.number)
            for item in lesson.practice_items.all():
                for text in [item.answer, *item.accepted]:
                    unknown = [t for t in text_tokens(text) if not is_known(t, vocab)]
                    self.assertEqual(unknown, [], f"{lesson.slug} #{item.order}: {text}")

    def test_model_answer_is_accepted(self):
        for item in PracticeItem.objects.all():
            self.assertTrue(item.is_correct(item.answer), item)
            self.assertTrue(all(item.is_correct(a) for a in item.accepted), item)
            self.assertFalse(item.is_correct(""), item)

    def test_cafe_servings_require_plural_in_translation_checker(self):
        # These are orders for individual servings, not names on a menu.
        # The old accepted list contradicted the lesson's plural explanation.
        cases = (
            (1, "Two coffees and one tea, please.", "Two coffee and one tea, please."),
            (2, "Three teas, please.", "Three tea, please."),
        )
        for order, correct, singular in cases:
            item = PracticeItem.objects.get(lesson__slug="a1-numbers-1-20", order=order)
            with self.subTest(order=order):
                for given, expected in ((correct, True), (singular, False)):
                    response = self.client.post(
                        f"/api/practice/{item.pk}/check/",
                        json.dumps({"answer": given}),
                        content_type="application/json",
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["correct"], expected)

    def test_review_target_has_delayed_questions(self):
        for item in PracticeItem.objects.select_related("lesson"):
            exercise = item.lesson.exercises.get(order=item.review_of)
            self.assertTrue(variants_for(exercise), item)


class TranslationApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.item = PracticeItem.objects.get(lesson__slug="a1-verb-be", order=1)

    def post(self, url, body):
        return self.client.post(url, json.dumps(body), content_type="application/json").json()

    def url(self):
        return f"/api/practice/{self.item.pk}/check/"

    def test_contraction_counts_as_correct(self):
        data = self.post(self.url(), {"answer": "I'm at home"})
        self.assertTrue(data["correct"])
        self.assertEqual(data["assessment"], "model_match")

    def test_mismatch_is_not_declared_an_error(self):
        data = self.post(self.url(), {"answer": "Me home"})
        self.assertFalse(data["correct"])
        self.assertEqual(data["assessment"], "needs_review")
        self.assertNotIn("answer", data)

    def test_reveal_shows_model_and_explanation(self):
        data = self.post(self.url(), {"reveal": True})
        self.assertEqual(data["answer"], self.item.answer)
        self.assertTrue(data["explanation"])

    def test_correct_answer_saves_word_progress_for_learner(self):
        user = get_user_model().objects.create_user("t1", password="pw-12345-x")
        self.client.force_login(user)
        self.post(self.url(), {"answer": self.item.answer})
        self.assertTrue(UnitProgress.objects.filter(user=user).exists())

    def test_optional_review_is_scheduled_only_on_request(self):
        user = get_user_model().objects.create_user("t2", password="pw-12345-x")
        self.client.force_login(user)
        self.post(self.url(), {"answer": "Me home"})
        self.assertFalse(MistakeReview.objects.filter(user=user).exists())
        response = self.client.post(f"/learning/practice-review/{self.item.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(MistakeReview.objects.filter(user=user).exists())

    def test_lesson_page_renders_translation_section(self):
        html = self.client.get(f"/lessons/{self.item.lesson.slug}/").content.decode()
        self.assertIn('id="translate"', html)
        self.assertIn('data-kind="translate"', html)
        self.assertIn(self.item.prompt_ru, html)
