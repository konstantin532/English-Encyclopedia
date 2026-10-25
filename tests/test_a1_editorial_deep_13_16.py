"""Actual answer API, progress and rendered marker regressions for A1 13–16."""
import json
from html.parser import HTMLParser
from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import User
from apps.drills.models import Exercise, PracticeItem
from apps.learning.models import ExerciseAttempt, UnitProgress
from tests.runner import ensure_content

SLUGS=('a1-he-she-works','a1-jobs-what-do-you-do','a1-where-is-prepositions','a1-directions-turn-left')

class A1DeepThirteenSixteenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.user=User.objects.create_user('deep-thirteen@example.com','test-thirteen-only')
    def setUp(self):self.client.force_login(self.user)
    def check(self,collection,item,text,expected):
        response=self.client.post(f'/api/{collection}/{item.pk}/check/',json.dumps({'answer':text}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['correct'],expected,text)
        if collection=='practice' or item.stage==Exercise.Stage.TRANSFER:
            self.assertEqual(response.json()['assessment'],'model_match' if expected else 'needs_review')
    def test_start_time_slot_accepts_digits_and_clock_without_changing_subject_or_hour(self):
        item=Exercise.objects.get(uid='EX-00073')
        for text,expected in [('starts at seven.',True),('starts work at 7.',True),("starts at seven o'clock.",True),("starts work at 7 o'clock.",True),('start at seven.',False),('starts at eight.',False),("doesn't start at seven.",False),('He starts at seven.',False),('seven at starts.',False)]:
            with self.subTest(answer=text):self.check('exercises',item,text,expected)
    def test_mother_job_keys_allow_local_contractions_without_changing_owner_or_job(self):
        item=Exercise.objects.get(uid='EX-00079')
        good=["My mom is a nurse. She works at a hospital.","My mom's a nurse. She works in a hospital.","My mother's a nurse. She works at a hospital.","My mother's a nurse. She works in a hospital."]
        bad=["Your mom's a nurse. She works in a hospital.","My mom's a doctor. She works in a hospital.","My mom's not a nurse. She works in a hospital.","My mom's a nurse. He works in a hospital.","My mom a nurse is. She works in a hospital."]
        for text in good+bad:
            with self.subTest(answer=text):self.check('exercises',item,text,text in good)
    def test_cafe_location_allows_explicit_noun_contraction_but_not_wrong_side(self):
        item=Exercise.objects.get(uid='EX-00083')
        for text,expected in [("The cafe's on the right.",True),("The café is on the right.",True),("It's on the right.",True),("The cafe's on the left.",False),("The cafe's not on the right.",False),("The cafe on the right is.",False)]:
            with self.subTest(answer=text):self.check('exercises',item,text,expected)
    def test_she_short_reply_preserves_person_and_negation(self):
        item=Exercise.objects.get(uid='EX-00071')
        for text,expected in [("No, she doesn't.",True),('No, she does not.',True),("No, he doesn't.",False),('Yes, she does.',False),('No, she does.',False),("No, doesn't she.",False)]:
            with self.subTest(answer=text):self.check('exercises',item,text,expected)
    def practice_credits(self,slug,mapping):
        for order,uids in mapping.items():
            item=PracticeItem.objects.get(lesson__slug=slug,order=order)
            UnitProgress.objects.filter(user=self.user).delete()
            self.check('practice',item,item.answer,True)
            with self.subTest(lesson=slug,order=order):self.assertEqual(set(UnitProgress.objects.filter(user=self.user).values_list('unit__uid',flat=True)),set(uids))
    def test_third_person_practice_credits_only_its_target_words_and_phrases(self):
        self.practice_credits(SLUGS[0],{1:['LX-00128','LX-00153'],2:['LX-00128','LX-00131'],3:['LX-00128','LX-00150','LX-00156'],4:['LX-00332']})
    def test_jobs_practice_does_not_claim_office_or_a_different_job(self):
        self.practice_credits(SLUGS[1],{1:['LX-00142','LX-00152'],2:['LX-00128','LX-00143'],3:['LX-00151'],4:['LX-00146']})
    def test_locations_practice_does_not_claim_a_question_or_unspoken_right_answer(self):
        self.practice_credits(SLUGS[2],{1:['LX-00157','LX-00162','LX-00176'],2:['LX-00160','LX-00161','LX-00162','LX-00171'],3:['LX-00162','LX-00169','LX-00172'],4:['LX-00162','LX-00338','LX-00131','LX-00344']})
    def test_directions_practice_does_not_claim_turn_left_when_turning_right(self):
        self.practice_credits(SLUGS[3],{1:['LX-00166','LX-00170'],2:['LX-00167','LX-00168'],3:['LX-00166','LX-00167','LX-00169','LX-00170'],4:['LX-00158','LX-00159','LX-00175']})
    def main_credits(self,uid,uids):
        item=Exercise.objects.get(uid=uid);self.check('exercises',item,item.answer,True)
        self.assertEqual(set(UnitProgress.objects.filter(user=self.user).values_list('unit__uid',flat=True)),set(uids))
        self.assertTrue(ExerciseAttempt.objects.get(user=self.user,exercise=item).is_correct)
    def test_mia_cafe_does_not_certify_tom_home_phrase(self):self.main_credits('EX-00068',['LX-00128','LX-00131'])
    def test_she_reply_does_not_certify_he_reply_but_keeps_attempt(self):self.main_credits('EX-00071',[])
    def test_start_completion_does_not_certify_nurse_word(self):self.main_credits('EX-00073',['LX-00332'])
    def test_doctor_reply_does_not_certify_teacher_phrase(self):self.main_credits('EX-00077',['LX-00144'])
    def test_object_her_is_rendered_as_a_personal_pronoun(self):
        class Labels(HTMLParser):
            def __init__(self):super().__init__();self.span=None;self.rows=[]
            def handle_starttag(self,tag,attrs):
                if tag=='span':self.span=dict(attrs)
            def handle_data(self,data):
                if self.span and self.span.get('data-cat') and data.strip()=='her':self.rows.append((data.strip(),self.span.get('data-label','')))
            def handle_endtag(self,tag):
                if tag=='span':self.span=None
        for slug,word,suffix in [(SLUGS[3],'her','Личные местоимения (pronouns)')]:
            page=self.client.get(reverse('lessons:detail',args=[slug]));self.assertEqual(page.status_code,200)
            parser=Labels();parser.feed(page.content.decode());labels=[label for token,label in parser.rows if token==word]
            with self.subTest(word=word):self.assertTrue(labels);self.assertTrue(all(label.endswith(suffix) for label in labels),labels)
