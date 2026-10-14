import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import yaml
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("gen", ROOT / "scripts" / "generate_story_audio.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

VOICES = yaml.safe_load((ROOT / "content/manifests/voices.yaml").read_text(encoding="utf-8"))
ROLES, EMOTIONS = VOICES["roles"], VOICES["emotions"]

STORY = """number: 1
ambience: morning_home
script:
  - speaker: anna
    text: "[T8]I[/] [D1]am[/] [S1]Anna[/]."
    music: morning
  - speaker: tom
    text: "[T8]I[/] [D1]am[/] [S1]Tom[/]."
    emotion: happy
"""
WEEK = """level: A1
week: 1
ambience: morning_home
script:
  - speaker: anna
    text: "[T8]I[/] [D1]am[/] [S1]Anna[/]."
  - speaker: tom
    text: "[T8]I[/] [D1]am[/] [S1]Tom[/]."
    emotion: surprised
"""


class GeneratorTests(SimpleTestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        patches = [mock.patch.object(gen, "ROOT", self.tmp), mock.patch.object(gen, "OUT", self.tmp / "static" / "audio")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def write(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_emotion_changes_speed_and_lands_in_timings(self):
        script = [{"speaker": "tom", "text": "I am Tom here", "emotion": "sad"},
                  {"speaker": "tom", "text": "I am Tom here"}]
        _, t = gen.build_track(gen.TestEngine(), script, ROLES, 1.0, 1.0, EMOTIONS)
        self.assertEqual([x["emotion"] for x in t], ["sad", "neutral"])
        self.assertGreater(t[0]["end"] - t[0]["start"], t[1]["end"] - t[1]["start"])

    def test_whisper_is_quieter(self):
        script = [{"speaker": "tom", "text": "I am Tom", "emotion": "whisper"}, {"speaker": "tom", "text": "I am Tom"}]
        audio, t = gen.build_track(gen.TestEngine(), script, ROLES, 1.0, 1.0, EMOTIONS)
        part = lambda x: audio[int(x["start"] * gen.SR):int(x["end"] * gen.SR)]
        self.assertLess(np.abs(part(t[0])).max(), np.abs(part(t[1])).max() / 2)

    def test_music_ducks_under_lines(self):
        music = np.ones(gen.SR * 6, np.float32)
        out = gen.duck(music, [{"start": 2.0, "end": 4.0}])
        self.assertLess(abs(out[int(3.0 * gen.SR)]), 10 ** (-11 / 20))
        self.assertGreater(abs(out[int(5.5 * gen.SR)]), 0.9)
        self.assertGreater(abs(out[int(0.5 * gen.SR)]), 0.99)

    def test_music_none_gives_no_track(self):
        self.assertIsNone(gen.music_track([{"speaker": "anna", "text": "Hi", "music": "none"}], [{"start": 0, "end": 1}], 2.0))
        self.assertIsNone(gen.music_track([{"speaker": "anna", "text": "Hi"}], [{"start": 0, "end": 1}], 2.0))

    def test_music_mood_carries_forward(self):
        script = [{"speaker": "anna", "text": "a", "music": "calm"}, {"speaker": "anna", "text": "b"},
                  {"speaker": "anna", "text": "c", "music": "none"}]
        timings = [{"start": 0.5, "end": 2}, {"start": 3, "end": 5}, {"start": 8, "end": 9}]
        m = gen.music_track(script, timings, 12.0)
        self.assertEqual(len(m), 12 * gen.SR)
        self.assertGreater(np.abs(m[int(4 * gen.SR):int(6 * gen.SR)]).max(), 0.01)
        self.assertLess(np.abs(m[int(10 * gen.SR):]).max(), 1e-6)

    def test_every_mood_generator_is_deterministic(self):
        for mood, fn in gen.MUSIC.items():
            with self.subTest(mood=mood):
                a, b = fn(4.0), fn(4.0)
                self.assertTrue(np.array_equal(a, b))
                self.assertGreater(np.abs(a).max(), 0.01)
        self.assertEqual(set(gen.MUSIC) | {"none"}, set(VOICES["music_moods"]))

    def test_story_manifest_has_music_per_tempo(self):
        msg = gen.generate(gen.TestEngine(), self.write("s01.yaml", STORY), VOICES)
        manifest = json.loads((self.tmp / "static/audio/stories/s01/manifest.json").read_text(encoding="utf-8"))
        self.assertIn("История 1", msg)
        self.assertEqual(manifest["natural"]["music_gain_db"], -26)
        self.assertEqual(manifest["very_slow"]["music_gain_db"], -30)
        self.assertTrue((self.tmp / "static" / manifest["slow"]["music"]).exists())
        self.assertRegex(manifest["slow"]["music"], r"stories/s01/music_slow\.(mp3|wav)$")
        self.assertEqual([t["emotion"] for t in manifest["slow"]["timings"]], ["neutral", "happy"])

    def test_story_without_music_has_no_music_keys(self):
        gen.generate(gen.TestEngine(), self.write("s01.yaml", STORY.replace("    music: morning\n", "")), VOICES)
        manifest = json.loads((self.tmp / "static/audio/stories/s01/manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("music", manifest["slow"])

    def test_unknown_emotion_exits_with_message(self):
        with self.assertRaises(SystemExit) as cm:
            gen.generate(gen.TestEngine(), self.write("s01.yaml", STORY.replace("emotion: happy", "emotion: furious")), VOICES)
        self.assertIn("неизвестная эмоция furious", str(cm.exception.code))
        with self.assertRaises(SystemExit) as cm:
            gen.generate(gen.TestEngine(), self.write("s01.yaml", STORY.replace("music: morning", "music: disco")), VOICES)
        self.assertIn("неизвестное настроение disco", str(cm.exception.code))

    def test_week_and_twister_folders(self):
        gen.generate_week(gen.TestEngine(), self.write("a1_w01.yaml", WEEK), VOICES)
        week = json.loads((self.tmp / "static/audio/weeks/a1-w01/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(week["natural"]["timings"]), 2)
        self.assertNotIn("music", week["natural"])
        gen.generate_twister(gen.TestEngine(), {"number": 1, "text": "[T2]This[/] [D1]is[/] [T2]this[/]."}, VOICES)
        tw = json.loads((self.tmp / "static/audio/twisters/t001/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(tw) & {"very_slow", "slow", "natural"}, {"very_slow", "slow", "natural"})
        self.assertIsNone(tw["ambience"])
        self.assertEqual(tw["voices"], {"twister": VOICES["extras"][0]})
