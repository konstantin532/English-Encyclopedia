"""Новое слово A1+ не может повторять слово A1 — ни целиком, ни как его форму."""
from django.test import TestCase

from apps.curriculum.models import Level, Week
from apps.lexicon.models import LexicalUnit
from apps.publishing.audit import run_audit
from tests.runner import ensure_content


class DuplicateWordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.a1plus = Level.objects.get(code="A1+")
        cls.week = Week.objects.filter(level=cls.a1plus).order_by("number").first()
        cls.template = LexicalUnit.objects.get(uid="LX-00016")  # be (A1)

    def errors(self, needle):
        return [e for e in run_audit().errors if needle in e]

    def add(self, uid, lemma, **extra):
        unit = LexicalUnit.objects.get(pk=self.template.pk)
        unit.pk, unit.uid, unit.lemma = None, uid, lemma
        unit.internal_level, unit.week = self.a1plus, self.week
        unit.forms, unit.grammar_features = extra.get("forms", []), extra.get("grammar_features", [])
        unit.save()
        return unit

    def test_current_course_has_no_repeated_words(self):
        self.assertEqual(self.errors("уже есть в словаре"), [])
        self.assertEqual(self.errors("а не новое слово"), [])

    def test_repeating_an_a1_word_is_an_error(self):
        self.add("LX-99901", "cat")
        self.assertTrue(self.errors("LX-99901 cat: слово уже есть в словаре"))

    def test_a_form_of_a_known_word_is_not_a_new_word(self):
        self.add("LX-99902", "is")  # форма be
        self.assertTrue(self.errors("LX-99902 is: это форма слова be"))

    def test_explicit_new_meaning_is_allowed(self):
        self.add("LX-99903", "cat", grammar_features=["new_sense"])
        self.assertEqual(self.errors("LX-99903"), [])

    def test_related_but_different_word_is_allowed(self):
        self.add("LX-99904", "teacherly")
        self.assertEqual(self.errors("LX-99904"), [])
