from django.test import SimpleTestCase

from apps.curriculum.registry import LEVELS, TOTAL_UNITS, validate_plan
from apps.taxonomy.markup import find_issues, render_inline, strip_markup
from apps.taxonomy.registry import CATEGORIES, MARKERS, PALETTE, validate_registry


class RegistryTests(SimpleTestCase):
    def test_registry_is_valid(self):
        self.assertEqual(validate_registry(), [])

    def test_eleven_categories_each_with_unique_marker(self):
        self.assertEqual(len(CATEGORIES), 11)
        self.assertEqual(len({c.marker for c in CATEGORIES}), 11)
        self.assertTrue(all(c.marker in MARKERS for c in CATEGORIES))

    def test_content_words_use_bottom_lines_and_function_words_top(self):
        for c in CATEGORIES:
            line = MARKERS[c.marker][0]
            if c.content_word:
                self.assertEqual(line, "underline", c.key)
            elif c.code == "F":
                self.assertEqual(line, "line-through")
            else:
                self.assertEqual(line, "overline", c.key)

    def test_palette_has_ten_fixed_colors(self):
        self.assertEqual(PALETTE[1][1], "#d32f2f")
        self.assertEqual(PALETTE[10][1], "#37474f")
        self.assertEqual(len(PALETTE), 10)


class PlanTests(SimpleTestCase):
    def test_plan_is_consistent(self):
        self.assertEqual(validate_plan(), [])

    def test_totals(self):
        self.assertEqual(sum(lv.new_units for lv in LEVELS), TOTAL_UNITS)
        self.assertEqual(sum(lv.story_count for lv in LEVELS), 60)
        self.assertEqual(sum(lv.poem_count for lv in LEVELS), 60)
        self.assertEqual(sum(lv.weeks for lv in LEVELS), 150)


class MarkupTests(SimpleTestCase):
    def test_render_token(self):
        html = render_inline("[T3]My[/] [S2]book[/]")
        self.assertIn('data-cat="S" data-cls="2"', html)
        self.assertIn(">book</span>", html)

    def test_hex_must_match_registry(self):
        self.assertEqual(find_issues("[S1-#d32f2f]mother[/]"), [])
        issues = find_issues("[S1-#000000]mother[/]")
        self.assertEqual(len(issues), 1)
        self.assertIn("не совпадает", issues[0].problem)

    def test_unknown_class_is_reported(self):
        self.assertTrue(find_issues("[X10]word[/]"))  # у частиц 9 классов

    def test_html_is_escaped(self):
        self.assertNotIn("<script>", render_inline("<script>x</script> [S1]a[/]"))

    def test_strip(self):
        self.assertEqual(strip_markup("[T3]My[/] [S2]book[/]."), "My book.")


from pathlib import Path

import yaml

CONTENT = Path(__file__).resolve().parent.parent / "content"


class WeeksRegistryTests(SimpleTestCase):
    def test_spheres_and_norms(self):
        from apps.curriculum.registry import DIALOGUE_LINES, DIALOGUE_WORDS, SPHERES, TWISTER_SERIES, global_week

        self.assertEqual(len(SPHERES), 12)
        self.assertEqual(DIALOGUE_LINES["A1"], (6, 10))
        self.assertEqual(DIALOGUE_WORDS["A1"], (40, 90))
        self.assertEqual(set(TWISTER_SERIES), {lv.code for lv in LEVELS})
        self.assertEqual(TWISTER_SERIES["A1"], "sounds")
        self.assertEqual(TWISTER_SERIES["B2+"], "fast")
        self.assertEqual(global_week("A1", 1), 1)
        self.assertEqual(global_week("A1+", 1), 15)
        self.assertEqual(global_week("B2+", 22), 150)

    def test_voices_manifest_lists(self):
        v = yaml.safe_load((CONTENT / "manifests/voices.yaml").read_text(encoding="utf-8"))
        self.assertEqual(set(v["emotions"]),
                         {"neutral", "happy", "surprised", "sad", "tired", "angry", "worried", "whisper", "excited"})
        self.assertEqual(v["emotions"]["whisper"], {"name_ru": "шёпотом", "speed": 0.92, "gain_db": -8, "pause": 1.2})
        self.assertEqual(set(v["music_moods"]), {"none", "calm", "morning", "mystery", "sad", "happy", "tense"})
        self.assertEqual(v["music_gain_db"]["A1"], -26)
        self.assertEqual(v["music_gain_db"]["B2+"], -19)

    def test_weeks_plan_a1(self):
        from apps.curriculum.registry import SPHERES

        plan = yaml.safe_load((CONTENT / "manifests/weeks_plan.yaml").read_text(encoding="utf-8"))["weeks"]
        a1 = [w for w in plan if w["level"] == "A1"]
        self.assertEqual([w["week"] for w in a1], list(range(1, 15)))
        self.assertEqual({w["sphere"] for w in a1}, set(SPHERES))
        self.assertEqual(a1[0]["grammar_markers"], ["D1"])
        self.assertEqual(a1[7]["grammar_markers"], ["P1", "A6"])
        self.assertEqual(a1[13]["grammar_markers"], [])
