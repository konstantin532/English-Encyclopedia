"""Machine-checkable 516-unit / 28-lesson editorial contracts.

Passing this file does not confirm naturalness, pronunciation, CEFR level,
or the semantic adequacy of translations. Those need independent review.
"""
import re
from collections import Counter
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase

from apps.drills.models import Exercise, loose_normalize

CONTENT = Path(settings.BASE_DIR) / "content"
MARKER = re.compile(r"\[[^\]]+\]")
EN_NEGATION = re.compile(r"\b(?:no|not|never|cannot|don't|doesn't|can't|isn't|aren't)\b", re.I)
RU_NEGATION = re.compile(r"(?:^|[\s,.;:«—])(?:не|нет|никогда|нельзя|без)(?=$|[\s,.;:»!?])", re.I)


def plain(value):
    return MARKER.sub("", str(value)).replace("’", "'").casefold()


def demonstrates_target(example, candidates, unit_type):
    example = plain(example)
    if unit_type == "phrase":
        # A conversational contraction still demonstrates the same phrase.
        # Keep every content word and require complete token boundaries.
        example = f" {loose_normalize(example)} "
        candidates = [loose_normalize(form) for form in candidates]
        return any(form and f" {form} " in example for form in candidates)
    return any(form and form in example for form in candidates)


def corpus(directory):
    for path in sorted((CONTENT / directory).glob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        if record.get("level") == "A1":
            yield path, record


class A1CorpusAlignmentTests(SimpleTestCase):
    def test_500_entries_demonstrate_the_target_lemma_or_declared_form(self):
        seen = []
        for path, packet in corpus("seed_lexicon"):
            for unit in packet["units"]:
                uid = unit["uid"]
                seen.append(uid)
                # An alphabetical series is ONE explicit teaching unit; the
                # illustrative excerpt deliberately does not repeat all 26 letters.
                if uid == "LX-00187":
                    self.assertIn("A, B, C, D, E, F, G", unit["example_en"])
                    continue
                forms = unit.get("forms") or []
                self.assertIsInstance(forms, list, f"{path.name} {uid}")
                target = unit["lemma"].casefold().rstrip(".!?")
                examples = plain(unit["example_en"])
                candidates = [target, *(str(form).casefold() for form in forms)]
                with self.subTest(uid=uid):
                    self.assertTrue(
                        demonstrates_target(examples, candidates, unit.get("unit_type")),
                        f"{path.name}: {uid} ({unit['lemma']}) not demonstrated in {examples!r}"
                    )
        self.assertEqual(len(seen), 516)
        self.assertEqual(len(set(seen)), 516)

    def test_phrase_demonstration_accepts_contractions_and_preserves_target_words(self):
        cases = (
            ("What is your name?", "What's your name?", "What's your address?"),
            ("I am from Russia.", "I'm from Russia.", "I'm from Canada."),
            ("I am your neighbor.", "I'm your neighbor.", "I'm your teacher."),
            ("That is your room.", "That's your room.", "That's my room."),
            ("It is not my box.", "It's not my box.", "It's my box."),
            ("You are welcome.", "You're welcome.", "You're late."),
            ("Who is this?", "Who's this?", "Who's that?"),
            ("Here is your photo.", "Here's your photo.", "Here's my photo."),
            ("I am happy!", "I'm happy!", "I'm unhappy!"),
            ("What is the address?", "What's the address?", "What's the name?"),
        )
        for target, contracted, changed_meaning in cases:
            with self.subTest(target=target):
                self.assertTrue(demonstrates_target(target, [target], "phrase"))
                self.assertTrue(demonstrates_target(contracted, [target], "phrase"))
                self.assertFalse(demonstrates_target(changed_meaning, [target], "phrase"))
        self.assertTrue(demonstrates_target(
            "[T8]I[/][D1]'m[/] [J4]happy[/]!", ["I am happy!"], "phrase"
        ))
        self.assertFalse(demonstrates_target("I'm happyish.", ["I am happy"], "phrase"))

    def test_word_demonstration_still_requires_the_target_or_a_declared_form(self):
        self.assertTrue(demonstrates_target("He went home.", ["go", "went"], "word"))
        self.assertFalse(demonstrates_target("He went home.", ["go"], "word"))
        self.assertFalse(demonstrates_target("I'm happy.", ["am"], "word"))

    def test_500_examples_preserve_explicit_negation_in_russian(self):
        checked = 0
        for path, packet in corpus("seed_lexicon"):
            for unit in packet["units"]:
                checked += 1
                source = plain(unit["example_en"])
                if EN_NEGATION.search(source):
                    with self.subTest(uid=unit["uid"]):
                        self.assertRegex(
                            unit["example_ru"], RU_NEGATION,
                            f"{path.name}: {unit['uid']} negative {source!r} "
                            "requires a semantically negative Russian translation"
                        )
        self.assertEqual(checked, 516)

    def test_28_lessons_and_163_exercises_have_solvable_unambiguous_keys(self):
        lesson_count = 0
        question_count = 0
        for path, lesson in corpus("seed_lessons"):
            lesson_count += 1
            self.assertEqual(
                [layer["number"] for layer in lesson["layers"]],
                list(range(1, 8)), path.name
            )
            for exercise in lesson["exercises"]:
                question_count += 1
                options = exercise.get("options", [])
                answer = exercise["answer"]
                with self.subTest(lesson=lesson["slug"], order=exercise["order"]):
                    if exercise["kind"] == "choice":
                        self.assertEqual(
                            len(set(Exercise.normalize(option) for option in options)),
                            len(options), "Equivalent choices make a question ambiguous"
                        )
                        self.assertIn(
                            Exercise.normalize(answer),
                            [Exercise.normalize(option) for option in options],
                        )
                    elif exercise["kind"] == "build":
                        # Counter, not set: repeated I/the/etc. must each exist
                        # as separate draggable tiles.
                        expected = Counter(
                            Exercise.normalize(word) for word in answer.split()
                        )
                        available = Counter(
                            Exercise.normalize(word) for word in options
                        )
                        self.assertEqual(
                            expected, available,
                            f"Cannot build {answer!r} from {options!r}"
                        )
                    else:
                        self.assertEqual(exercise["kind"], "fill")
                        self.assertTrue(answer.strip())
        self.assertEqual(lesson_count, 28)
        self.assertEqual(question_count, 163)
