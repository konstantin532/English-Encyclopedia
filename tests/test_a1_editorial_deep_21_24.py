"""Live grading and lexical progress, A1 lessons 21–24."""
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.drills.models import Exercise
from apps.learning.models import UnitProgress
from tests.runner import ensure_content
class Editorial2124Tests(TestCase):
    @classmethod
    def setUpTestData(cls): ensure_content()
    def post(self, uid, answer, expected):
        item=Exercise.objects.get(uid=uid)
        r=self.client.post(f'/api/exercises/{item.pk}/check/',json.dumps({'answer':answer}),content_type='application/json')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['correct'],expected,answer)
    def test_local_contraction_owner_negation_and_order(self):
        for answer,expected in [("My last name's Belova.",True),('My last name is Belova.',True),("Her last name's Belova.",False),("My first name's Belova.",False),('My last name is not Belova.',False),('My Belova is last name.',False)]:
            with self.subTest(answer=answer): self.post('EX-00139',answer,expected)
    def test_headache_gap_progress(self): self.progress('EX-00117','headache',{'LX-00212'})
    def test_thirst_choice_progress(self): self.progress('EX-00126','I am thirsty.',{'LX-00405'})
    def test_leg_progress(self):
        self.progress('EX-00121','My leg hurts.',{'LX-00400'})
        for answer in ['Your leg hurts.','My leg does not hurt.','My leg hurt is.']: self.post('EX-00121',answer,False)
    def progress(self,uid,answer,expected):
        user=get_user_model().objects.create_user(email=uid+'@example.test',password='test-pass')
        self.client.force_login(user);self.post(uid,answer,True)
        self.assertEqual(set(UnitProgress.objects.filter(user=user).values_list('unit__uid',flat=True)),expected)
    def test_negative_auxiliary_keys(self):
        for uid,answer,expected in [('EX-00123','cannot',True),('EX-00123',"can't",True),('EX-00123','can',False),('EX-00123','am not',False),('EX-00129',"don't",True),('EX-00129','do not',True),('EX-00129',"doesn't",False),('EX-00129','do',False)]:
            with self.subTest(answer=answer): self.post(uid,answer,expected)
    def test_student_pages_and_unchanged_body_agreement(self):
        from django.urls import reverse
        for slug in ['a1-what-hurts','a1-cant-cannot','a1-dont-doesnt','a1-letters-address']:
            with self.subTest(slug=slug):
                response=self.client.get(reverse('lessons:detail',kwargs={'slug':slug}))
                self.assertEqual(response.status_code,200)
                self.assertNotContains(response,'[T4]')
        for answer,expected in [('My feet hurt.',True),('My feet hurts.',False),('Your feet hurt.',False)]:
            self.post('EX-00120',answer,expected)
    def test_dont_gap_does_not_certify_supplied_stamp_phrase(self):
        self.progress('EX-00129',"don't",set())
