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
