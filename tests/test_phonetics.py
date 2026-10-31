from django.template import Context, Template
from django.test import SimpleTestCase

from apps.lexicon.phonetics import HINTS, render_html, to_plain, transcribe, unknown_symbols
from tests.runner import ensure_content


class RussianTranscriptionTests(SimpleTestCase):
    def test_words_from_the_course(self):
        cases = {
            "/ˈmʌðɚ/": "ма́зэр",
            "/ˈfæməli/": "фэ́мэли",
            "/ˈwɑt̬ɚ/": "уа́дэр",
            "/aɪm ˈhoʊm/": "айм хо́ум",
            "/hæv‿ə ˈnaɪs ˈdeɪ/": "хэв‿э на́йс дэ́й",
            "/ju/": "ю",
            "/jɚ maɪ ˈfrend/": "йэр май фрэ́нд",
            "/ɡʊd ˈmɔrnɪŋ | ˈdeɪ/": "гуд мо́рнин | дэ́й",
            "/ɪt ˈɪzənt maɪ ˈbʊk/": "ит и́зэнт май бу́к",
            "/ðæts ˈnaɪs/": "зэтс на́йс",
            "/maɪ ˈfoʊn‿ɪz ˈnu/": "май фо́ун‿из ну́",
        }
        for ipa, expected in cases.items():
            with self.subTest(ipa=ipa):
                self.assertEqual(to_plain(ipa), expected)

    def test_text_outside_slashes_is_kept(self):
        self.assertEqual(
            to_plain("/də jə ˈlaɪk‿ɪt/, быстро /dʒə ˈlaɪk‿ɪt/"),
            "дэ йэ ла́йк‿ит, быстро джэ ла́йк‿ит",
        )

    def test_hard_sounds_are_marked(self):
        marked = [(s.text, s.hint) for s in transcribe("/ˈmʌðɚ/") if s.hint]
        self.assertEqual(marked, [("з", "dh"), ("эр", "r")])
        hints = {s.hint for s in transcribe("/θɪŋk ˈwɑt̬ɚ hæv/") if s.hint}
        self.assertEqual(hints, {"th", "ng", "w", "flap", "r", "h", "ae"})
        self.assertTrue(set(HINTS) >= hints)

    def test_unknown_symbols_are_reported(self):
        self.assertEqual(unknown_symbols("/ˈmʌðɚ/, быстро /ˈmʌðɚ/"), set())
        self.assertEqual(unknown_symbols("/ˈmʌxɚ/"), {"x"})

    def test_html_marks_sounds_and_override_wins(self):
        html = render_html("/ˈmʌðɚ/")
        self.assertIn('class="ru-tr"', html)
        self.assertIn('data-snd="dh"', html)
        self.assertIn(HINTS["dh"][1], html)
        self.assertIn("ма́", html)
        custom = render_html("/ˈmʌðɚ/", override="мазер")
        self.assertIn("мазер", custom)
        self.assertNotIn("data-snd", custom)
        self.assertEqual(render_html(""), "")

    def test_template_filter(self):
        out = Template('{% load ru %}{{ ipa|ru_ipa }}').render(Context({"ipa": "/aɪm ˈhoʊm/"}))
        self.assertIn("о́ум", out)
        self.assertIn('data-snd="h"', out)


from django.test import TestCase
from django.urls import reverse

from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from apps.poems.models import Poem


class RussianTranscriptionOnPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def test_every_unit_and_note_has_known_symbols(self):
        from apps.publishing.audit import run_audit

        self.assertEqual([w for w in run_audit().warnings if "транскрипц" in w], [])

    def test_audit_warns_about_unknown_symbol(self):
        from apps.publishing.audit import run_audit

        unit = LexicalUnit.objects.get(lemma="mother")
        unit.ipa_us = "/ˈmʌxɚ/"
        unit.save()
        self.assertTrue(any("mother" in w and "x" in w for w in run_audit().warnings))
        unit.ipa_ru = "ма́зэр"
        unit.save()
        self.assertFalse(any("mother" in w and "транскрипц" in w for w in run_audit().warnings))

    def test_word_list_and_detail_show_russian(self):
        unit = LexicalUnit.objects.get(lemma="mother")
        self.assertContains(self.client.get(reverse("lexicon:list")), "ма́")
        detail = self.client.get(reverse("lexicon:detail", args=[unit.uid]))
        self.assertContains(detail, 'data-snd="dh"')
        self.assertContains(detail, 'id="sound-legend"')

    def test_manual_override_on_word_page(self):
        unit = LexicalUnit.objects.get(lemma="mother")
        unit.ipa_ru = "ма́зэр (ручной)"
        unit.save()
        self.assertContains(self.client.get(reverse("lexicon:detail", args=[unit.uid])), "ма́зэр (ручной)")

    def test_lesson_sound_notes_and_poem_show_russian(self):
        lesson = Lesson.objects.get(slug="a1-nouns-first-words")
        response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
        self.assertContains(response, "[айм <span class=\"snd\" data-snd=\"h\"")
        self.assertContains(response, "о́ум]")
        poem = Poem.objects.exclude(pronunciation=[]).first()
        response = self.client.get(reverse("stories:poem", args=[poem.number]))
        self.assertContains(response, 'class="ru-tr"')
