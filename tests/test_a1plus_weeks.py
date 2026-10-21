"""Недели A1+: план на 16 недель и наполненные недели (диалог, уроки, слова, скороговорка)."""
from pathlib import Path

import yaml
from django.conf import settings
from django.test import TestCase

from apps.curriculum.models import TongueTwister, Week
from apps.curriculum.registry import DIALOGUE_LINES, DIALOGUE_WORDS, SPHERES
from apps.lexicon.models import LexicalUnit
from apps.publishing.audit import AuditReport, text_tokens
from apps.publishing.audit_weeks import audit_weeks
from tests.runner import ensure_content

CONTENT = Path(settings.CONTENT_DIR)
READY_WEEKS = (1, 2, 3)


class A1PlusPlanTests(TestCase):
    def test_plan_has_16_weeks_and_all_spheres(self):
        plan = yaml.safe_load((CONTENT / "manifests/weeks_plan.yaml").read_text(encoding="utf-8"))["weeks"]
        weeks = [w for w in plan if w["level"] == "A1+"]
        self.assertEqual([w["week"] for w in weeks], list(range(1, 17)))
        self.assertEqual({w["sphere"] for w in weeks}, set(SPHERES))
        self.assertEqual(weeks[-1]["grammar_markers"], [])  # неделя 16 — повторение уровня

    def test_dialogue_norms_exist_for_a1_plus(self):
        self.assertEqual(DIALOGUE_LINES["A1+"], (8, 12))
        self.assertEqual(DIALOGUE_WORDS["A1+"], (70, 130))


class A1PlusReadyWeeksTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_ready_weeks_have_everything(self):
        for n in READY_WEEKS:
            week = Week.objects.select_related("scene").get(level__code="A1+", number=n)
            with self.subTest(week=n):
                self.assertTrue(week.scene.script)
                self.assertGreaterEqual(week.lessons.filter(is_published=True).count(), 2)
                self.assertTrue(5 <= week.scene.chunks.count() <= 8)
                self.assertTrue(TongueTwister.objects.filter(week=week, series="contractions").exists())
                units = LexicalUnit.objects.filter(internal_level__code="A1+", week=week).count()
                self.assertTrue(30 <= units <= 39, units)
                words = len(text_tokens(" ".join(line["text"] for line in week.scene.script)))
                self.assertTrue(70 <= words <= 130, words)

    def test_audit_has_no_errors_for_ready_weeks(self):
        r = AuditReport()
        audit_weeks(r)
        own = [e for e in r.errors if any(f"A1+-{n}" in e or f"Скороговорка {14 + n}" in e for n in READY_WEEKS)]
        self.assertEqual(own, [])

    def test_ing_forms_are_forms_of_a1_verbs(self):
        for lemma, form in (("drink", "drinking"), ("sit", "sitting"), ("write", "writing"), ("be", "being")):
            self.assertIn(form, LexicalUnit.objects.get(lemma=lemma, unit_type="word").forms)
        self.assertFalse(LexicalUnit.objects.filter(lemma__in=["drinking", "making", "musting"]).exists())
