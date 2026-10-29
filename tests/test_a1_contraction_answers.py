"""A1 conversational models must preserve both valid written spellings."""
import json

from django.test import TestCase

from apps.drills.models import Exercise, PracticeItem
from apps.learning.understanding import get_guide, model_agreement
from tests.runner import ensure_content


class A1ContractionAnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def check_answer(self, collection, item, answer, correct=True):
        response = self.client.post(
            f"/api/{collection}/{item.pk}/check/",
            json.dumps({"answer": answer}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["correct"], correct, answer)

    def test_edited_exercises_accept_both_forms_and_reject_changed_meaning(self):
        cases = (
            ("EX-00004", "This is my book. It is new.",
             "This is my book. It's new.", "This is my book. It's old."),
            ("EX-00043", "We are a big family. Their house is big.",
             "We're a big family. Their house is big.", "We're a big family. Our house is big."),
            ("EX-00137", "It is for my friend in Russia.",
             "It's for my friend in Russia.", "It's for my friend in Canada."),
            ("EX-00157", "Where is the train station?",
             "Where's the train station?", "Where's the bus station?"),
            ("EX-00027", "I would like a sandwich and a juice, please.",
             "I'd like a sandwich and a juice, please.", "I would like coffee, please."),
            ("EX-00035", "This is my sister. She is twelve.",
             "This is my sister. She's twelve.", "This is my sister. She is ten."),
            ("EX-00054", "That is expensive!", "That's expensive!", "That's cheap!"),
            ("EX-00161", "I am from Russia. I can speak English.",
             "I'm from Russia. I can speak English.", "I'm from Russia. I can't speak English."),
        )
        for uid, full, short, wrong in cases:
            item = Exercise.objects.get(uid=uid)
            for answer in (full, short):
                with self.subTest(uid=uid, answer=answer):
                    self.check_answer("exercises", item, answer)
            with self.subTest(uid=uid, wrong=wrong):
                self.check_answer("exercises", item, wrong, False)

    def test_edited_translations_accept_full_and_short_forms(self):
        cases = (
            (1, 2, "Good morning! What is your name?", "Good morning! What's your name?"),
            (3, 2, "That is your room.", "That's your room."),
            (3, 4, "It is not my box.", "It isn't my box."),
            (5, 2, "I would like a coffee, please.", "I'd like a coffee, please."),
            (6, 4, "I would like five cookies.", "I'd like five cookies."),
            (7, 1, "Who is this?", "Who's this?"),
            (8, 4, "Here is your photo, Mia.", "Here's your photo, Mia."),
            (10, 2, "It is two dollars.", "It's two dollars."),
            (10, 4, "They are cheap!", "They're cheap!"),
            (12, 1, "It is seven o'clock.", "It's seven o'clock."),
            (16, 4, "Excuse me, where is the bank?", "Excuse me, where's the bank?"),
            (18, 2, "What is your phone number?", "What's your phone number?"),
            (23, 3, "I do not know.", "I don't know."),
            (24, 2, "What is the address?", "What's the address?"),
            (25, 3, "I cannot play the guitar.", "I can't play the guitar."),
            (26, 2, "Because I cannot sleep.", "Because I can't sleep."),
            (28, 1, "My name is Anna. I am from Russia.", "My name is Anna. I'm from Russia."),
            (28, 3, "Where is the bank? It is on the right.", "Where's the bank? It's on the right."),
            (28, 4, "I do not know, but I can ask.", "I don't know, but I can ask."),
        )
        for lesson, order, full, short in cases:
            item = PracticeItem.objects.get(lesson__level__code="A1", lesson__order=lesson, order=order)
            for answer in (full, short):
                with self.subTest(lesson=lesson, order=order, answer=answer):
                    self.check_answer("practice", item, answer)

    def test_edited_understanding_writing_preserves_both_spellings(self):
        cases = (
            ("a1-how-much-prices", "It is three dollars.", "It's three dollars.", "It is two dollars."),
            ("a1-why-because", "Because I am tired.", "Because I'm tired.", "Because I am not tired."),
        )
        for slug, full, short, wrong in cases:
            task = get_guide(slug)["tasks"]["writing"]
            for answer in (full, short):
                with self.subTest(slug=slug, answer=answer):
                    self.assertTrue(model_agreement(task, answer))
            self.assertFalse(model_agreement(task, wrong))
