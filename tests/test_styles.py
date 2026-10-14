import re
from pathlib import Path

from django.test import SimpleTestCase


class SpeechStyleTests(SimpleTestCase):
    def test_new_week_and_speech_styles_use_defined_tokens(self):
        root = Path(__file__).resolve().parent.parent / "static/css"
        sheets = [path.read_text(encoding="utf-8") for path in root.glob("*.css")]
        defined = set(re.findall(r"(--[\w-]+)\s*:", "\n".join(sheets)))
        studio = (root / "studio.css").read_text(encoding="utf-8")
        new_rules = studio.split("/* Два варианта реплики и пояснение полной формы. */", 1)[1]
        used = set(re.findall(r"var\((--[\w-]+)\)", new_rules))
        self.assertEqual(used - defined, set())
