"""Истории A1+ (№6–11): длина, знакомые слова, новые слова, сюжетные задания."""
from django.test import TestCase

from apps.curriculum.registry import LEVEL_BY_CODE
from apps.publishing.audit import (
    AuditReport,
    audit_stories_and_poems,
    is_known,
    text_tokens,
    vocab_until,
)
from apps.stories.models import Story
from apps.taxonomy.markup import strip_markup
from tests.runner import ensure_content


class A1PlusStoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.stories = list(Story.objects.filter(level__code="A1+").select_related("level", "week")
                           .prefetch_related("new_units"))

    def test_six_stories_are_published_on_planned_weeks(self):
        self.assertEqual([(s.number, s.week.number) for s in self.stories],
                         [(6, 2), (7, 6), (8, 8), (9, 10), (10, 14), (11, 16)])
        self.assertTrue(all(s.is_published for s in self.stories))

    def test_length_known_share_and_new_words(self):
        low, high = LEVEL_BY_CODE["A1+"].story_words
        for story in self.stories:
            with self.subTest(story=story.number):
                tokens = text_tokens(story.body)
                self.assertTrue(low <= len(tokens) <= high, len(tokens))
                new = list(story.new_units.all())
                self.assertTrue(1 <= len(new) <= 5)
                for unit in new:
                    self.assertEqual(unit.internal_level.code, "A1+")
                    self.assertLessEqual(unit.week.number, story.week.number)
                known = vocab_until(story.level, story.week.number, exclude_ids=[u.pk for u in new])
                unknown = [t for t in tokens if not is_known(t, known)]
                self.assertGreaterEqual(1 - len(unknown) / len(tokens), 0.95)

    def test_audit_has_no_story_errors(self):
        r = AuditReport()
        audit_stories_and_poems(r)
        own = [e for e in r.errors if any(e.startswith(f"История {n}:") for n in range(6, 12))]
        self.assertEqual(own, [])

    def test_tasks_quote_the_story(self):
        for story in self.stories:
            plain = " ".join(strip_markup(line["text"]) for line in story.script)
            with self.subTest(story=story.number):
                self.assertIn("music", story.script[0])
                self.assertEqual(len(story.phrase_hunt), 5)
                for item in story.phrase_hunt:
                    self.assertIn(item["phrase"], plain)
                self.assertGreaterEqual(len(story.questions), 5)
                self.assertEqual(len(story.retell_words), 5)

    def test_each_story_ends_with_a_question(self):
        for story in self.stories:
            with self.subTest(story=story.number):
                self.assertTrue(strip_markup(story.script[-1]["text"]).rstrip("”").endswith("?"))

    def test_past_forms_are_forms_not_new_words(self):
        from apps.lexicon.models import LexicalUnit

        for lemma, form in (("be", "was"), ("be", "were"), ("go", "went"), ("have", "had"), ("see", "saw")):
            unit = LexicalUnit.objects.get(lemma=lemma, unit_type="word")
            self.assertIn(form, unit.forms, lemma)
        self.assertFalse(LexicalUnit.objects.filter(lemma__in=["was", "went", "saw", "found"]).exists())
