"""The pilot must expose reviewed content and only conservative recall evidence."""
import importlib
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings


class VocabularyTrainerContentTests(SimpleTestCase):
    def content_module(self):
        self.assertIsNotNone(
            importlib.util.find_spec("apps.learning.trainer_content"),
            "Reviewed pilot content loader is not implemented",
        )
        return importlib.import_module("apps.learning.trainer_content")

    def test_pilot_is_exactly_three_existing_senses_after_lesson_five(self):
        content = self.content_module()
        pilot = content.pilot_content()
        self.assertEqual(content.UNIT_UIDS, ("LX-00055", "LX-00285", "LX-00084"))
        self.assertEqual([u["uid"] for u in pilot["units"]], list(content.UNIT_UIDS))
        self.assertEqual(pilot["prerequisites"], {
            "lesson_slug": "a1-cafe-order", "lesson_order": 5, "week": 3,
            "exposure_only": True,
        })
        for unit in pilot["units"]:
            self.assertEqual(unit["source"]["lesson"], "content/seed_lessons/a1_w03_l05_cafe.yaml")
            expected = "a1_w03_cafe_plus.yaml" if unit["uid"] == "LX-00285" else "a1_w03_pilot.yaml"
            self.assertEqual(unit["source"]["lexicon"], "content/seed_lexicon/" + expected)
            self.assertEqual(unit["prerequisites"], pilot["prerequisites"])
            for field in ("explanation", "mnemonic", "reviewer_note"):
                self.assertTrue(unit[field].strip())
            self.assertEqual(unit["mnemonic_review"], "ai_reviewed_not_human_validated")
            self.assertGreaterEqual(len(unit["examples"]), 2)
            self.assertEqual(unit["spoken"]["evidence"], "self_report_only")
            self.assertIsNone(unit["spoken"]["audio"])

    def test_each_unit_has_two_stable_distinct_families_and_ungraded_application(self):
        pilot = self.content_module().pilot_content()
        task_ids = []
        for unit in pilot["units"]:
            tasks = unit["recall_tasks"]
            self.assertEqual(len(tasks), 2)
            self.assertEqual(len({t["family_id"] for t in tasks}), 2)
            self.assertEqual(len({t["prompt"] for t in tasks}), 2)
            for task in tasks:
                task_ids.append(task["task_id"])
                self.assertIn(task["model"], task["accepted"])
                self.assertTrue(task["meaning_errors"])
            self.assertEqual(len(unit["applications"]), 2)
            for task in unit["applications"]:
                task_ids.append(task["task_id"])
                self.assertTrue(task["criteria"])
                self.assertGreaterEqual(len(task["valid_examples"]), 3)
                self.assertNotIn("accepted", task)
                self.assertEqual(task["assessment"], "self_report_only")
        self.assertEqual(len(task_ids), len(set(task_ids)))

    def test_normalization_tolerates_cosmetics_but_preserves_meaning(self):
        normalize = self.content_module().normalize_answer
        for answer, expected in (
            ("  I’d   like a coffee, please!  ", "i'd like a coffee please"),
            ("Sorry? Can you say it again, please?", "sorry can you say it again please"),
            ("I don't like tea.", "i don't like tea"),
            ("tea-time", "tea-time"),
            ("I'd", "i'd"),
            ("Id", "id"),
        ):
            with self.subTest(answer=answer):
                self.assertEqual(normalize(answer), expected)
        self.assertNotEqual(normalize("I don't like tea"), normalize("I do like tea"))
        self.assertNotEqual(normalize("tea-time"), normalize("tea time"))

    def test_tea_word_task_accepts_only_reviewed_word(self):
        content = self.content_module()
        unit = content.unit_content("LX-00055")
        for answer, outcome in (("TEA!", "correct"), ("coffee", "incorrect"),
                                ("Tea, please.", "uncertain"), ("chai", "uncertain"),
                                ("I don't want tea", "uncertain")):
            with self.subTest(answer=answer):
                result = content.assess_recall(unit, answer)
                self.assertEqual(result["outcome"], outcome)
                self.assertEqual(result["target_used"], outcome == "correct")
                self.assertEqual(result["canonical_answer"], "tea")
                self.assertTrue(result["feedback"])

    def test_polite_order_accepts_taught_contractions_and_distinguishes_goal(self):
        content = self.content_module()
        unit = content.unit_content("LX-00285")
        for answer in ("I'd like a coffee, please.", "I would like a coffee, please.",
                       "I’d like a tea, please.", "I would like tea, please."):
            with self.subTest(answer=answer):
                result = content.assess_recall(unit, answer)
                self.assertEqual(result["outcome"], "correct")
                self.assertTrue(result["target_used"])
                self.assertTrue(result["goal_achieved"])
        for answer in ("Tea, please.", "Can I have a coffee, please?"):
            result = content.assess_recall(unit, answer)
            self.assertEqual(result["outcome"], "uncertain")
            self.assertTrue(result["goal_achieved"])
            self.assertFalse(result["target_used"])
        for answer in ("I like coffee.", "I don't like coffee."):
            self.assertEqual(content.assess_recall(unit, answer)["outcome"], "incorrect")
        for answer in ("May I please have some tea?", "Id like a coffee please", "I'd like a coffee without milk"):
            self.assertEqual(content.assess_recall(unit, answer)["outcome"], "uncertain")

    def test_repeat_requires_full_reviewed_phrase_not_keyword(self):
        content = self.content_module()
        unit = content.unit_content("LX-00084")
        for answer in ("Sorry? Can you say it again, please?", "Can you say it again, please?",
                       "Can you please say it again?"):
            self.assertEqual(content.assess_recall(unit, answer)["outcome"], "correct")
        for answer in ("again", "Sorry?", "Would you mind repeating that?", "Don't say it again, please.", "Can you say it, please?", "Could you say it again, please?"):
            self.assertEqual(content.assess_recall(unit, answer)["outcome"], "uncertain")
        self.assertEqual(content.assess_recall(unit, "I can say it again, please.")["outcome"], "incorrect")

    def test_selected_task_controls_which_goal_is_reviewed(self):
        content = self.content_module()
        unit = content.unit_content("LX-00055")
        task_id = unit["recall_tasks"][1]["task_id"]
        result = content.assess_recall(unit, "tea", task_id=task_id)
        self.assertEqual(result["task_id"], task_id)
        with self.assertRaises(ValueError):
            content.assess_recall(unit, "tea", task_id="nonexistent-task")

    def test_unknown_and_blank_are_not_fabricated_language_errors(self):
        content = self.content_module()
        unit = content.unit_content("LX-00285")
        for answer in ("", " ", "Another natural answer", "Мне tea, please"):
            result = content.assess_recall(unit, answer)
            self.assertEqual(result["outcome"], "uncertain")
            self.assertIsNone(result["goal_achieved"])
            self.assertFalse(result["target_used"])

    def test_consumers_cannot_mutate_shared_content(self):
        content = self.content_module()
        unit = content.unit_content("LX-00055")
        unit["recall_tasks"][0]["accepted"].append("coffee")
        self.assertEqual(content.assess_recall(content.unit_content("LX-00055"), "coffee")["outcome"], "incorrect")
        with self.assertRaises(KeyError):
            content.unit_content("LX-99999")

    def load_changed_document(self, mutate):
        content = self.content_module()
        document = content.pilot_content()
        mutate(document)
        with tempfile.TemporaryDirectory() as directory:
            manifests = Path(directory) / "manifests"
            manifests.mkdir()
            (manifests / "a1_vocabulary_trainer.json").write_text(json.dumps(document), encoding="utf-8")
            with override_settings(CONTENT_DIR=Path(directory)):
                return content.pilot_content()

    def test_missing_editorial_material_or_ambiguous_keys_fail_closed(self):
        for mutate in (
            lambda d: d["units"][0].update(mnemonic=""),
            lambda d: d["units"][0].update(mnemonic_review="pending"),
            lambda d: d["units"][0].update(applications=[]),
            lambda d: d["units"][0]["recall_tasks"][1].update(family_id=d["units"][0]["recall_tasks"][0]["family_id"]),
            lambda d: d["units"][0]["recall_tasks"][0]["accepted"].append("coffee"),
            lambda d: d["units"][0]["applications"][0].update(accepted=["tea"]),
            lambda d: d["units"].pop(),
        ):
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.load_changed_document(mutate)

    def test_malformed_version_maps_and_duplicate_application_situations_fail_closed(self):
        def invented_initial(document):
            document["content_version"] = "2.0"
            document["assessment_revision"] = "2"
            document["compatibility"]["2.0"] = {
                "change": "initial", "assessment_revision": "2",
                "compatible_with": [], "task_mapping": {}, "history_policy": "preserve",
            }
        def malformed_reference(document):
            document["compatibility"]["bad"] = []
            document["compatibility"]["1.0"].update(change="cosmetic", compatible_with=["bad"])
        def duplicate_situation(document):
            tasks = document["units"][0]["applications"]
            tasks[1]["prompt"] = tasks[0]["prompt"]
        for mutate in (invented_initial, malformed_reference, duplicate_situation):
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.load_changed_document(mutate)

    def test_version_mapping_allows_cosmetic_continuity_only_explicitly(self):
        def cosmetic(document):
            document["content_version"] = "1.0.1"
            document["compatibility"]["1.0.1"] = {
                "change": "cosmetic", "assessment_revision": "1",
                "compatible_with": ["1.0"], "task_mapping": {},
                "history_policy": "preserve",
            }
        document = self.load_changed_document(cosmetic)
        self.assertEqual(document["compatibility"]["1.0.1"]["compatible_with"], ["1.0"])
        with self.assertRaises(ValueError):
            self.load_changed_document(lambda d: d.update(content_version="unmapped"))
        def disguised_assessment(document):
            cosmetic(document)
            document["compatibility"]["1.0.1"]["assessment_revision"] = "2"
        with self.assertRaises(ValueError):
            self.load_changed_document(disguised_assessment)

    def test_assessment_revision_needs_explicit_task_map_and_preserves_history(self):
        def revision(document):
            document["content_version"] = "2.0"
            document["assessment_revision"] = "2"
            document["compatibility"]["2.0"] = {
                "change": "assessment", "assessment_revision": "2",
                "compatible_with": [], "task_mapping": {}, "history_policy": "preserve",
            }
        with self.assertRaises(ValueError):
            self.load_changed_document(revision)
        def mapped_revision(document):
            revision(document)
            document["compatibility"]["2.0"]["task_mapping"] = {"old-task": "tea-drink-name"}
        document = self.load_changed_document(mapped_revision)
        self.assertEqual(document["compatibility"]["2.0"]["history_policy"], "preserve")
        with self.assertRaises(ValueError):
            self.load_changed_document(lambda d: d["compatibility"]["1.0"].update(history_policy="regrade"))
