"""Fifteen A1 editorial gates plus live independent-output and privacy tests."""
import json

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.learning.models import IndependentAttempt, UnitProgress, ExerciseAttempt
from apps.learning.understanding import understanding_bank, quality_gates, model_agreement
from tests.runner import ensure_content


class A1ClarityQualityGatesTests(SimpleTestCase):
    def test_fifteen_review_gates_cover_all_28_beginner_lessons(self):
        path = settings.CONTENT_DIR / "manifests" / "a1_understanding_checks.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        checks = quality_gates(document)
        self.assertEqual(len(checks), 15)
        for name, good in checks.items():
            with self.subTest(gate=name):
                self.assertTrue(good)
        self.assertEqual(len(understanding_bank()), 28)
        self.assertEqual(sum(len(v["tasks"]) for v in understanding_bank().values()), 112)

    def test_missing_reason_fails_quality_gate(self):
        document = json.loads((settings.CONTENT_DIR / "manifests" /
                               "a1_understanding_checks.json").read_text(encoding="utf-8"))
        document["lessons"][0]["why"] = ""
        self.assertFalse(quality_gates(document)["06_all_guide_sections"])
        self.assertFalse(quality_gates(document)["08_explicit_reason_length"])

    def test_missing_or_duplicate_meaning_contrast_fails_gate(self):
        document = json.loads((settings.CONTENT_DIR / "manifests" /
                               "a1_understanding_checks.json").read_text(encoding="utf-8"))
        document["lessons"][0]["contrast"]["b_en"] = document["lessons"][0]["contrast"]["a_en"]
        self.assertFalse(quality_gates(document)["11_examples_not_empty"])

    def test_explain_why_prompt_must_not_supply_the_rule(self):
        document = json.loads((settings.CONTENT_DIR / "manifests" /
                               "a1_understanding_checks.json").read_text(encoding="utf-8"))
        document["lessons"][0]["tasks"]["explain"]["prompt"] = (
            "Объясните, почему работает такая схема: " + document["lessons"][0]["pattern"]
        )
        self.assertFalse(quality_gates(document)["15_bounds_and_no_model_in_prompt"])

    def test_duplicate_slug_fails_audit(self):
        document = json.loads((settings.CONTENT_DIR / "manifests" /
                               "a1_understanding_checks.json").read_text(encoding="utf-8"))
        document["lessons"][0]["slug"] = document["lessons"][1]["slug"]
        self.assertFalse(quality_gates(document)["04_unique_slugs"])

    def test_free_transfer_can_never_be_automatically_marked_wrong(self):
        for lesson in understanding_bank().values():
            self.assertNotIn("accepted", lesson["tasks"]["transfer"])
            self.assertFalse(model_agreement(lesson["tasks"]["transfer"], lesson["tasks"]["transfer"]["model"]))
            self.assertFalse(model_agreement(lesson["tasks"]["transfer"], "Another natural answer."))


