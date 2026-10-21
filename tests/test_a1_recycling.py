"""Повторение прошлого уровня и порог знакомых слов в историях (план 16 недель A1+)."""
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, TestCase

from apps.lexicon.models import UnitType
from apps.publishing import audit
from tests.runner import ensure_content


def unit(uid, lemma, forms=(), phrase=False):
    return SimpleNamespace(uid=uid, lemma=lemma, forms=list(forms),
                           unit_type=UnitType.PHRASE if phrase else UnitType.WORD)


class RecyclingCountTests(SimpleTestCase):
    def test_words_count_by_forms_endings_and_contractions(self):
        units = [unit("LX-1", "go", ["went", "goes"]), unit("LX-2", "book"), unit("LX-3", "can")]
        texts = ["[S1]Anna[/] went home. She goes to the [S1]books[/] shop.", "I can't. You can."]
        counts = audit.recycling_counts(units, texts)
        self.assertEqual(counts, {"LX-1": 2, "LX-2": 1, "LX-3": 2})

    def test_phrase_counts_only_as_whole(self):
        units = [unit("LX-9", "See you later", phrase=True)]
        counts = audit.recycling_counts(units, ["See you later, Max!", "Later I see you."])
        self.assertEqual(counts["LX-9"], 1)

    def test_story_threshold_is_ninety_five_percent(self):
        self.assertEqual(audit.STORY_KNOWN_SHARE, 0.95)
        self.assertEqual((audit.RECYCLE_TARGET, audit.RECYCLE_MIN_HITS), (0.70, 2))


class RecyclingReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_report_says_no_a1plus_texts_yet(self):
        r = audit.AuditReport()
        with mock.patch.object(audit, "level_texts", return_value=[]):
            audit.audit_recycling(r)
        self.assertIn("Повторение A1 в A1+: текстов A1+ пока нет.", r.facts)
        self.assertFalse(r.errors)

    def test_low_recycling_is_a_warning_with_missing_words(self):
        r = audit.AuditReport()
        with mock.patch.object(audit, "level_texts",
                               side_effect=lambda lv: ["Hello. Hello."] if lv.code == "A1+" else []):
            audit.audit_recycling(r)
        fact = next(f for f in r.facts if f.startswith("Повторение A1 в A1+"))
        self.assertIn("цель 70%", fact)
        warning = next(w for w in r.warnings if w.startswith("Повторение A1 в A1+"))
        self.assertIn("Ещё не встречались", warning)
        self.assertFalse(r.errors)

    def test_full_recycling_has_no_warning(self):
        from apps.lexicon.models import LexicalUnit

        a1 = list(LexicalUnit.objects.filter(internal_level__code="A1"))
        text = " ".join(f"{u.lemma}. {u.lemma}." for u in a1)
        r = audit.AuditReport()
        with mock.patch.object(audit, "level_texts", side_effect=lambda lv: [text] if lv.code == "A1+" else []):
            audit.audit_recycling(r)
        self.assertFalse([w for w in r.warnings if w.startswith("Повторение A1 в A1+")])
        self.assertIn(f"из {len(a1)} единиц", next(f for f in r.facts if "A1 в A1+" in f))

    def test_a1_stories_meet_new_threshold(self):
        r = audit.AuditReport()
        audit.audit_stories_and_poems(r)
        self.assertFalse([e for e in r.errors if "знакомых слов" in e])
