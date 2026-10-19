"""Structural contracts. Browser and device measurements require a separate QA pass."""
import re
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parent.parent


class MotionSystemContracts(SimpleTestCase):
    def test_base_loads_existing_gsap_once_then_motion_runtime(self):
        base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
        self.assertEqual(base.count("vendor/gsap/gsap.min.js"), 1)
        self.assertEqual(base.count("js/motion-system.js"), 1)
        self.assertEqual(base.count("css/motion-system.css"), 1)
        self.assertLess(base.index("vendor/gsap/gsap.min.js"), base.index("js/motion-system.js"))
        self.assertLess(base.index("css/accessibility.css"), base.index("css/motion-system.css"))

    def test_manual_and_system_minimal_are_independent_failsafes(self):
        css = (ROOT / "static/css/motion-system.css").read_text(encoding="utf-8")
        js = (ROOT / "static/js/motion-system.js").read_text(encoding="utf-8")
        minimal_selector = r'html\[data-motion=(?:"minimal"|minimal)\] \*'
        self.assertRegex(css, minimal_selector)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn('"ee-motion-mode"', js)
        self.assertIn('media.matches', js)
        self.assertNotIn('display: none', re.split(minimal_selector, css, maxsplit=1)[1])
        self.assertIn('if (!global || !global.document) return;', js)

    def test_controls_do_not_change_navigation_or_educational_content(self):
        header = (ROOT / "templates/components/header.html").read_text(encoding="utf-8")
        footer = (ROOT / "templates/components/footer.html").read_text(encoding="utf-8")
        self.assertIn('aria-label="Интенсивность анимации"', header)
        self.assertIn('aria-label="Интенсивность анимации"', footer)
        self.assertIn("data-motion-control", header)
        self.assertIn("data-motion-control", footer)
        self.assertIn("motion-control-mobile", footer)
        self.assertIn("aria-live", header)

    def test_feedback_remains_server_authoritative(self):
        player = (ROOT / "static/js/learning-player.js").read_text(encoding="utf-8")
        self.assertIn("data.correct", player)
        self.assertIn("await post(form.dataset.url, { answer: value })", player)
        self.assertIn("if (checking) return", player)
        self.assertIn("window.EnglishMotion?.resolve(feedback, state)", player)
        self.assertNotIn("gsap.fromTo(feedback", player)
