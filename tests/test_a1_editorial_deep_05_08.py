"""Live key and learning-evidence regressions for the deep A1 lessons 5–8 pass.

Unmatched free answers remain needs_review; finite keys do not prove that an
unlisted sentence is ungrammatical. These tests exercise the actual API/forms.
"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.drills.models import Exercise, PracticeItem
from apps.learning.models import ExerciseAttempt, IndependentAttempt, MistakeReview, UnitProgress
from tests.runner import ensure_content

CAFE = "a1-cafe-order"
NUMBERS = "a1-numbers-1-20"
PHOTO = "a1-family-photo"
POSSESSION = "a1-family-possession"


class DeepA1AnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check(self, item, answer, matches):
        collection = "practice" if isinstance(item, PracticeItem) else "exercises"
        response = self.client.post(
            f"/api/{collection}/{item.pk}/check/", json.dumps({"answer": answer}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["correct"], matches, answer)
        if collection == "practice" or item.stage == Exercise.Stage.TRANSFER:
            self.assertEqual(data["assessment"], "model_match" if matches else "needs_review")
        return data

    def test_cafe_transfer_accepts_taught_requests_and_both_ordered_items(self):
        for uid, good, bad in (
            ("EX-00025", ("I'd like a tea, please.", "I would like a tea, please."),
             ("I'd like a coffee, please.", "I don't like tea.", "I would tea, please.")),
            ("EX-00027", ("I'd like a juice and a sandwich, please.",
                          "I would like a juice and a sandwich, please.",
                          "A juice and a sandwich, please."),
             ("I'd like a sandwich, please.", "I'd like a juice, please.",
              "I'd like a tea and a coffee, please.")),
        ):
            item = Exercise.objects.get(uid=uid)
            for answer in good:
                with self.subTest(uid=uid, answer=answer):
                    self.check(item, answer, True)
            for answer in bad:
                with self.subTest(uid=uid, answer=answer):
                    self.check(item, answer, False)

    def test_four_servings_preserve_number_drink_and_plural(self):
        item = Exercise.objects.get(uid="EX-00031")
        for answer in ("I'd like four teas, please.", "I would like four teas, please.",
                       "Can I have four teas, please?", "Four teas, please."):
            with self.subTest(answer=answer):
                self.check(item, answer, True)
        for answer in ("I'd like three teas, please.", "I'd like four coffees, please.",
                       "I'd like four tea, please.", "I don't like four teas."):
            with self.subTest(answer=answer):
                self.check(item, answer, False)

    def test_number_translations_accept_requests_without_swapping_the_quantities(self):
        for order, good, bad in (
            (1, ("Can I have two coffees and one tea, please?",
                 "I'd like two coffees and one tea, please.", "One tea and two coffees, please."),
             ("One coffee and two teas, please.", "Two coffee and one tea, please.")),
            (2, ("Can I have three teas, please?", "I'd like three teas, please."),
             ("Can I have thirteen teas, please?", "Three tea, please.")),
        ):
            item = PracticeItem.objects.get(lesson__slug=NUMBERS, order=order)
            for answer in good:
                with self.subTest(order=order, answer=answer):
                    self.check(item, answer, True)
            for answer in bad:
                with self.subTest(order=order, answer=answer):
                    self.check(item, answer, False)

    def test_photo_transfer_accepts_years_old_but_preserves_sister_and_age(self):
        item = Exercise.objects.get(uid="EX-00035")
        for answer in ("This is my sister. She is twelve years old.",
                       "This is my sister. She is 12 years old.",
                       "It is my sister. She is twelve.", "It's my sister. She is twelve."):
            with self.subTest(answer=answer):
                self.check(item, answer, True)
        for answer in ("This is your sister. She is twelve.",
                       "This is my sister. She is twenty.",
                       "This is my brother. He is twelve.",
                       "This is my sister. She has twelve."):
            with self.subTest(answer=answer):
                self.check(item, answer, False)

    def test_name_translations_allow_only_the_explicit_noun_contractions(self):
        for order, good, bad in (
            (1, ("Her name's Mia.", "Her name’s Mia."),
             ("His name is Mia.", "Her name is Anna.", "Her name Mia.")),
            (3, ("His name's Tom.", "His name’s Tom."),
             ("Her name is Tom.", "His name is Anna.", "His name Tom.")),
        ):
            item = PracticeItem.objects.get(lesson__slug=POSSESSION, order=order)
            for answer in good:
                with self.subTest(order=order, answer=answer):
                    self.check(item, answer, True)
            for answer in bad:
                with self.subTest(order=order, answer=answer):
                    self.check(item, answer, False)

    def test_possessive_slot_does_not_accept_a_missing_apostrophe_or_a_copula(self):
        item = Exercise.objects.get(uid="EX-00039")
        for answer, matches in (("Tom's", True), ("Tom’s", True),
                                ("Tom", False), ("Toms", False), ("Tom is", False)):
            with self.subTest(answer=answer):
                self.check(item, answer, matches)

    def test_mias_brother_translation_preserves_possession_and_age(self):
        item = PracticeItem.objects.get(lesson__slug=POSSESSION, order=2)
        for answer in ("Mia's brother is 10.", "Mia's brother is ten years old.",
                       "Mia's brother is 10 years old."):
            with self.subTest(answer=answer):
                self.check(item, answer, True)
        for answer in ("Mia is brother is ten.", "Tom's brother is ten.",
                       "Mia's brother is twenty.", "Mia's sister is ten.",
                       "Mia's brother is not ten."):
            with self.subTest(answer=answer):
                self.check(item, answer, False)


class DeepA1EvidenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def credit(self, collection, item, answer, required, forbidden, serial):
        user = get_user_model().objects.create_user(email=f"deep-a1-{serial}@example.test", password="Test-pass-123!")
        self.client.force_login(user)
        response = self.client.post(f"/api/{collection}/{item.pk}/check/", json.dumps({"answer": answer}),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["correct"])
        credited = set(UnitProgress.objects.filter(user=user).values_list("unit__uid", flat=True))
        self.assertTrue(set(required) <= credited, credited)
        self.assertFalse(set(forbidden) & credited, credited)
        if collection == "exercises":
            attempt = ExerciseAttempt.objects.get(user=user, exercise=item)
            self.assertTrue(attempt.is_correct)
            self.assertEqual(attempt.exercise.uid, item.uid)
            self.assertEqual(attempt.answer, answer)
        return credited

    def test_cafe_answers_do_not_credit_unspoken_requests_or_replies(self):
        for order, required, forbidden in (
            (1, {"LX-00056"}, {"LX-00084", "LX-00285"}),
            (2, {"LX-00011"}, {"LX-00082", "LX-00084", "LX-00284", "LX-00285"}),
            (3, {"LX-00084"}, {"LX-00085", "LX-00086", "LX-00087", "LX-00284", "LX-00285"}),
            (4, {"LX-00058"}, {"LX-00285"}),
        ):
            item = PracticeItem.objects.get(lesson__slug=CAFE, order=order)
            with self.subTest(order=order):
                self.credit("practice", item, "Coffee, please." if order == 2 else item.answer,
                            required, forbidden, f"cafe-{order}")

    def test_quantity_answers_credit_the_actual_drink_or_food(self):
        for order, required, forbidden in (
            (1, {"LX-00062", "LX-00063", "LX-00011", "LX-00055"}, set()),
            (2, {"LX-00064", "LX-00055"}, {"LX-00083"}),
            (3, {"LX-00073", "LX-00056"}, {"LX-00083"}),
            (4, {"LX-00066", "LX-00056"}, {"LX-00083"}),
        ):
            item = PracticeItem.objects.get(lesson__slug=NUMBERS, order=order)
            with self.subTest(order=order):
                self.credit("practice", item, item.answer, required, forbidden, f"number-{order}")

    def test_family_translations_do_not_credit_unasked_family_questions(self):
        for order, required, forbidden in (
            (1, {"LX-00099"}, {"LX-00102", "LX-00103"}),
            (2, {"LX-00088"}, {"LX-00101", "LX-00103"}),
            (3, {"LX-00002", "LX-00039"}, {"LX-00101", "LX-00102", "LX-00103"}),
            (4, {"LX-00095", "LX-00278"}, {"LX-00101", "LX-00102", "LX-00103"}),
        ):
            item = PracticeItem.objects.get(lesson__slug=PHOTO, order=order)
            with self.subTest(order=order):
                self.credit("practice", item, item.answer, required, forbidden, f"photo-{order}")

    def test_possession_translations_do_not_credit_the_other_speakers_phrase(self):
        for order, required, forbidden in (
            (1, {"LX-00098", "LX-00015"}, {"LX-00104", "LX-00105"}),
            (2, {"LX-00088", "LX-00071"}, {"LX-00104", "LX-00105"}),
            (3, {"LX-00097", "LX-00104"}, {"LX-00105"}),
            (4, {"LX-00039", "LX-00057", "LX-00105"}, {"LX-00104"}),
        ):
            item = PracticeItem.objects.get(lesson__slug=POSSESSION, order=order)
            with self.subTest(order=order):
                self.credit("practice", item, item.answer, required, forbidden, f"owner-{order}")

    def test_recognition_and_transfer_credit_only_the_answered_skill(self):
        for serial, (uid, required, forbidden) in enumerate((
            ("EX-00025", {"LX-00055"}, {"LX-00082"}),
            ("EX-00026", {"LX-00281"}, {"LX-00285"}),
            ("EX-00027", {"LX-00282", "LX-00283"}, {"LX-00284", "LX-00285"}),
            ("EX-00034", {"LX-00002", "LX-00039"}, {"LX-00103"}),
            ("EX-00039", set(), {"LX-00097"}),
        )):
            item = Exercise.objects.get(uid=uid)
            with self.subTest(uid=uid):
                credited = self.credit("exercises", item, item.answer, required, forbidden, f"main-{serial}")
                if uid == "EX-00039":
                    self.assertEqual(credited, set(), "A grammatical suffix has no standalone lexical UID")


    def test_optional_review_targets_the_translated_skill_without_false_error_evidence(self):
        for slug, targets in (
            (CAFE, ((1, "EX-00024"), (2, "EX-00026"), (3, "EX-00022"), (4, "EX-00023"))),
            (NUMBERS, ((1, "EX-00030"), (2, "EX-00029"), (3, "EX-00031"), (4, "EX-00031"))),
            (PHOTO, ((1, "EX-00032"), (2, "EX-00033"), (3, "EX-00034"), (4, "EX-00037"))),
            (POSSESSION, ((1, "EX-00041"), (2, "EX-00039"), (3, "EX-00040"))),
        ):
            for order, expected_uid in targets:
                with self.subTest(slug=slug, order=order):
                    user = get_user_model().objects.create_user(
                        email=f"review-{slug}-{order}@example.test", password="Test-pass-123!")
                    self.client.force_login(user)
                    item = PracticeItem.objects.get(lesson__slug=slug, order=order)
                    before = timezone.now()
                    response = self.client.post(reverse("learning:request_practice_review", args=[item.pk]))
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["count"], 5)
                    row = MistakeReview.objects.get(user=user)
                    self.assertEqual(row.exercise.uid, expected_uid)
                    self.assertEqual(row.exercise.lesson_id, item.lesson_id)
                    self.assertGreaterEqual(row.due_at, before + timedelta(days=2))
                    self.assertLessEqual(row.due_at, timezone.now() + timedelta(days=2))
                    self.assertEqual((row.current_index, row.correct_count), (0, 0))
                    self.assertFalse(ExerciseAttempt.objects.filter(user=user).exists())
                    self.assertFalse(UnitProgress.objects.filter(user=user).exists())


class DeepA1IndependentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = get_user_model().objects.create_user(email="independent-deep-a1@example.test", password="Test-pass-123!")

    def setUp(self):
        self.client.force_login(self.user)

    def submit(self, slug, skill, answer, matches):
        url = reverse("learning:independent_check", args=[slug])
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        guide = page.context["guide"]
        data = {"action": "batch", "assistance": "no_help", "batch_token": page.context["batch_token"],
                "transfer_variant": str(page.context["transfer_variant"]),
                **{"answer_" + key: guide["tasks"][key]["model"]
                   for key in ("meaning", "writing", "transfer", "explain")}}
        data["answer_" + skill] = answer
        before = set(IndependentAttempt.objects.values_list("pk", flat=True))
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        saved = IndependentAttempt.objects.exclude(pk__in=before)
        self.assertEqual(saved.count(), 4)
        row = saved.get(skill=skill)
        self.assertEqual(row.submitted, answer)
        self.assertEqual(row.outcome, IndependentAttempt.Outcome.MODEL_MATCH if matches
                         else IndependentAttempt.Outcome.NEEDS_REVIEW)
        for key in ("transfer", "explain"):
            self.assertEqual(saved.get(skill=key).outcome, IndependentAttempt.Outcome.SELF_REPORTED)

    def test_tea_writing_recognizes_the_taught_polite_frames(self):
        for answer, matches in (("Tea, please.", True), ("A tea, please.", True),
                                ("I'd like a tea, please.", True), ("Can I have a tea, please?", True),
                                ("Can I have coffee, please?", False), ("I don't like tea.", False),
                                ("Can I tea, please?", False)):
            with self.subTest(answer=answer):
                self.submit(CAFE, "writing", answer, matches)

    def test_coffee_meaning_accepts_the_speakers_gender_without_changing_the_drink(self):
        for answer, matches in (("Я бы хотела кофе, пожалуйста.", True),
                                ("Я бы хотел кофе, пожалуйста.", True),
                                ("Я бы хотела чай, пожалуйста.", False),
                                ("Мне не нравится кофе.", False)):
            with self.subTest(answer=answer):
                self.submit(CAFE, "meaning", answer, matches)

    def test_two_teas_writing_preserves_number_plural_and_drink(self):
        for answer, matches in (("Can I have two teas, please?", True),
                                ("I'd like two teas, please.", True), ("Two teas, please.", True),
                                ("Can I have twelve teas, please?", False),
                                ("Two coffees, please.", False), ("Two tea, please.", False)):
            with self.subTest(answer=answer):
                self.submit(NUMBERS, "writing", answer, matches)

    def test_brother_writing_preserves_the_relation_and_owner(self):
        for answer, matches in (("That is my brother.", True), ("He is my brother.", True),
                                ("This is my brother.", True), ("He is your brother.", False),
                                ("This is my sister.", False), ("He is not my brother.", False)):
            with self.subTest(answer=answer):
                self.submit(PHOTO, "writing", answer, matches)

    def test_book_writing_keeps_toms_possession_and_the_apostrophe(self):
        for answer, matches in (("It is Tom's book.", True), ("That's Tom's book.", True),
                                ("This is Tom’s book.", True), ("This is Anna's book.", False),
                                ("This is Toms book.", False), ("This is Tom is book.", False),
                                ("This is not Tom's book.", False)):
            with self.subTest(answer=answer):
                self.submit(POSSESSION, "writing", answer, matches)