class A1IndependentAssessmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(
            email="independent@example.test", password="ExamplePassword123!"
        )
        self.client.force_login(self.user)
        self.lesson = Lesson.objects.get(level__code="A1", order=1)
        self.url = reverse("learning:independent_check", args=[self.lesson.slug])

    def test_all_28_lessons_render_clarity_bridge_without_deleting_layers(self):
        for lesson in Lesson.objects.filter(level__code="A1"):
            with self.subTest(lesson=lesson.order):
                response = self.client.get(reverse("lessons:detail", args=[lesson.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Понять за минуту")
                self.assertContains(response, "Почему работает?")
                self.assertContains(response, "Типичная ошибка")
                self.assertContains(response, "Как исправить")
                self.assertContains(response, "Проверить себя самостоятельно")
                self.assertContains(response, "Сравните — почему смысл меняется?")
                self.assertContains(response, "В чём разница:")
                for i in range(1, 8):
                    self.assertContains(response, f'id="layer-{i}"')

    def test_initial_independent_page_does_not_leak_any_of_four_models(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        bank = understanding_bank()[self.lesson.slug]
        self.assertContains(response, "Проверяю, что могу сам")
        self.assertContains(response, "Пишу сам")
        self.assertContains(response, "Переношу в новую ситуацию")
        self.assertNotContains(response, 'name="options"')
        self.assertNotContains(response, 'data-answer=')
        # Models are stored server-side; no correct text is rendered as key.
        self.assertNotContains(response, "Один возможный образец")
        for key in ("meaning", "writing", "transfer", "explain"):
            self.assertContains(response, 'name="answer_' + key + '"')

    def test_reasoning_and_error_fix_are_hidden_before_independent_attempt(self):
        initial = self.client.get(self.url)
        self.assertNotContains(initial, "Типичная ловушка:")
        self.assertNotContains(initial, "Как себя проверить:")
        sample = understanding_bank()[self.lesson.slug]["tasks"]["writing"]["model"]
        checked = self.client.post(self.url, {"skill": "writing", "answer": sample})
        self.assertEqual(checked.status_code, 200)
        self.assertContains(checked, "Типичная ловушка:")
        self.assertContains(checked, "Как себя проверить:")
        self.assertContains(checked, "Почему здесь так? Разобрать правило")

    def test_blind_full_attempt_shows_no_model_until_all_four_responses(self):
        guide = understanding_bank()[self.lesson.slug]
        form = {"action": "batch"}
        for key in ("meaning", "writing", "transfer", "explain"):
            form["answer_" + key] = guide["tasks"][key]["model"]
        initial = self.client.get(self.url)
        self.assertNotContains(initial, "Разбор всех четырёх ответов")
        self.assertNotContains(initial, "Один возможный образец")
        form["batch_token"] = initial.context["batch_token"]
        form["transfer_variant"] = str(initial.context["transfer_variant"])
        checked = self.client.post(self.url, form)
        self.assertEqual(checked.status_code, 200)
        self.assertContains(checked, "Разбор всех четырёх ответов")
        self.assertContains(checked, "Один возможный образец", count=4)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user).count(), 4)
        self.assertEqual(
            set(IndependentAttempt.objects.filter(user=self.user).values_list("skill", flat=True)),
            {"meaning", "writing", "transfer", "explain"},
        )
        self.assertFalse(UnitProgress.objects.filter(user=self.user).exists())

    def test_batch_rejects_partial_answers_without_saving_any(self):
        guide = understanding_bank()[self.lesson.slug]
        page = self.client.get(self.url)
        form = {"action": "batch", "batch_token": page.context["batch_token"],
                "transfer_variant": str(page.context["transfer_variant"]),
                "answer_meaning": guide["tasks"]["meaning"]["model"],
                "answer_writing": guide["tasks"]["writing"]["model"],
                "answer_transfer": "My own response", "answer_explain": ""}
        res = self.client.post(self.url, form)
        self.assertEqual(res.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.user).exists())
        form["answer_explain"] = "My own independent explanation"
        form["answer_transfer"] = "X" * 401
        res = self.client.post(self.url, form)
        self.assertEqual(res.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.user).exists())

    def test_own_model_phrase_is_recorded_as_agreement_not_cefr(self):
        t = understanding_bank()[self.lesson.slug]["tasks"]["writing"]
        response = self.client.post(self.url, {"skill": "writing", "answer": t["model"]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "совпал с подготовленным образцом")
        attempt = IndependentAttempt.objects.get(user=self.user)
        self.assertEqual(attempt.outcome, IndependentAttempt.Outcome.MODEL_MATCH)
        self.assertEqual(attempt.skill, "writing")
        self.assertFalse(UnitProgress.objects.filter(user=self.user).exists())
        self.assertFalse(ExerciseAttempt.objects.filter(user=self.user).exists())

    def test_open_but_different_response_is_not_falsely_graded_wrong(self):
        answer = "This is another possible way to say the same thing."
        response = self.client.post(self.url, {"skill": "writing", "answer": answer})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Он может быть допустимым")
        attempt = IndependentAttempt.objects.get(user=self.user)
        self.assertEqual(attempt.outcome, IndependentAttempt.Outcome.NEEDS_REVIEW)
        self.assertFalse(UnitProgress.objects.filter(user=self.user).exists())

    def test_transfer_is_ungraded_even_if_identical_to_model(self):
        task = understanding_bank()[self.lesson.slug]["tasks"]["transfer"]
        response = self.client.post(self.url, {"skill": "transfer", "answer": task["model"]})
        self.assertEqual(response.status_code, 200)
        attempt = IndependentAttempt.objects.get(user=self.user)
        self.assertEqual(attempt.outcome, IndependentAttempt.Outcome.SELF_REPORTED)
        self.assertContains(response, "Как у вас получилось?")
        self.assertNotContains(response, "Вы ответили правильно")

    def test_explain_rule_is_an_open_self_assessed_task(self):
        task = understanding_bank()[self.lesson.slug]["tasks"]["explain"]
        response = self.client.post(self.url, {"skill": "explain", "answer": task["model"]})
        self.assertEqual(response.status_code, 200)
        item = IndependentAttempt.objects.get(user=self.user)
        self.assertEqual(item.outcome, IndependentAttempt.Outcome.SELF_REPORTED)
        self.assertEqual(item.skill, "explain")
        self.assertContains(response, "Как у вас получилось?")
        result = self.client.post(self.url, {
            "action": "rate", "attempt_id": item.pk, "rating": "independent",
        })
        self.assertEqual(result.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.self_rating, "independent")

    def test_student_can_self_rate_only_their_own_transfer(self):
        self.client.post(self.url, {"skill": "transfer", "answer": "This is a phone."})
        attempt = IndependentAttempt.objects.get(user=self.user)
        response = self.client.post(self.url, {"action": "rate", "attempt_id": attempt.pk, "rating": "helped"})
        self.assertEqual(response.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.self_rating, "helped")
        other = User.objects.create_user(email="another-independent@example.test", password="ExamplePassword123!")
        self.client.force_login(other)
        forbidden = self.client.post(self.url, {"action": "rate", "attempt_id": attempt.pk, "rating": "independent"})
        self.assertEqual(forbidden.status_code, 404)
        attempt.refresh_from_db()
        self.assertEqual(attempt.self_rating, "helped")
        self.assertNotContains(self.client.get(self.url), "This is a phone.")

    def test_empty_and_oversized_answers_rejected_without_storage(self):
        for value in ("", " ", "a" * 401):
            with self.subTest(length=len(value)):
                response = self.client.post(self.url, {"skill": "writing", "answer": value})
                self.assertEqual(response.status_code, 400)
        self.assertFalse(IndependentAttempt.objects.filter(user=self.user).exists())

    def test_invalid_skill_and_rating_are_rejected(self):
        self.assertEqual(self.client.post(self.url, {"skill": "speaking", "answer": "Hello"}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {"skill": "meaning", "answer": "Да"}).status_code, 200)
        item = IndependentAttempt.objects.get(user=self.user)
        self.assertEqual(self.client.post(self.url, {"action": "rate", "attempt_id": item.pk, "rating": "independent"}).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"action": "rate", "attempt_id": item.pk, "rating": "fake"}).status_code, 400)

    def test_login_required_and_other_levels_excluded(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url, {"skill": "writing", "answer": "Hello"}).status_code, 302)

    def test_mobile_semantics_present(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="viewport" content="width=device-width, initial-scale=1"')
        self.assertContains(response, "css/independent-check.css")
        self.assertContains(response, "<textarea", count=4)
        self.assertContains(response, "maxlength=\"400\"", count=4)
        self.assertContains(response, "Отправить четыре ответа и открыть разбор", count=1)
