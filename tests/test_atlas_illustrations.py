from pathlib import Path
from xml.etree import ElementTree as ET
from django.test import SimpleTestCase
from apps.curriculum.views import a1_atlas_cover

ROOT = Path(__file__).resolve().parents[1]

class A1AtlasIllustrationsTests(SimpleTestCase):
    def test_each_chapter_has_original_local_vector_art(self):
        for week in range(1, 15):
            filename = f"a1-week-{week:02d}.svg"
            asset = ROOT / "static" / "img" / "studio" / filename
            self.assertTrue(asset.is_file(), filename)
            self.assertEqual(ET.parse(asset).getroot().tag, "{http://www.w3.org/2000/svg}svg")
            self.assertIn(filename, a1_atlas_cover("A1", week))

    def test_other_levels_or_missing_chapters_keep_existing_fallback(self):
        self.assertIsNone(a1_atlas_cover("A1+", 1))
        self.assertIsNone(a1_atlas_cover("B1", 4))
        self.assertIsNone(a1_atlas_cover("A1", 0))
        self.assertIsNone(a1_atlas_cover("A1", 15))
