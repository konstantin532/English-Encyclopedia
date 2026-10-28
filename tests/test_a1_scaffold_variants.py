"""Beginner editorial scaffolds, independently varied transfer, and honest reflection."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import override_settings

from django.conf import settings
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.test.html import parse_html
from django.urls import reverse

from apps.accounts.models import User
from apps.learning.models import IndependentAttempt, UnitProgress
from apps.learning.understanding import scaffold_bank, understanding_bank
from apps.lessons.models import Lesson
from tests.runner import ensure_content


def elements(node):
    for child in node.children:
        if not isinstance(child, str):
            yield child
            yield from elements(child)


class ThreeStepEditorialTests(SimpleTestCase):
    def test_each_a1_lesson_has_three_specific_steps_and_distinct_transfer(self):
        rows = scaffold_bank()
        self.assertEqual(len(rows), 28)
        self.assertEqual(sum(len(r["steps"]) for r in rows.values()), 84)
        guides = understanding_bank()
        self.assertEqual(set(rows), set(guides))
        for slug, guide in guides.items():
            with self.subTest(slug=slug):
                self.assertEqual(len(guide["steps"]), 3)
                self.assertEqual(len(guide["transfer_variants"]), 2)
                for fresh in guide["transfer_variants"]:
                    self.assertNotEqual(
                        fresh["prompt"], guide["tasks"]["transfer"]["prompt"])
                    self.assertNotIn("accepted", fresh)
                    self.assertNotIn("options", fresh)
                    self.assertNotEqual(fresh["prompt"], fresh["model"])
                self.assertEqual(len({
                    t["prompt"] for t in (
                        guide["tasks"]["transfer"], *guide["transfer_variants"]
                    )
                }), 3)
                self.assertGreaterEqual(
                    len({step["example_en"] for step in guide["steps"]}), 3)

    def test_editors_cannot_add_leaked_keys_or_duplicate_transfer_tasks(self):
        original = settings.CONTENT_DIR / "manifests"
        basic = (original / "a1_understanding_checks.json").read_text("utf-8")
        data = json.loads((original / "a1_scaffold_transfer.json").read_text("utf-8"))
        for mutation in ("answer_in_prompt", "duplicate", "wrong_count"):
            with self.subTest(mutation=mutation), TemporaryDirectory() as tmp:
                folder = Path(tmp) / "manifests"
                folder.mkdir()
                (folder / "a1_understanding_checks.json").write_text(
                    basic, encoding="utf-8")
                broken = json.loads(json.dumps(data))
                if mutation == "answer_in_prompt":
                    broken["lessons"][0]["transfer_variants"][0]["accepted"] = [
                        "Do not leak accepted answers."
                    ]
                elif mutation == "duplicate":
                    broken["lessons"][0]["transfer_variants"][1]["prompt"] = (
                        broken["lessons"][0]["transfer_variants"][0]["prompt"]
                    )
                else:
                    broken["lessons"][0]["transfer_variants"].pop()
                (folder / "a1_scaffold_transfer.json").write_text(
                    json.dumps(broken), encoding="utf-8")
                with override_settings(CONTENT_DIR=Path(tmp)):
                    with self.assertRaises(ValueError):
                        scaffold_bank()

    def test_eight_fine_grained_editorial_corrections(self):
        bank = understanding_bank()
        noun = bank["a1-nouns-first-words"]["steps"]
        self.assertIn("исчисляемым", noun[0]["why_ru"])
        definite = bank["a1-determiners-a-the-this-my"]["steps"]
        self.assertEqual(definite[1]["example_ru"], "Ключ здесь.")
        water = bank["a1-there-is-some"]["steps"]
        self.assertIn("не обязательно", water[1]["why_ru"])
        self.assertEqual(water[1]["example_ru"], "Есть вода.")
        numbers = bank["a1-numbers-1-20"]["steps"]
        self.assertEqual(numbers[1]["example_en"], "three books")
        self.assertEqual(numbers[2]["example_en"], "I need three books.")
        spelling = bank["a1-spelling-phone-numbers"]["steps"]
        self.assertEqual(spelling[1]["example_en"], "M-I-A")
        habits = bank["a1-always-never"]["steps"]
        self.assertIn("Sundays", habits[2]["example_en"])
        directions = bank["a1-directions-turn-left"]["steps"]
        self.assertIn("стоять", directions[2]["why_ru"])
        origin = bank["a1-review-everything"]["steps"]
        self.assertIn("глагола be", origin[0]["why_ru"])

    def test_micro_review_explanations_keep_relevant_true_rules(self):
        guides = understanding_bank()
        # Independent examples must not teach false bans on valid constructions.
        self.assertIn("like to read", " ".join(
            x["example_en"] for x in guides["a1-like-doing"]["steps"]))
        self.assertIn("Does he work", " ".join(
            x["example_en"] for x in guides["a1-he-she-works"]["steps"]))
        self.assertIn("There is some water", " ".join(
            x["example_en"] for x in guides["a1-there-is-some"]["steps"]))

    def test_editorial_incidents_stay_fixed_in_context_and_grammar(self):
        guides = understanding_bank()
        third_person = guides["a1-he-she-works"]
        for item in (third_person["tasks"]["transfer"], *third_person["transfer_variants"]):
            self.assertIn("Does ", item["model"])
            self.assertNotIn("Do you ", item["model"])
        numbers = guides["a1-numbers-1-20"]
        self.assertIn("cookies", numbers["transfer_variants"][1]["model"])
        self.assertNotIn("tickets", numbers["transfer_variants"][0]["model"])
        address = guides["a1-letters-address"]["tasks"]["transfer"]["model"]
        self.assertEqual(address, "5 Park Street")
        # No grammar checker can replace an editor, but these caught defects
        # should never be silently reintroduced.
        self.assertIn("like to read", " ".join(
            x["example_en"] for x in guides["a1-like-doing"]["steps"]))
        self.assertTrue(guides["a1-review-everything"]["transfer_variants"][0]["model"].endswith("?"))

    def test_fifth_pass_questions_match_speaker_and_situation(self):
        guides = understanding_bank()
        # In third-person questions, the learner addresses Tom/the colleague,
        # not the woman whom the question is about.
        mia = guides["a1-questions-do-does"]["transfer_variants"][1]
        self.assertIn("Спросите у Тома", mia["prompt"])
        self.assertTrue(mia["model"].startswith("Does Mia "))
        colleague = guides["a1-he-she-works"]["transfer_variants"][0]
        self.assertIn("коллегу", colleague["prompt"])
        self.assertTrue(colleague["model"].startswith("Does Anna "))
        # Being here is not the same as the speaker owning the book.
        book = guides["a1-determiners-a-the-this-my"]["transfer_variants"][0]
        self.assertIn("находится здесь", book["prompt"])
        self.assertEqual(book["model"], "The book is here.")
        water = guides["a1-there-is-some"]["tasks"]["transfer"]
        self.assertIn("есть ли вода", water["prompt"])
        # The ordinary presence question does not require any. That word is
        # not introduced in A1 week5; lexical prerequisites are checked by
        # the shared 9–12 behavioral suite, rather than forced by this shape test.
        question = water["model"].split("?", 1)[0] + "?"
        self.assertRegex(question, r"^Is there (?:some |any )?water\?$")
        self.assertIn("some water", water["model"])

    def test_phone_readability_and_accessibility_contracts(self):
        css = (Path(settings.BASE_DIR) / "static/css/independent-check.css").read_text("utf-8")
        for rule in ("max-width: 430px", "min-height: 52px",
                     "focus-visible", "forced-colors: active",
                     "prefers-reduced-motion: reduce", "prefers-contrast: more",
                     "safe-area-inset-left", "safe-area-inset-right",
                     "independent-form-error:focus",
                     "overflow-wrap: anywhere", "font-size: max(1rem, 16px)"):
            with self.subTest(rule=rule):
                self.assertIn(rule, css)


class RotatingIndependentReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.student = User.objects.create_user(
            email="new-transfer@example.test", password="LongTestPass123!")
        self.other = User.objects.create_user(
            email="new-transfer-other@example.test", password="LongTestPass123!")
        self.lesson = Lesson.objects.get(level__code="A1", order=13)
        self.url = reverse("learning:independent_check", args=[self.lesson.slug])
        self.client.force_login(self.student)

    def batch(self, variant=None):
        page = self.client.get(self.url)
        guide = page.context["guide"]
        current = page.context["transfer_variant"]
        answers = {"action": "batch", "assistance": "no_help",
                   "batch_token": page.context["batch_token"],
                   **{"answer_" + key: guide["tasks"][key]["model"]
                      for key in ("meaning", "writing", "transfer", "explain")}}
        if variant is not None:
            answers["transfer_variant"] = str(variant)
        return self.client.post(self.url, answers)

    def test_all_28_lessons_keep_minute_card_core_and_optional_independent_review(self):
        lessons = Lesson.objects.filter(level__code="A1")
        self.assertEqual(lessons.count(), 28)
        for lesson in lessons:
            with self.subTest(lesson=lesson.order):
                response = self.client.get(
                    reverse("lessons:detail", args=[lesson.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="beginner-steps"', count=1)
                self.assertContains(response, '<h2 id="a1-clarity-title">Понять за минуту — без сложных терминов</h2>', count=1, html=True)
                self.assertNotContains(response, 'class="a1-step-list"')
                self.assertNotContains(response, 'class="a1-step-en"')
                self.assertNotContains(response, "Разобрать ещё проще")
                self.assertContains(response, 'data-a1-full-lesson')
                self.assertNotContains(response, 'data-a1-route-mode')
                articles = [node for node in elements(parse_html(response.content.decode())) if node.name == "article"]
                self.assertEqual(len(articles), 1)
                blocks = [node for node in articles[0].children if not isinstance(node, str)]
                self.assertEqual(
                    [(node.name, dict(node.attributes).get("id")) for node in blocks],
                    [("section", "beginner-steps"), ("div", None),
                     ("section", "practice"), ("section", "translate"),
                     ("section", "lesson-complete"),
                     ("details", "lesson-extra-practice")],
                )
                self.assertIn("data-lesson-reader", dict(blocks[1].attributes))
                completion, extra = blocks[-2:]
                self.assertIn(parse_html('<h2 id="lesson-complete-title">Урок пройден ✓</h2>'), completion)
                self.assertNotIn("open", dict(extra.attributes))
                self.assertEqual(extra.children[0], parse_html("<summary>Ещё практика (по желанию)</summary>"))
                self.assertIn(parse_html('<h2>Проверка без готовых ответов</h2>'), extra)
                self.assertIn(parse_html(f'<a class="btn btn-primary" href="{reverse("learning:independent_check", args=[lesson.slug])}">Проверить себя самостоятельно →</a>'), extra)
                self.assertEqual(sum(dict(node.attributes).get("id") == "spoken-coach" for node in elements(extra)), 1)

    def test_baseline_then_fresh_transfer_are_rotated_only_after_full_batch(self):
        before = self.client.get(self.url)
        self.assertEqual(before.context["transfer_variant"], 0)
        baseline = before.context["guide"]["tasks"]["transfer"]["prompt"]
        self.assertEqual(before.context["transfer_variant_total"], 3)
        result = self.batch(variant=0)
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, "Разбор всех четырёх ответов")
        saved = IndependentAttempt.objects.get(
            user=self.student, skill="transfer")
        self.assertEqual(saved.task_variant, 0)

        after = self.client.get(self.url)
        self.assertEqual(after.context["transfer_variant"], 1)
        self.assertNotEqual(after.context["guide"]["tasks"]["transfer"]["prompt"], baseline)
        self.assertEqual(
            self.client.post(self.url, {"action": "batch", "transfer_variant": "0"}).status_code,
            400)
        second = self.batch(variant=1)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.context["transfer_variant"], 2)
        self.assertEqual(second.context["guide"]["tasks"]["transfer"]["prompt"],
                         understanding_bank()[self.lesson.slug]["transfer_variants"][1]["prompt"])
        self.assertEqual(IndependentAttempt.objects.filter(
            user=self.student, skill="transfer", task_variant=1).count(), 1)
        self.assertEqual(self.client.get(self.url).context["transfer_variant"], 2)
        self.assertEqual(self.batch(variant=2).status_code, 200)
        self.assertEqual(self.client.get(self.url).context["transfer_variant"], 0)
        self.assertFalse(UnitProgress.objects.filter(user=self.student).exists())

    def test_mobile_double_tap_replay_cannot_duplicate_a_full_batch(self):
        page = self.client.get(self.url)
        guide = page.context["guide"]
        token = page.context["batch_token"]
        form = {"action": "batch", "assistance": "no_help", "batch_token": token,
                "transfer_variant": str(page.context["transfer_variant"]),
                **{"answer_" + skill: guide["tasks"][skill]["model"]
                   for skill in ("meaning", "writing", "transfer", "explain")}}
        first = self.client.post(self.url, form)
        self.assertEqual(first.status_code, 200)
        self.assertNotContains(first, 'data-blind-batch')
        self.assertNotContains(first, 'name="answer_transfer"')
        self.assertContains(first, 'Начать следующую независимую попытку')
        self.assertEqual(first.context["transfer_variant"], 1)
        self.assertEqual(first.context["guide"]["tasks"]["transfer"]["prompt"],
                         understanding_bank()[self.lesson.slug]["transfer_variants"][0]["prompt"])
        self.assertNotEqual(first.context["batch_token"], token)
        replay = self.client.post(self.url, form)
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.student).count(), 4)

    def test_database_itself_prevents_concurrent_duplicate_batch_rows(self):
        self.assertEqual(self.batch(variant=0).status_code, 200)
        saved = IndependentAttempt.objects.get(
            user=self.student, skill="transfer")
        self.assertTrue(saved.batch_token)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IndependentAttempt.objects.create(
                    user=self.student, lesson=self.lesson, skill="transfer",
                    submitted="A repeated message", outcome=saved.outcome,
                    batch_token=saved.batch_token, task_variant=0)
        self.assertEqual(IndependentAttempt.objects.filter(
            user=self.student, skill="transfer").count(), 1)

    def test_missing_token_cannot_bypass_database_idempotency(self):
        guide = self.client.get(self.url).context["guide"]
        res = self.client.post(self.url, {"action": "batch", "transfer_variant": "0",
            **{"answer_" + k: guide["tasks"][k]["model"]
               for k in ("meaning", "writing", "transfer", "explain")}})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())

    def test_mobile_error_keeps_entered_text_and_hides_answer_keys(self):
        page = self.client.get(self.url)
        original = "My own detailed answer on a narrow Android screen"
        invalid = self.client.post(self.url, {
            "action": "batch", "assistance": "no_help", "batch_token": page.context["batch_token"],
            "transfer_variant": str(page.context["transfer_variant"]),
            "answer_meaning": original, "answer_writing": "I am here.",
            "answer_transfer": "I have a book.", "answer_explain": "",
        })
        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, original, status_code=400)
        self.assertContains(invalid, 'role="alert"', status_code=400)
        self.assertContains(invalid, "Ответы пока не сохранены", status_code=400)
        self.assertNotContains(invalid, "Один возможный образец", status_code=400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())

    def test_invalid_mobile_form_escapes_user_supplied_html(self):
        page = self.client.get(self.url)
        attack = "<script>alert(1)</script>"
        bad = self.client.post(self.url, {
            "action": "batch", "assistance": "no_help", "batch_token": page.context["batch_token"],
            "transfer_variant": str(page.context["transfer_variant"]),
            "answer_meaning": attack, "answer_writing": "I am here.",
            "answer_transfer": "I read.", "answer_explain": "",
        })
        self.assertEqual(bad.status_code, 400)
        self.assertNotContains(bad, attack, status_code=400)
        self.assertContains(bad, "&lt;script&gt;", status_code=400)

    def test_disclosure_is_required_recorded_and_is_not_verified(self):
        page = self.client.get(self.url)
        t = page.context["guide"]["tasks"]
        base = {"action": "batch", "batch_token": page.context["batch_token"],
                "transfer_variant": str(page.context["transfer_variant"]),
                **{"answer_" + k: t[k]["model"] for k in
                   ("meaning", "writing", "transfer", "explain")}}
        self.assertEqual(self.client.post(self.url, base).status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())
        base["assistance"] = "translator"
        ok = self.client.post(self.url, base)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(set(IndependentAttempt.objects.filter(
            user=self.student).values_list("assistance", flat=True)), {"translator"})
        self.assertContains(ok, "С онлайн-переводчиком")
        self.assertFalse(UnitProgress.objects.filter(user=self.student).exists())

    def test_revisited_context_is_not_claimed_as_fresh(self):
        start = self.client.get(self.url)
        self.assertFalse(start.context["transfer_variant_seen"])
        self.assertEqual(self.batch(variant=0).status_code, 200)
        self.assertEqual(self.batch(variant=1).status_code, 200)
        self.assertEqual(self.batch(variant=2).status_code, 200)
        page = self.client.get(self.url)
        self.assertTrue(page.context["transfer_variant_seen"])
        self.assertContains(page, "Это повторная ситуация")
        self.assertNotContains(page, "Эта ситуация ещё не встречалась")

    def test_cannot_claim_independence_after_declaring_translation_help(self):
        page = self.client.get(self.url)
        t = page.context["guide"]["tasks"]
        form = {"action": "batch", "assistance": "translator",
                "batch_token": page.context["batch_token"],
                "transfer_variant": str(page.context["transfer_variant"]),
                **{"answer_" + k: t[k]["model"]
                   for k in ("meaning", "writing", "transfer", "explain")}}
        self.assertEqual(self.client.post(self.url, form).status_code, 200)
        item = IndependentAttempt.objects.get(user=self.student, skill="transfer")
        forbidden = self.client.post(self.url, {
            "action": "rubric", "attempt_id": item.pk,
            "rubric_meaning": "yes", "rubric_form": "yes",
            "rubric_context": "yes", "rubric_independence": "independent"})
        self.assertEqual(forbidden.status_code, 400)
        item.refresh_from_db()
        self.assertFalse(item.self_rubric)
        acceptable = self.client.post(self.url, {
            "action": "rubric", "attempt_id": item.pk,
            "rubric_meaning": "yes", "rubric_form": "yes",
            "rubric_context": "yes", "rubric_independence": "helped"})
        self.assertEqual(acceptable.status_code, 200)

    def test_one_letter_explanation_does_not_count_as_independent_reasoning(self):
        page = self.client.get(self.url)
        t = page.context["guide"]["tasks"]
        form = {"action": "batch", "assistance": "no_help",
                "batch_token": page.context["batch_token"],
                "transfer_variant": str(page.context["transfer_variant"]),
                **{"answer_" + k: t[k]["model"]
                   for k in ("meaning", "writing", "transfer", "explain")}}
        form["answer_explain"] = "a"
        res = self.client.post(self.url, form)
        self.assertEqual(res.status_code, 400)
        self.assertContains(res, "от 10 символов", status_code=400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())

    def test_natural_contract_and_full_negative_are_not_marked_wrong(self):
        from apps.learning.understanding import model_agreement
        bank = understanding_bank()
        self.assertTrue(model_agreement(
            bank["a1-verb-be"]["tasks"]["writing"], "I'm at home."))
        self.assertTrue(model_agreement(
            bank["a1-cant-cannot"]["tasks"]["writing"], "I cannot work today."))
        self.assertTrue(model_agreement(
            bank["a1-like-doing"]["tasks"]["writing"],
            "I like to play the guitar."))

    def test_fake_token_is_rejected_without_saving_student_data(self):
        res = self.client.post(self.url, {"action": "batch",
                                           "batch_token": "not-issued-to-this-session"})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())

    def test_partial_batch_does_not_rotate_or_store_any_answers(self):
        page = self.client.get(self.url)
        result = self.client.post(self.url, {
            "action": "batch", "assistance": "no_help", "batch_token": page.context["batch_token"],
            "transfer_variant": "0", "answer_meaning": "Да",
            "answer_writing": "Hello", "answer_transfer": "",
            "answer_explain": "Понимаю правило"})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.client.get(self.url).context["transfer_variant"], 0)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.student).exists())

    def test_four_axis_reflection_never_changes_cefr_or_vocabulary(self):
        self.assertEqual(self.batch(variant=0).status_code, 200)
        attempt = IndependentAttempt.objects.get(user=self.student, skill="transfer")
        page = self.client.get(self.url)
        self.assertContains(page, 'name="answer_transfer"')
        invalid = self.client.post(self.url, {
            "action": "rubric", "attempt_id": attempt.pk,
            "rubric_meaning": "yes", "rubric_form": "magical",
            "rubric_context": "yes", "rubric_independence": "independent"})
        self.assertEqual(invalid.status_code, 400)
        attempt.refresh_from_db()
        self.assertEqual(attempt.self_rubric, {})
        accepted = self.client.post(self.url, {
            "action": "rubric", "attempt_id": attempt.pk,
            "rubric_meaning": "yes", "rubric_form": "partly",
            "rubric_context": "yes", "rubric_independence": "helped"})
        self.assertEqual(accepted.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.self_rubric,
                         {"meaning": "yes", "form": "partly",
                          "context": "yes", "independence": "helped"})
        self.assertEqual(attempt.self_rating, "helped")
        self.assertFalse(UnitProgress.objects.filter(user=self.student).exists())

    def test_rubric_has_accessible_radio_groups_and_does_not_leak_before_answer(self):
        initial = self.client.get(self.url)
        self.assertNotContains(initial, 'name="rubric_meaning"')
        self.assertNotContains(initial, "Один возможный образец")
        self.assertContains(initial, 'name="batch_token"')
        self.assertContains(initial, 'data-batch-submit')
        self.assertContains(initial, 'role="status"')
        self.assertContains(initial, 'js/independent-check.js')
        response = self.batch(variant=0)
        self.assertContains(response, 'name="rubric_meaning"', count=6)
        self.assertContains(response, 'name="rubric_form"', count=6)
        self.assertContains(response, 'name="rubric_context"', count=6)
        self.assertContains(response, 'name="rubric_independence"', count=6)
        self.assertContains(response, "Как у вас получилось?")
        self.assertNotContains(response, 'aria-describedby="prompt-transfer"')
        self.assertNotContains(response, 'name="answer_transfer"')
        self.assertContains(initial, 'aria-describedby="prompt-transfer count-transfer"')
        self.assertContains(response, 'lang="en"')

    def test_mobile_counters_and_distinct_rubrics_are_visible(self):
        first = self.client.get(self.url)
        self.assertContains(first, "id=\"count-transfer\"")
        self.assertContains(first, 'name="answer_transfer"')
        self.assertContains(first, "autocomplete=\"off\"")
        result = self.batch(variant=0)
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, "Самооценка: применение в ситуации")
        self.assertContains(result, "Самооценка: объяснение правила")
        self.assertContains(result, "Исходный вопрос:")

    def test_cross_user_cannot_read_or_rate_another_student(self):
        self.assertEqual(self.batch(variant=0).status_code, 200)
        attempt = IndependentAttempt.objects.get(user=self.student, skill="transfer")
        self.client.force_login(self.other)
        res = self.client.post(self.url, {
            "action": "rubric", "attempt_id": attempt.pk,
            "rubric_meaning": "yes", "rubric_form": "yes",
            "rubric_context": "yes", "rubric_independence": "independent"})
        self.assertEqual(res.status_code, 404)
        self.assertNotContains(self.client.get(self.url), attempt.submitted)
