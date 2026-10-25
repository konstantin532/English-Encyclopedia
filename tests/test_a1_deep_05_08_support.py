"""Prerequisites and real contextual delayed-review feedback for A1 5–8."""
from datetime import timedelta
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.drills.models import Exercise
from apps.learning.mistake_review import variants_for
from apps.learning.models import MistakeReview
from apps.learning.understanding import understanding_bank
from apps.lessons.models import Lesson
from apps.poems.models import Poem
from apps.publishing.audit import is_known, text_tokens, vocab_until
from tests.runner import ensure_content


class DeepA1SupportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_cold_transfer_uses_known_words_or_an_explicitly_prepared_whole_phrase(self):
        guides = understanding_bank()
        for slug in ('a1-cafe-order', 'a1-numbers-1-20', 'a1-family-photo', 'a1-family-possession'):
            lesson = Lesson.objects.select_related('level', 'week').get(slug=slug)
            vocabulary = vocab_until(lesson.level, lesson.week.number)
            guide = guides[slug]
            # A translated ready-made expression can precede its full grammar.
            # Only that complete expression is allowed, not all its words globally.
            prepared = {step['example_en'] for step in guide['steps']}
            for task in (guide['tasks']['transfer'], *guide['transfer_variants']):
                if task['model'] in prepared:
                    continue
                with self.subTest(slug=slug, model=task['model']):
                    self.assertEqual([t for t in text_tokens(task['model']) if not is_known(t, vocabulary)], [])

    def test_poem_targets_are_actually_present_and_the_page_serves_the_same_units(self):
        poem = Poem.objects.get(number=2)
        words = {token.lower() for token in text_tokens(poem.body)}
        targets = list(poem.target_units.all())
        self.assertEqual({unit.lemma.lower() for unit in targets} - words, set())
        response = self.client.get(reverse('stories:poem', args=[poem.number]))
        self.assertEqual(response.status_code, 200)
        served = {unit.uid for unit in response.context['targets']}
        self.assertEqual(served, {unit.uid for unit in targets})
        class AgeMarkers(HTMLParser):
            def __init__(self):
                super().__init__()
                self.current = None
                self.labels = []
            def handle_starttag(self, tag, attrs):
                if tag == 'span':
                    self.current = dict(attrs)
            def handle_data(self, data):
                if data.strip() == 'ten' and self.current and self.current.get('data-cat') == 'N':
                    self.labels.append(self.current.get('data-label'))
            def handle_endtag(self, tag):
                if tag == 'span':
                    self.current = None
        parser = AgeMarkers()
        parser.feed(response.content.decode())
        self.assertGreaterEqual(len(parser.labels), 3)
        self.assertTrue(all(label.endswith('Возраст') for label in parser.labels), parser.labels)

    def test_echo_distractors_get_card_specific_feedback_for_the_required_question_order(self):
        user = get_user_model().objects.create_user(email='deep-card-context@example.test', password='Test-pass-123!')
        self.client.force_login(user)
        for uid, slot in (('EX-00032', 1), ('EX-00034', 0), ('EX-00034', 3)):
            exercise = Exercise.objects.get(uid=uid)
            card = variants_for(exercise)[slot]
            # An explicit local explanation must distinguish the target question
            # from a possible echo question. The actual view must serve that reason.
            self.assertEqual(len(card), 5)
            for choice in range(3):
                with self.subTest(uid=uid, slot=slot, choice=choice):
                    review, _ = MistakeReview.objects.update_or_create(
                        user=user, exercise=exercise,
                        defaults={'due_at': timezone.now() - timedelta(seconds=1),
                                  'current_index': slot, 'correct_count': 0, 'completed_at': None})
                    response = self.client.post(reverse('learning:mistake_review'),
                                                {'review_id': review.pk, 'index': slot, 'choice': choice})
                    self.assertEqual(response.status_code, 200)
                    result = response.context['answer_result']
                    self.assertEqual(result['correct'], choice == card[3])
                    self.assertEqual(result['model'], card[2][card[3]])
                    self.assertEqual(result['reason'], card[4])
