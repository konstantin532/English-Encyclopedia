"""Real prerequisite, answer, review and contextual-marker checks for A1 9–12."""
from datetime import timedelta
import json
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.curriculum.models import TongueTwister
from apps.drills.models import Exercise
from apps.learning.mistake_review import variants_for
from apps.learning.models import IndependentAttempt, MistakeReview, UnitProgress
from apps.learning.understanding import understanding_bank
from apps.lessons.models import Lesson
from apps.lexicon.phonetics import IPA_OF_HINT
from apps.poems.models import Poem
from apps.publishing.audit import is_known, text_tokens, vocab_until
from tests.runner import ensure_content

SLUGS = ('a1-there-is-some', 'a1-how-much-prices', 'a1-present-simple-i-you', 'a1-time-at-seven')


class SharedDeepA10912Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_cold_transfer_models_use_vocabulary_available_at_the_week(self):
        for slug in SLUGS:
            lesson = Lesson.objects.select_related('level', 'week').get(slug=slug)
            vocabulary = vocab_until(lesson.level, lesson.week.number)
            guide = understanding_bank()[slug]
            for task in (guide['tasks']['writing'], guide['tasks']['transfer'], *guide['transfer_variants']):
                with self.subTest(slug=slug, model=task['model']):
                    self.assertEqual([t for t in text_tokens(task['model']) if not is_known(t, vocabulary)], [])

    def test_micro_correct_answers_use_available_vocabulary(self):
        for slug in SLUGS:
            lesson = Lesson.objects.select_related('level', 'week').get(slug=slug)
            vocabulary = vocab_until(lesson.level, lesson.week.number)
            for exercise in lesson.exercises.all():
                for slot, card in enumerate(variants_for(exercise)):
                    with self.subTest(uid=exercise.uid, slot=slot):
                        self.assertEqual([t for t in text_tokens(card[2][card[3]]) if not is_known(t, vocabulary)], [])

    def test_independent_price_accepts_equivalent_full_forms_and_preserves_meaning(self):
        user = get_user_model().objects.create_user(email='deep-price-shared@example.test', password='Example-pass-123!')
        self.client.force_login(user)
        lesson = Lesson.objects.get(slug='a1-how-much-prices')
        url = reverse('learning:independent_check', args=[lesson.slug])
        good = ('It is three dollars.', "It's three dollars.", 'That is three dollars.', "That's three dollars.",
                'It is 3 dollars.', "It's 3 dollars.", 'That is 3 dollars.', "That's 3 dollars.")
        bad = ('It is four dollars.', 'It is not three dollars.', 'Is it three dollars?',
               'It three dollars is.', 'That is three dollar.', 'You are three dollars.')
        for answer in (*good, *bad):
            with self.subTest(answer=answer):
                page = self.client.get(url)
                guide = page.context['guide']
                form = {'action': 'batch', 'assistance': 'no_help',
                        'batch_token': page.context['batch_token'],
                        'transfer_variant': str(page.context['transfer_variant']),
                        **{'answer_' + key: guide['tasks'][key]['model'] for key in ('meaning','writing','transfer','explain')}}
                form['answer_writing'] = answer
                response = self.client.post(url, form)
                self.assertEqual(response.status_code, 200)
                attempt = IndependentAttempt.objects.filter(user=user, lesson=lesson, skill='writing').latest('pk')
                self.assertEqual(attempt.submitted, answer)
                self.assertEqual(attempt.outcome, IndependentAttempt.Outcome.MODEL_MATCH if answer in good else IndependentAttempt.Outcome.NEEDS_REVIEW)
        self.assertFalse(UnitProgress.objects.filter(user=user).exists())

    def test_poem_clock_and_work_labels_reflect_their_contextual_functions(self):
        poem = Poem.objects.get(number=3)
        response = self.client.get(reverse('stories:poem', args=[3]))
        self.assertEqual(response.status_code, 200)
        class Labels(HTMLParser):
            def __init__(self):
                super().__init__(); self.span = None; self.rows = []
            def handle_starttag(self, tag, attrs):
                if tag == 'span': self.span = dict(attrs)
            def handle_data(self, data):
                if self.span and data.strip() in ('Ten', 'work', 'in'):
                    self.rows.append((data.strip(), self.span.get('data-cat'), self.span.get('data-label','')))
            def handle_endtag(self, tag):
                if tag == 'span': self.span = None
        parser = Labels(); parser.feed(response.content.decode())
        times = [r for r in parser.rows if r[0]=='Ten']; jobs = [r for r in parser.rows if r[0]=='work']
        self.assertTrue(times); self.assertTrue(jobs)
        particles = [r for r in parser.rows if r[0]=='in']
        self.assertTrue(particles)
        for word, category, suffix, records in (
            ('Ten','N','Время на часах',times),
            ('work','S','Работа, учёба, общение',jobs),
            ('in','X','Частицы фразовых глаголов: направление',particles)):
            with self.subTest(contextual_word=word):
                self.assertTrue(all(cat==category and label.endswith(suffix) for _,cat,label in records),records)
        # This lexical UID is only the verb "to do a job"; the poem contains its noun counterpart.
        with self.subTest(contextual_word='verb lexical target'):
            self.assertNotIn('LX-00128', {u.uid for u in response.context['targets']})
        # Removing the unrelated glossary link must not remove a gap or change its solution.
        self.assertEqual(sum(r['gap'] is not None for r in response.context['gapped']),len(poem.gaps))
        self.assertEqual([g['word'] for g in poem.gaps], ['five','seven','twelve','time','bed'])

    def test_twister_declared_simple_focus_sounds_occur_in_its_ipa(self):
        twister = TongueTwister.objects.get(number=5)
        self.assertTrue(twister.focus_sounds)
        for hint in twister.focus_sounds:
            sound = IPA_OF_HINT[hint]
            with self.subTest(hint=hint):
                self.assertIn(sound, twister.ipa)

    def test_all_five_milk_question_contexts_keep_rotated_keys_and_real_feedback(self):
        user = get_user_model().objects.create_user(email='micro-shared@example.test', password='Example-pass-123!')
        self.client.force_login(user)
        exercise = Exercise.objects.get(lesson__slug='a1-there-is-some', order=1)
        cards = variants_for(exercise)
        self.assertEqual(len(cards),5)
        self.assertEqual(len({r[0] for r in cards}),5)
        for slot, card in enumerate(cards):
            self.assertEqual(card[3],(-slot)%3)
            for choice in range(3):
                with self.subTest(slot=slot,choice=choice):
                    review,_=MistakeReview.objects.update_or_create(user=user,exercise=exercise,
                        defaults={'due_at':timezone.now()-timedelta(seconds=1),'current_index':slot,'correct_count':0,'completed_at':None})
                    response=self.client.post(reverse('learning:mistake_review'),{'review_id':review.pk,'index':slot,'choice':choice})
                    self.assertEqual(response.status_code,200)
                    result=response.context['answer_result']
                    self.assertEqual(result['correct'],choice==card[3])
                    self.assertEqual(result['model'],card[2][card[3]])
                    self.assertEqual(result['reason'],card[4])

    def test_poem_gap_api_still_checks_the_five_original_words_without_vocabulary_progress(self):
        user = get_user_model().objects.create_user(email='poem-gap-shared@example.test', password='Example-pass-123!')
        self.client.force_login(user)
        for index, word in enumerate(('five', 'seven', 'twelve', 'time', 'bed')):
            for submitted, expected in ((word, True), ('wrong', False)):
                with self.subTest(index=index, submitted=submitted):
                    response = self.client.post(reverse('api:check_poem_gap', args=[3,index]),
                        json.dumps({'answer':submitted}),content_type='application/json')
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response.json()['correct'],expected)
        self.assertFalse(UnitProgress.objects.filter(user=user).exists())

    def test_poem_three_prepares_its_chunks_and_other_intro_text_stays_the_same(self):
        class Intro(HTMLParser):
            def __init__(self):
                super().__init__(); self.header=False; self.in_p=False; self.text=[]; self.paragraphs=[]
            def handle_starttag(self, tag, attrs):
                if tag=='header' and 'page-head' in dict(attrs).get('class','').split(): self.header=True
                if self.header and tag=='p': self.in_p=True; self.text=[]
            def handle_data(self, text):
                if self.in_p: self.text.append(text)
            def handle_endtag(self, tag):
                if self.in_p and tag=='p': self.paragraphs.append(''.join(self.text)); self.in_p=False
                if tag=='header': self.header=False
        def intro(poem):
            response=self.client.get(reverse('stories:poem',args=[poem.number]))
            self.assertEqual(response.status_code,200)
            parsed=Intro();parsed.feed(response.content.decode())
            return next(text for text in parsed.paragraphs if text.startswith(poem.theme_ru))
        poem=Poem.objects.get(number=3)
        prepared=intro(poem)
        for pairing in ('go to work — идти на работу','coffee again — снова кофе','comes in — входит'):
            self.assertIn(pairing,prepared)
        self.assertNotIn('не вводит новых слов',prepared)
        self.assertIn('для понимания',prepared)
        # Other-level route is made renderable only in this transactional test;
        # no unpublished A1+ text is represented as actually reviewed content.
        next_level=Poem.objects.filter(level__code='A1+').first()
        self.assertIsNotNone(next_level)
        next_level.is_published=True;next_level.body='[T8]I[/] [D1]am[/] [A3]here[/].';next_level.save(update_fields=['is_published','body'])
        for other in (Poem.objects.get(number=2),next_level):
            self.assertEqual(intro(other),f'{other.theme_ru}. Рифма {other.rhyme_scheme}. Стихотворение не вводит новых слов: оно тренирует произношение на знакомых.')

    def test_water_transfer_model_is_a_known_question_plus_request_and_stays_self_reported(self):
        user=get_user_model().objects.create_user(email='water-shared@example.test',password='Example-pass-123!')
        self.client.force_login(user)
        lesson=Lesson.objects.select_related('level','week').get(slug='a1-there-is-some')
        url=reverse('learning:independent_check',args=[lesson.slug])
        page=self.client.get(url);guide=page.context['guide'];task=guide['tasks']['transfer'];vocabulary=vocab_until(lesson.level,lesson.week.number)
        self.assertEqual([t for t in text_tokens(task['model']) if not is_known(t,vocabulary)],[])
        question,request=task['model'].split('?',1)
        self.assertRegex(question+'?',r'^Is there (?:some |any )?water\?$')
        self.assertRegex(request.strip(),r'^Can I have (?:some )?water, please\?$')
        form={'action':'batch','assistance':'no_help','batch_token':page.context['batch_token'],'transfer_variant':str(page.context['transfer_variant']),
            **{'answer_'+key:guide['tasks'][key]['model'] for key in ('meaning','writing','transfer','explain')}}
        form['answer_transfer']=task['model']
        response=self.client.post(url,form);self.assertEqual(response.status_code,200)
        saved=IndependentAttempt.objects.get(user=user,skill='transfer')
        self.assertEqual(saved.submitted,task['model']);self.assertEqual(saved.outcome,IndependentAttempt.Outcome.SELF_REPORTED)
        self.assertFalse(UnitProgress.objects.filter(user=user).exists())
