"""Audit vocabulary identity must preserve accents, not certify ASCII fragments."""
import unicodedata
from types import SimpleNamespace
from django.test import SimpleTestCase, TestCase
from apps.drills.models import Exercise
from apps.lexicon.models import LexicalUnit, UnitType
from apps.publishing.audit import text_tokens, is_known, unit_words, run_audit
from tests.runner import ensure_content

class LatinAuditTokenTests(SimpleTestCase):
    def test_accented_words_are_single_tokens_and_russian_explanations_are_ignored(self):
        self.assertEqual(text_tokens('Кофе: café, piñata; résumé и naïve.'),['café','piñata','résumé','naïve'])
        self.assertEqual(text_tokens('Молоко, кофе, русский перевод.'),[])
    def test_nfd_and_nfc_have_one_identity_without_losing_accents(self):
        text='café íntegro résumé'
        self.assertEqual(text_tokens(unicodedata.normalize('NFD',text)),text.split())
        self.assertTrue(is_known(unicodedata.normalize('NFD','íntegro'),{'íntegro'}))
        self.assertFalse(is_known('íntegro',{'integro'}))
        # Not every Latin-letter/diacritic pair has a precomposed code point.
        self.assertEqual(text_tokens('q\u0301a'),['q\u0301a'])
    def test_cafe_variant_is_known_only_when_the_variant_is_declared(self):
        plain=SimpleNamespace(lemma='cafe',forms=['cafes'],unit_type=UnitType.WORD)
        declared=SimpleNamespace(lemma='cafe',forms=['cafes','café','cafés'],unit_type=UnitType.WORD)
        self.assertFalse(is_known('café',unit_words(plain)))
        for word in ['café','cafés',"café's"]:
            with self.subTest(word=word):self.assertTrue(is_known(word,unit_words(declared)))
    def test_stored_nfd_forms_are_canonically_normalized(self):
        unit=SimpleNamespace(lemma='cafe',forms=[unicodedata.normalize('NFD','café')],unit_type=UnitType.WORD)
        self.assertIn('café',unit_words(unit))
    def test_unknown_pinata_does_not_become_two_known_ascii_fragments(self):
        words=text_tokens('piñata')
        self.assertEqual(words,['piñata'])
        self.assertFalse(all(is_known(word,{'pi','ata'}) for word in words))
    def test_resume_and_resume_with_accents_remain_distinct_words(self):
        self.assertFalse(is_known('résumé',{'resume'}))
        self.assertFalse(is_known('resume',{'résumé'}))
        self.assertEqual(text_tokens('résumé resume'),['résumé','resume'])
    def test_existing_contraction_and_punctuation_rules_are_preserved(self):
        self.assertEqual(text_tokens("I’m, Anna's; can't! don't? books."),['I’m',"Anna's","can't","don't",'books'])
        for text in ['I’m',"Anna's","can't","don't",'books']:
            with self.subTest(word=text):self.assertTrue(is_known(text,{'i','anna','can','do','book'}))
    def test_mixed_script_misspelling_is_not_silently_ignored(self):
        bad='c\u0430fe'  # Cyrillic а between Latin letters.
        self.assertEqual(text_tokens(bad),[bad])
        self.assertFalse(is_known(bad,{'cafe'}))

class RealLatinCourseAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):ensure_content()
    def test_loaded_existing_cafe_unit_declares_its_spellings_without_another_uid(self):
        unit=LexicalUnit.objects.get(uid='LX-00131')
        self.assertEqual(unit.lemma,'cafe')
        self.assertTrue({'café','cafés'}<=set(unit.forms))
        self.assertFalse(LexicalUnit.objects.filter(lemma='café').exists())
    def test_real_audit_keeps_valid_cafe_and_still_reports_whole_unknown_words(self):
        unit=LexicalUnit.objects.get(uid='LX-00131')
        # Same legitimate fixture both before and after, isolating tokenization.
        unit.forms=list(dict.fromkeys([*unit.forms,'café','cafés']))
        unit.save(update_fields=['forms'])
        item=Exercise.objects.get(uid='EX-00083')
        item.accepted=[*item.accepted,"The café's on the right.",'The piñata is on the right.']
        item.save(update_fields=['accepted'])
        report=run_audit()
        self.assertNotIn('caf',report.unknown_words)
        self.assertNotIn('café',report.unknown_words)
        self.assertNotIn("café's",report.unknown_words)
        self.assertIn('piñata',report.unknown_words)
        self.assertIn('a1-where-is-prepositions/задание 4',report.unknown_words['piñata'])
        self.assertNotIn('pi',report.unknown_words)
        self.assertNotIn('ata',report.unknown_words)
