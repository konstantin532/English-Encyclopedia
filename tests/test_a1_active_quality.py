"""Учебная последовательность и канон дополнительной практики A1."""
from django.test import TestCase
from django.urls import reverse

from apps.core.a1_active import active_topics
from apps.curriculum.models import Level
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from apps.publishing.audit import is_known, text_tokens, vocab_until
from tests.runner import ensure_content


class ActiveA1ContentQualityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_english_models_use_vocabulary_known_in_their_week(self):
        level = Level.objects.get(code="A1")
        for number, topic in active_topics().items():
            vocab = vocab_until(level, topic["week"])
            samples = [("dialogue", line[1]) for line in topic["dialogue"]]
            samples += [(key, topic[key]) for key in ("answer", "transfer_example")]
            samples += [("alternative", text) for text in topic["alternatives"]]
            samples += [("repair", topic["repair"][key]) for key in ("wrong", "correct")]
            samples += [("repair alternative", text) for text in topic["repair"].get("alternatives", [])]
            samples += [("mission", item["example"]) for item in topic["missions"]]
            samples += [("twist", item["example"]) for item in topic["twists"]]
            # English response options are checked; Russian explanations are not vocabulary tasks.
            samples += [("option", text) for text in topic["options"]
                        if text.isascii()]
            for field, text in samples:
                with self.subTest(number=number, field=field, text=text):
                    # Lesson 18 deliberately spells names by individual alphabet letters.
                    unknown = {word for word in text_tokens(text)
                               if not is_known(word, vocab)
                               and not (number == 18 and word.isascii() and len(word) == 1)}
                    self.assertEqual(unknown, set())

    def test_six_mission_models_are_distinct_within_each_lesson(self):
        for number, topic in active_topics().items():
            models = [" ".join(m["example"].lower().split()).rstrip(".!?")
                      for m in topic["missions"]]
            self.assertEqual(len(set(models)), 6, f"урок {number}: {models}")

    def test_mia_gets_up_at_five(self):
        mia = [line[1] for line in active_topics()[12]["dialogue"] if line[0] == "Mia"]
        self.assertIn("At five.", mia)
        self.assertNotIn("At seven.", mia)

    def test_toms_mother_has_her_own_age(self):
        self.assertIn("She's fifty.", [line[1] for line in active_topics()[7]["dialogue"]])

    def test_early_quiz_options_use_plain_russian(self):
        self.assertFalse(any("present simple" in option.lower()
                             for option in active_topics()[4]["options"]))

    def test_in_is_introduced_before_the_time_lesson(self):
        unit = LexicalUnit.objects.get(lemma="in")
        self.assertEqual(unit.week.number, 6)
        self.assertTrue(Lesson.objects.get(slug="a1-time-at-seven").units.filter(pk=unit.pk).exists())

    def test_renamed_source_lesson_has_no_dead_practice_invitation(self):
        lesson = Lesson.objects.get(level__code="A1", order=18)
        lesson.slug = "renamed-a1-spelling"
        lesson.save(update_fields=["slug"])
        response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
        self.assertNotContains(response, 'class="section a1-active-invite"')
