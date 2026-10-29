"""Живая разговорная речь в диалогах A1.

Реакции (Oh, Wow, Yeah, Hmm…) делают речь американской: без них даже
правильная грамматика звучит как диктор учебника. Тест не даёт Codex
или автору незаметно вернуть «учебные» диалоги.
"""
import re
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase

CONTENT = Path(settings.BASE_DIR) / "content"
MARKER = re.compile(r"\[[^\]]+\]")
LIVE = ("oh", "wow", "yeah", "awesome", "aww", "hmm", "hey", "hi", "no kidding", "thanks a lot",
        "one second", "no way", "oh no", "take care", "i'm in", "have a good one", "sounds good")


def spoken_lines(week):
    data = yaml.safe_load((CONTENT / "seed_weeks" / f"a1_w{week:02d}.yaml").read_text(encoding="utf-8"))
    return [MARKER.sub("", line.get("spoken") or line["text"]).casefold() for line in data["script"]]


class A1LiveSpeechTests(SimpleTestCase):
    def test_every_week_after_the_first_has_live_reactions(self):
        # Неделя 1 — первые слова: реакции вводятся со второй недели.
        for week in range(2, 15):
            with self.subTest(week=week):
                text = " ".join(spoken_lines(week))
                found = [r for r in LIVE if re.search(rf"(?<![a-z']){re.escape(r)}(?![a-z'])", text)]
                self.assertTrue(found, f"в неделе {week} нет ни одной живой реакции")

    def test_live_pack_is_registered_once(self):
        lemmas = []
        for path in sorted((CONTENT / "seed_lexicon").glob("a1_w*_live_speech.yaml")):
            lemmas += [u["lemma"].casefold().rstrip(".!") for u in yaml.safe_load(path.read_text(encoding="utf-8"))["units"]]
        self.assertEqual(len(lemmas), 16)
        self.assertEqual(len(set(lemmas)), 16)
