"""Намеренно испорченные учебные тексты живут только в тестовой базе."""
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from apps.curriculum.models import TongueTwister, WeekScene
from apps.drills.models import Exercise
from apps.lessons.models import Lesson
from apps.publishing.audit import AuditReport, audit_contractions, run_audit
from apps.taxonomy.markup import find_issues, render_inline


class BrokenMarkupTests(SimpleTestCase):
    def test_unclosed_and_nested_markers_are_reported(self):
        for text in ["[S1]book", "[T8]I[/] [D1]am", "[Z1]book", "[S1]my [S2]book[/]",
                     "[S1-#oops]book", "[S1] [/]"]:
            with self.subTest(text=text):
                self.assertTrue(find_issues(text), text)

    def test_open_marker_with_a_missing_bracket_is_reported(self):
        for text in ["[S1", "[S1 book", "[T8]I[/] [D1 am\n[S2]home[/]"]:
            with self.subTest(text=text):
                self.assertTrue(find_issues(text), text)

    def test_valid_adjacent_tokens_and_literal_brackets_are_allowed(self):
        for text in ["[T8]I[/][D1]'m[/] [S2]home[/].", "[D1]is[/][X1]n't[/]", "См. [пример], [1] и /aɪm/.",
                     "[S1-#d32f2f]mother[/]", "[S2]my\nbook[/]"]:
            with self.subTest(text=text):
                self.assertEqual(find_issues(text), [])

    def test_html_stays_escaped_even_inside_malformed_markup(self):
        text = '[S1]<img src=x onerror="alert(1)"> [S2]book[/]'
        html = render_inline(text)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)

    def test_unsplit_negative_inside_a_longer_marker_is_rejected(self):
        for text in ["[D1]isn't my book[/]", "[D1]don't.[/]", "[D1]isn’t my book[/]",
                     "[D1-#d32f2f]isn't\nmy book[/]"]:
            with self.subTest(text=text):
                report = AuditReport()
                audit_contractions(report, "пример", text)
                self.assertTrue(report.errors)


class AuditSurfaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", stdout=StringIO())

    def test_invalid_markup_in_written_week_dialogue_is_reported(self):
        scene = WeekScene.objects.get(week__level__code="A1", week__number=1)
        scene.script[0]["text"] = "[X10]Good[/] [S7]morning[/]!"
        scene.save()
        self.assertTrue(any("X10" in error and "Неделя A1-1" in error for error in run_audit().errors))

    def test_invalid_markup_in_story_is_reported(self):
        from apps.stories.models import Story

        story = Story.objects.get(number=1)
        story.script[0]["text"] = "[X10]My[/] [S9]name[/] [D1]is[/] [S1]Anna[/]."
        story.body = "\n\n".join(line["text"] for line in story.script)
        story.save()
        self.assertTrue(any("X10" in error and "История 1" in error for error in run_audit().errors))

    def test_invalid_markup_in_twister_is_reported(self):
        twister = TongueTwister.objects.get(number=1)
        twister.text = "[X10]This[/] [S2]house[/], [T2]this[/] [S2]room[/]."
        twister.save()
        self.assertTrue(any("X10" in error and "Скороговорка 1" in error for error in run_audit().errors))

    def test_unsplit_negative_in_twister_is_reported(self):
        twister = TongueTwister.objects.get(number=1)
        twister.text = "[D1]isn't[/] [T3]my[/] [S2]book[/]."
        twister.save()
        self.assertTrue(any("слитная форма" in error and "Скороговорка 1" in error for error in run_audit().errors))

    def test_invalid_markup_in_sound_notes_is_reported(self):
        lesson = Lesson.objects.get(slug="a1-verb-be")
        lesson.sound_notes[0]["text"] = "[X10]It[/] is nice."
        lesson.save()
        self.assertTrue(any("X10" in error and "a1-verb-be" in error for error in run_audit().errors))

    def test_unregistered_word_in_contraction_pair_is_reported(self):
        lesson = Lesson.objects.get(slug="a1-verb-be")
        lesson.contractions[0]["full"] = "I am quokkapocalypse"
        lesson.contractions[0]["short"] = "I'm quokkapocalypse"
        lesson.save()
        self.assertIn("quokkapocalypse", run_audit().unknown_words)

    def test_contraction_field_is_not_scanned_as_an_english_marker(self):
        lesson = Lesson.objects.get(slug="a1-verb-be")
        lesson.contractions[0]["full"] = "[T8]I[/] [D1]am[/]"
        lesson.contractions[0]["short"] = "[T8]I[/][D1]'m[/]"
        lesson.save()
        self.assertFalse([error for error in run_audit().errors if "нет апострофа" in error or "full не должно" in error])

    def test_unknown_word_in_choice_options_is_reported(self):
        exercise = Exercise.objects.get(lesson__slug="a1-nouns-first-words", order=1)
        exercise.options = [*exercise.options, "quokkapocalypse"]
        exercise.save()
        self.assertIn("quokkapocalypse", run_audit().unknown_words)

    def test_seeded_choices_do_not_introduce_unregistered_words(self):
        self.assertEqual(run_audit().unknown_words, {})
