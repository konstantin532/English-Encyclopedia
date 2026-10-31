"""Behavior regressions for the second editorial review of A1 lessons 1–4.

A key match is deliberately narrower than grammatical correctness: unmatched
free replies stay unverified, and transfer/explanation remain self reports.
"""
import json
from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.drills.models import Exercise, PracticeItem, loose_normalize
from apps.learning.mistake_review import variants_for
from apps.learning.models import IndependentAttempt, MistakeReview
from tests.runner import ensure_content

NOUNS = "a1-nouns-first-words"
BE = "a1-verb-be"
DETERMINERS = "a1-determiners-a-the-this-my"
HAVE = "a1-have-like-can-do"


class EditorialContractionSafetyTests(SimpleTestCase):
    def test_possessive_s_is_not_globally_expanded_to_is(self):
        self.assertNotEqual(loose_normalize("Anna's book"), loose_normalize("Anna is book"))
        self.assertNotEqual(loose_normalize("My name's Anna"), loose_normalize("My name is Anna"))
        self.assertEqual(loose_normalize("It's my book"), loose_normalize("It is my book"))


class EditorialAnswerKeyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def assert_answer(self, collection, item, submitted, expected):
        response = self.client.post(
            f"/api/{collection}/{item.pk}/check/",
            json.dumps({"answer": submitted}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["correct"], expected, submitted)
        if collection == "practice":
            self.assertEqual(data["assessment"], "model_match" if expected else "needs_review")
        elif item.stage == Exercise.Stage.TRANSFER:
            self.assertEqual(data["assessment"], "model_match" if expected else "needs_review")

    def test_book_transfer_preserves_both_ownership_and_newness(self):
        item = Exercise.objects.get(uid="EX-00004")
        for text in ("This is my book and it is new.", "This is my book and it's new.",
                     "It is my new book.", "It’s my new book."):
            with self.subTest(answer=text):
                self.assert_answer("exercises", item, text, True)
        for text in ("This is your new book.", "This is my old book.",
                     "This is not my new book.", "This is my book."):
            with self.subTest(answer=text):
                self.assert_answer("exercises", item, text, False)

    def test_room_transfer_accepts_reordered_thoughts_but_not_swapped_properties(self):
        item = Exercise.objects.get(uid="EX-00014")
        for text in ("That room is new. This room is big.",
                     "That room is new and this room is big."):
            with self.subTest(answer=text):
                self.assert_answer("exercises", item, text, True)
        for text in ("This room is new. That room is big.",
                     "That room is not new. This room is big.",
                     "That is new room. This big room is."):
            with self.subTest(answer=text):
                self.assert_answer("exercises", item, text, False)

    def test_name_translation_accepts_explicit_noun_contraction(self):
        item = PracticeItem.objects.get(lesson__slug=NOUNS, order=3)
        for text, correct in (("My name's Anna.", True), ("My name’s Anna.", True),
                              ("I'm Anna.", True), ("My name Anna.", False),
                              ("My name's Tom.", False), ("Your name is Anna.", False)):
            with self.subTest(answer=text):
                self.assert_answer("practice", item, text, correct)

    def test_water_translation_preserves_request_and_recipient(self):
        item = PracticeItem.objects.get(lesson__slug=HAVE, order=1)
        for text, correct in (("Can I have water, please?", True),
                              ("Can I have a water, please?", True),
                              ("Can you have water, please?", False),
                              ("Can I water, please?", False),
                              ("I have some water.", False),
                              ("Can I not have water, please?", False)):
            with self.subTest(answer=text):
                self.assert_answer("practice", item, text, correct)

    def test_cat_translation_preserves_present_possession_and_owner(self):
        item = PracticeItem.objects.get(lesson__slug=HAVE, order=3)
        for text, correct in (("I have a cat.", True),
                              ("I got a cat.", False), ("You have a cat.", False),
                              ("I haven't got a cat.", False), ("I have cat.", False)):
            with self.subTest(answer=text):
                self.assert_answer("practice", item, text, correct)

    def test_optional_future_vocabulary_stays_ungraded_under_the_current_contract(self):
        # R16/R17 key expansions remain open: week2 does not introduce some/get.
        # A valid but unlisted free answer must be retained for review, not
        # asserted to be a grammatical error. Do not add a vocabulary whitelist.
        for order, replies in ((1, ("Can I have some water, please?",)),
                               (3, ("I have got a cat.", "I've got a cat.", "I’ve got a cat."))):
            item = PracticeItem.objects.get(lesson__slug=HAVE, order=order)
            for reply in replies:
                with self.subTest(answer=reply):
                    self.assert_answer("practice", item, reply, False)

    def test_room_translation_tracks_room_and_not_living_room(self):
        item = PracticeItem.objects.get(lesson__slug=DETERMINERS, order=2)
        self.assertIn("LX-00007", set(item.units.values_list("uid", flat=True)))
        self.assertNotIn("LX-00484", set(item.units.values_list("uid", flat=True)))


class EditorialIndependentAndReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user = User.objects.create_user(email="editorial-review@example.test", password="ExamplePassword123!")

    def setUp(self):
        self.client.force_login(self.user)

    def independent(self, slug, skill, text, matches):
        url = reverse("learning:independent_check", args=[slug])
        page = self.client.get(url)
        self.assertEqual(page.status_code, 200)
        guide = page.context["guide"]
        form = {"action": "batch", "assistance": "no_help",
                "batch_token": page.context["batch_token"],
                "transfer_variant": str(page.context["transfer_variant"]),
                **{"answer_" + key: guide["tasks"][key]["model"]
                   for key in ("meaning", "writing", "transfer", "explain")}}
        form["answer_" + skill] = text
        before = set(IndependentAttempt.objects.values_list("pk", flat=True))
        response = self.client.post(url, form)
        self.assertEqual(response.status_code, 200)
        saved = IndependentAttempt.objects.exclude(pk__in=before)
        self.assertEqual(saved.count(), 4)
        attempt = saved.get(skill=skill)
        self.assertEqual(attempt.submitted, text)
        self.assertEqual(attempt.outcome, IndependentAttempt.Outcome.MODEL_MATCH if matches
                         else IndependentAttempt.Outcome.NEEDS_REVIEW)
        for free_skill in ("transfer", "explain"):
            self.assertEqual(saved.get(skill=free_skill).outcome, IndependentAttempt.Outcome.SELF_REPORTED)

    def test_home_writing_accepts_both_taught_location_forms(self):
        for text, matches in (("I am home.", True), ("I'm home.", True),
                              ("I am at home.", True), ("I'm at home.", True),
                              ("I home.", False), ("I am not home.", False),
                              ("You are home.", False)):
            with self.subTest(answer=text):
                self.independent(BE, "writing", text, matches)

    def test_friend_meaning_preserves_person_and_owner(self):
        for text, matches in (("Ты моя подруга.", True), ("Вы моя подруга.", True),
                              ("Ты мой друг.", True), ("Я твой друг.", False),
                              ("Ты не мой друг.", False)):
            with self.subTest(answer=text):
                self.independent(BE, "meaning", text, matches)

    def test_coffee_meaning_accepts_address_and_translation_variants(self):
        for text, matches in (("Вам нравится кофе?", True), ("Ты любишь кофе?", True),
                              ("Вы любите кофе?", True), ("Тебе нравится кофе?", True),
                              ("Тебе не нравится кофе?", False), ("Мне нравится кофе.", False)):
            with self.subTest(answer=text):
                self.independent(HAVE, "meaning", text, matches)

    def test_delayed_cards_grade_the_requested_order_and_serve_their_own_reason(self):
        # Coordinates are review-variant slots under stable source exercise UIDs.
        for uid, slot, expected_answer in (
            ("EX-00019", 0, "Do you have a phone?"),
            ("EX-00019", 2, "Do you have a cat?"),
            ("EX-00020", 0, "Do you have a book?"),
            ("EX-00020", 4, "Do you have a friend?"),
            ("EX-00021", 3, "Can I have water, please?"),
        ):
            exercise = Exercise.objects.get(uid=uid)
            card = variants_for(exercise)[slot]
            self.assertEqual(card[2][card[3]], expected_answer)
            self.assertEqual(len(card), 5, "Ambiguous cards need their own contextual explanation")
            self.assertTrue(card[4].strip())
            for choice in range(3):
                with self.subTest(uid=uid, slot=slot, choice=choice):
                    review, _ = MistakeReview.objects.update_or_create(
                        user=self.user, exercise=exercise,
                        defaults={"due_at": timezone.now() - timedelta(seconds=1),
                                  "current_index": slot, "correct_count": 0, "completed_at": None},
                    )
                    response = self.client.post(reverse("learning:mistake_review"),
                                                {"review_id": review.pk, "index": slot, "choice": choice})
                    self.assertEqual(response.status_code, 200)
                    result = response.context["answer_result"]
                    self.assertEqual(result["correct"], choice == card[3])
                    self.assertEqual(result["model"], expected_answer)
                    self.assertEqual(result["reason"], card[4])
