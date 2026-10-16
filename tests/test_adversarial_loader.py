"""Повреждённые YAML-пакеты отклоняются с указанием файла и откатом."""
import copy
import shutil
import tempfile
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.test import tag

from apps.curriculum.models import TongueTwister, WeekScene
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit


@tag("slow")  # намеренно ломает и перезагружает весь курс; полный прогон — перед слиянием
class InvalidSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_content", stdout=StringIO())

    @contextmanager
    def changed_file(self, relative, transform=None, raw=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            content = root / "content"
            shutil.copytree(settings.CONTENT_DIR, content)
            path = content / relative
            if raw is None:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                raw = yaml.safe_dump(transform(copy.deepcopy(data)), allow_unicode=True, sort_keys=False)
            path.write_text(raw, encoding="utf-8")
            with override_settings(CONTENT_DIR=content, BASE_DIR=root):
                yield path

    def assert_rejected(self, relative, transform=None, raw=None):
        original = LexicalUnit.objects.get(uid="LX-00001").translation_ru
        with self.changed_file(relative, transform, raw) as path:
            with self.assertRaisesMessage(CommandError, path.name):
                call_command("load_content", stdout=StringIO())
        self.assertEqual(LexicalUnit.objects.get(uid="LX-00001").translation_ru, original)

    def test_invalid_yaml_and_non_mapping_documents_are_explained(self):
        for raw in ["units: [broken", "", "null", "[]", "42"]:
            with self.subTest(raw=raw):
                self.assert_rejected("seed_weeks/a1_w01.yaml", raw=raw)

    def test_script_shape_and_required_text_are_validated(self):
        for script in [None, {}, [None], ["hello"], [{"speaker": "anna"}], [{"speaker": "anna", "text": 42}]]:
            for file in ["seed_weeks/a1_w01.yaml", "seed_stories/s01_not_my_box.yaml"]:
                with self.subTest(file=file, script=script):
                    self.assert_rejected(file, lambda d: {**d, "script": script})

    def test_empty_false_story_beat_is_not_silently_accepted(self):
        for beat in [[], "", False, 0]:
            with self.subTest(beat=beat):
                self.assert_rejected("seed_weeks/a1_w01.yaml", lambda d: {**d, "story_beat": beat})

    def test_sound_notes_and_contractions_have_required_text_fields(self):
        for key, value in [("sound_notes", None), ("sound_notes", [{}]), ("sound_notes", [{"text": 42}]),
                           ("contractions", [None]), ("contractions", [{"full": "I am"}])]:
            with self.subTest(key=key, value=value):
                self.assert_rejected("seed_lessons/a1_w01_l02_be.yaml", lambda d: {**d, key: value})

    def test_twister_number_cannot_delete_another_weeks_twister(self):
        before = list(TongueTwister.objects.order_by("number").values_list("number", "week_id"))
        self.assert_rejected("seed_weeks/a1_w02.yaml", lambda d: {**d, "twister": {**d["twister"], "number": 1}})
        self.assertEqual(list(TongueTwister.objects.order_by("number").values_list("number", "week_id")), before)

    def test_duplicate_unit_ids_are_not_silently_overwritten(self):
        def duplicate(data):
            data["units"].append({**data["units"][0], "translation_ru": "искажённый перевод"})
            return data
        self.assert_rejected("seed_lexicon/a1_w01_core.yaml", duplicate)

    def test_invalid_late_package_rolls_back_earlier_updates(self):
        with self.changed_file("seed_weeks/a1_w01.yaml", lambda d: {**d, "chunks": ["LX-99999"]}):
            seed = Path(settings.CONTENT_DIR) / "seed_lexicon/a1_w01_core.yaml"
            data = yaml.safe_load(seed.read_text(encoding="utf-8"))
            unit_id = data["units"][0]["uid"]
            original = LexicalUnit.objects.get(uid=unit_id).translation_ru
            data["units"][0]["translation_ru"] = "НЕ ДОЛЖНО СОХРАНИТЬСЯ"
            seed.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
            with self.assertRaises(CommandError):
                call_command("load_content", stdout=StringIO())
            self.assertEqual(LexicalUnit.objects.get(uid=unit_id).translation_ru, original)

    def test_unknown_unit_references_cannot_disappear_silently(self):
        def broken_exercise(data):
            data["exercises"][0]["units"] = ["LX-99999"]
            return data
        for file, transform in [
            ("seed_lessons/a1_w01_l01_nouns.yaml", broken_exercise),
            ("seed_stories/s01_not_my_box.yaml", lambda d: {**d, "new_units": ["LX-99999"]}),
            ("seed_poems/p01_my_new_home.yaml", lambda d: {**d, "target_units": ["LX-99999"]}),
        ]:
            with self.subTest(file=file):
                self.assert_rejected(file, transform)

    def test_invalid_unit_class_has_an_explanation(self):
        for code in ["Z1", "S999", "broken"]:
            def bad_class(data):
                data["units"][0]["class"] = code
                return data
            with self.subTest(code=code):
                self.assert_rejected("seed_lexicon/a1_w01_core.yaml", bad_class)

    def test_bad_exercise_answers_and_option_lists_are_rejected(self):
        for key, value in [("answer", None), ("accepted", 42), ("options", 42),
                           ("accepted", [None]), ("options", [False])]:
            def change(data):
                data["exercises"][0][key] = value
                return data
            with self.subTest(key=key, value=value):
                self.assert_rejected("seed_lessons/a1_w01_l01_nouns.yaml", change)

    def test_bad_poem_exercises_are_rejected(self):
        for key, value in [("gaps", [42]), ("gaps", [{"line": 0, "word": "nice"}]),
                           ("gaps", [{"line": 999, "word": "phone"}]),
                           ("gaps", [{"line": 1, "word": ""}]), ("pronunciation", [42]),
                           ("pronunciation", [{"ipa": None}])]:
            with self.subTest(key=key, value=value):
                self.assert_rejected("seed_poems/p01_my_new_home.yaml", lambda d: {**d, key: value})

    def test_false_twister_values_cannot_delete_existing_twisters(self):
        for value in [[], False, 0, "", {}]:
            with self.subTest(value=value):
                self.assert_rejected("seed_weeks/a1_w01.yaml", lambda d: {**d, "twister": value})

    def test_unknown_week_cannot_make_units_known_before_their_time(self):
        for file in ["seed_lexicon/a1_w01_core.yaml", "seed_lessons/a1_w01_l01_nouns.yaml"]:
            with self.subTest(file=file):
                self.assert_rejected(file, lambda d: {**d, "week": 999})
