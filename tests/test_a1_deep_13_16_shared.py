"""Behavioral prerequisite, local-key and contextual-marker checks for A1 13–16."""
from datetime import timedelta
from html.parser import HTMLParser
import re
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from apps.drills.models import Exercise
from apps.learning.understanding import understanding_bank
from apps.learning.mistake_review import variants_for
from apps.learning.models import IndependentAttempt, UnitProgress, MistakeReview
from apps.lessons.models import Lesson
from apps.poems.models import Poem
from tests.runner import ensure_content
from apps.publishing.audit import vocab_until,is_known,text_tokens

SLUGS=('a1-he-she-works','a1-jobs-what-do-you-do','a1-where-is-prepositions','a1-directions-turn-left')

class Shared1316Tests(TestCase):
    @classmethod
    def setUpTestData(cls):ensure_content()

    def test_cold_models_use_known_lexical_meanings(self):
        for slug in SLUGS:
            lesson=Lesson.objects.select_related('level','week').get(slug=slug)
            known=vocab_until(lesson.level,lesson.week.number);g=understanding_bank()[slug]
            for task in (g['tasks']['writing'],g['tasks']['transfer'],*g['transfer_variants']):
                with self.subTest(slug=slug,model=task['model']):
                    self.assertEqual([t for t in text_tokens(task['model']) if not is_known(t,known)],[])
                    # Proper-name Park Street does not teach the common noun park.
                    if lesson.week.number < 10:self.assertNotRegex(task['model'],r'\bthe park\b')

    def test_all_compiled_correct_micro_answers_use_known_words(self):
        for slug in SLUGS:
            lesson=Lesson.objects.select_related('level','week').get(slug=slug)
            known=vocab_until(lesson.level,lesson.week.number)
            for ex in lesson.exercises.all():
                cards=variants_for(ex)
                self.assertEqual(len(cards),5)
                self.assertEqual(len({c[0] for c in cards}),5)
                for slot,card in enumerate(cards):
                    with self.subTest(uid=ex.uid,slot=slot):
                        model=card[2][card[3]]
                        self.assertEqual([t for t in text_tokens(model) if not is_known(t,known)],[])
                        if lesson.week.number<10:self.assertNotRegex(model,r'\bthe park\b')

    def _writing(self,slug,good,bad):
        user=get_user_model().objects.create_user(email=slug+'@example.test',password='Example-pass-123!')
        self.client.force_login(user);lesson=Lesson.objects.get(slug=slug)
        url=reverse('learning:independent_check',args=[slug])
        for answer in (*good,*bad):
            with self.subTest(answer=answer):
                page=self.client.get(url);g=page.context['guide']
                form={'action':'batch','assistance':'no_help','batch_token':page.context['batch_token'],
                      'transfer_variant':str(page.context['transfer_variant']),
                      **{'answer_'+k:g['tasks'][k]['model'] for k in ('meaning','writing','transfer','explain')}}
                form['answer_writing']=answer
                response=self.client.post(url,form);self.assertEqual(response.status_code,200)
                attempt=IndependentAttempt.objects.filter(user=user,lesson=lesson,skill='writing').latest('pk')
                expected=IndependentAttempt.Outcome.MODEL_MATCH if answer in good else IndependentAttempt.Outcome.NEEDS_REVIEW
                self.assertEqual(attempt.outcome,expected)
        self.assertFalse(UnitProgress.objects.filter(user=user).exists())

    def test_near_is_valid_for_unspecified_nearby_bank_but_not_inside_or_negated(self):
        self._writing(SLUGS[2],('The bank is next to the cafe.','The bank is near the cafe.','The cafe is near the bank.','The cafe is next to the bank.'),
            ('The bank is in the cafe.','The bank is not near the cafe.','The bank near the cafe.'))

    def test_school_work_place_variants_do_not_swap_person_or_work_for_be(self):
        self._writing(SLUGS[1],('I work at a school.','I work in a school.','I work at the school.','I work in the school.','I work at school.'),
            ('He works at a school.','I do not work at a school.','I am work at a school.','I work a school at.'))

    def test_between_review_disambiguates_grammatical_neighboring_option_and_keeps_keys(self):
        user=get_user_model().objects.create_user(email='micro1316@example.test',password='Example-pass-123!');self.client.force_login(user)
        exercise=Exercise.objects.get(lesson__slug=SLUGS[2],order=5)
        for slot,card in enumerate(variants_for(exercise)):
            self.assertEqual(card[3],(-slot)%3)
            self.assertIn('between',card[0])
            for choice in range(3):
                with self.subTest(slot=slot,choice=choice):
                    review,_=MistakeReview.objects.update_or_create(user=user,exercise=exercise,defaults={
                        'due_at':timezone.now()-timedelta(seconds=1),'current_index':slot,'correct_count':0,'completed_at':None})
                    response=self.client.post(reverse('learning:mistake_review'),{'review_id':review.pk,'index':slot,'choice':choice})
                    result=response.context['answer_result'];self.assertEqual(result['correct'],choice==card[3])
                    self.assertEqual(result['reason'],card[4]);self.assertIn('грамматически правильной',result['reason'])

    def test_poem_spatial_on_label_is_place_and_all_targets_have_a_real_word(self):
        response=self.client.get(reverse('stories:poem',args=[4]));self.assertEqual(response.status_code,200)
        rows=self._labels(response.content.decode())
        on=[r for r in rows if r[0]=='on'];self.assertTrue(on)
        self.assertTrue(all(cat=='P'and label.endswith('Место') for _,cat,label in on),on)
        poem=Poem.objects.get(number=4);plain=re.sub(r'\[[A-Z]\d+\]|\[/\]','',poem.body).lower()
        for unit in response.context['targets']:
            with self.subTest(uid=unit.uid):self.assertIn(unit.lemma.lower(),plain)

    @staticmethod
    def _labels(html):
        class Parser(HTMLParser):
            def __init__(self):super().__init__();self.current=None;self.rows=[]
            def handle_starttag(self,tag,attrs):
                if tag=='span':self.current=dict(attrs)
            def handle_endtag(self,tag):
                if tag=='span':self.current=None
            def handle_data(self,text):
                if self.current and self.current.get('data-cat') and text.strip():
                    self.rows.append((text.strip(),self.current.get('data-cat'),self.current.get('data-label','')))
        p=Parser();p.feed(html);return p.rows

    def test_week_twister_right_door_is_adjective_and_on_is_spatial(self):
        response=self.client.get(reverse('curriculum:week',args=['a1',8]));self.assertEqual(response.status_code,200)
        rows=self._labels(response.content.decode())
        self.assertTrue(any(word=='right'and cat=='J'and label.endswith('Оценка') for word,cat,label in rows),rows)
        self.assertFalse(any(word=='on'and label.endswith('Время') for word,cat,label in rows),rows)

    def test_story_possessive_suffix_is_separate_and_key_to_is_relationship(self):
        response=self.client.get(reverse('stories:detail',args=[3]));self.assertEqual(response.status_code,200)
        rows=self._labels(response.content.decode())
        self.assertTrue(any(word=="'s"and cat=='T'and label.endswith('Притяжательные детерминативы')for word,cat,label in rows),rows)
        self.assertTrue(any(word=='to'and cat=='P'and label.endswith('Абстрактные отношения')for word,cat,label in rows),rows)
