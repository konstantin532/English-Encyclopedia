"""Negative and positive contracts for the server-side café information-gap pilot.

These tests do not establish human language-learning effectiveness.
"""
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.learning.cafe_mission import SESSION_KEY, SKILLS, parse_order
from apps.learning.models import IndependentAttempt, UnitProgress
from tests.runner import ensure_content


class CafeInformationGapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()

    def setUp(self):
        self.user = User.objects.create_user(
            email="cafe-pilot@example.test", password="ExamplePassword123!"
        )
        self.client.force_login(self.user)
        self.url = reverse("learning:cafe_mission")
        with patch("apps.learning.cafe_mission.secrets.randbelow", return_value=0):
            self.first = self.client.get(self.url)

    def state(self):
        return self.client.session[SESSION_KEY]

    def post(self, action, **fields):
        return self.client.post(self.url, {
            "token": self.state()["nonce"], "action": action, **fields
        })

    def send(self, answer):
        return self.post("send", answer=answer)

    def complete(self):
        self.assertEqual(self.send("I'd like one tea, please.").status_code, 302)
        self.assertEqual(self.state()["phase"], "ask")
        self.assertEqual(self.send("What do you have?").status_code, 302)
        self.assertEqual(self.state()["phase"], "choose")
        self.assertEqual(self.send("Can I have one coffee, please?").status_code, 302)
        self.assertEqual(self.state()["phase"], "repair")
        self.assertEqual(self.send("No, one coffee, please.").status_code, 302)
        self.assertEqual(self.state()["phase"], "done")

    def test_guest_requires_login_and_old_cafe_lab_works(self):
        outsider = Client()
        self.assertEqual(outsider.get(self.url).status_code, 302)
        self.assertEqual(self.first.status_code, 200)
        self.assertContains(self.first, "Миссия: заказ в кафе")
        lab = self.client.get(reverse("core:cafe_lab"))
        self.assertEqual(lab.status_code, 200)
        self.assertContains(lab, self.url)
        self.assertContains(lab, "data-cafe-lab")

    def test_hidden_stock_not_in_initial_html_and_no_answer_model(self):
        self.assertContains(self.first, "one tea")
        self.assertNotContains(self.first, "we don't have tea")
        self.assertNotContains(self.first, "We have coffee and water")
        self.assertNotContains(self.first, "Did you say two coffees")
        self.assertNotContains(self.first, "What do you have?")
        self.assertEqual(self.state()["phase"], "order")

    def test_real_branching_and_clarification_is_necessary(self):
        self.send("I'd like one tea, please.")
        first_npc = self.client.get(self.url)
        self.assertContains(first_npc, "we don't have tea")
        self.assertNotContains(first_npc, "We have coffee and water")
        self.send("I'd like one coffee, please.")
        self.assertEqual(self.state()["phase"], "ask")
        self.send("What do you have?")
        self.assertEqual(self.state()["phase"], "choose")
        self.send("I'd like one tea, please.")
        self.assertEqual(self.state()["phase"], "choose")
        self.send("Can I have one water, please?")
        self.assertEqual(self.state()["phase"], "repair")
        self.send("No, one water, please.")
        self.assertEqual(self.state()["phase"], "done")

    def test_quantity_confusion_is_explicit_but_unknown_free_text_is_not_graded(self):
        self.send("I'd like two teas, please.")
        state = self.state()
        self.assertEqual(state["phase"], "order")
        self.assertIn("one (один) и two (два)", state["feedback"])
        self.assertEqual(state["observed"], [])
        self.send("I have a dog.")
        self.assertEqual(self.state()["phase"], "order")
        self.assertIn("не оценка ошибки", self.state()["feedback"])
        self.assertIsNone(parse_order("I don't want tea"))
        self.assertIsNone(parse_order("I'd like one tea and one coffee"))
        self.assertEqual(parse_order("Could I have one tea, please?"), (1, "tea"))

    def test_stale_submit_rejected_without_extra_turns(self):
        token = self.state()["nonce"]
        payload = {"token": token, "action": "send", "answer": "I'd like one tea."}
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.assertEqual(self.client.post(self.url, payload).status_code, 400)
        self.assertEqual(self.state()["turns"], 1)
        self.assertEqual(IndependentAttempt.objects.count(), 0)

    def test_invalid_actions_and_bounds_do_not_create_evidence(self):
        self.assertEqual(self.post("save", assistance="no_help").status_code, 400)
        for answer in ("", "x", "b" * 81):
            self.assertEqual(self.send(answer).status_code, 400)
        self.assertEqual(self.state()["turns"], 0)
        self.assertEqual(IndependentAttempt.objects.count(), 0)

    def test_completion_is_not_misrepresented_as_teacher_verified(self):
        self.complete()
        self.assertFalse(IndependentAttempt.objects.exists())
        self.assertEqual(self.post("save", assistance="no_help").status_code, 302)
        attempt = IndependentAttempt.objects.get(user=self.user)
        self.assertEqual(attempt.lesson.slug, "a1-cafe-order")
        self.assertEqual(attempt.skill, "transfer")
        self.assertEqual(attempt.teacher_verdict, "unreviewed")
        self.assertEqual(attempt.outcome, "self_reported")
        self.assertEqual(attempt.assistance, "no_help")
        self.assertEqual(len(attempt.self_rubric["skill_acts"]), 4)
        self.assertTrue(attempt.self_rubric["structured_goal_reached"])
        self.assertTrue(attempt.self_rubric["not_language_grade"])
        self.assertEqual(UnitProgress.objects.filter(user=self.user).count(), 0)
        self.assertContains(self.client.get(self.url), "ожидает оценки преподавателя")
        self.assertEqual(self.post("save", assistance="no_help").status_code, 400)
        self.assertEqual(IndependentAttempt.objects.filter(user=self.user).count(), 1)

    def test_hint_is_logged_as_assisted_even_if_user_selects_no_help(self):
        self.assertEqual(self.post("hint").status_code, 302)
        self.assertEqual(self.state()["hints"], 1)
        self.complete()
        self.assertEqual(self.post("save", assistance="no_help").status_code, 302)
        attempt = IndependentAttempt.objects.get(user=self.user)
        self.assertEqual(attempt.assistance, "notes")
        self.assertEqual(attempt.self_rubric["hint_count"], 1)

    def test_second_user_does_not_inherit_dialogue_or_evidence(self):
        self.send("I'd like one tea, please.")
        other = User.objects.create_user(
            email="another-cafe-pilot@example.test", password="ExamplePassword123!"
        )
        other_client = Client()
        other_client.force_login(other)
        response = other_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        other_state = other_client.session[SESSION_KEY]
        self.assertEqual(other_state["phase"], "order")
        self.assertNotContains(response, "we don't have tea")
        self.assertEqual(IndependentAttempt.objects.filter(user=other).count(), 0)

    def test_html_is_escaped_and_restart_resets_session_not_progress(self):
        self.send("<script>alert(1)</script>")
        response = self.client.get(self.url)
        self.assertNotContains(response, "<script>alert(1)</script>", html=False)
        self.assertContains(response, "&lt;script&gt;")
        self.assertEqual(self.post("restart").status_code, 302)
        self.assertEqual(self.state()["turns"], 0)
        self.assertEqual(self.state()["phase"], "order")

    def test_skill_graph_is_small_acyclic_and_only_observable_actions(self):
        self.assertEqual(len(SKILLS), 4)
        for skill, definition in SKILLS.items():
            self.assertTrue(definition["can_do"].startswith("Я могу"))
            for prereq in definition["requires"]:
                self.assertIn(prereq, SKILLS)
                self.assertNotEqual(prereq, skill)

    def test_scenario_two_requires_a_different_order(self):
        self.post("restart")
        # Manually replace the current session scenario to test the other
        # server-owned branch without depending on random generation.
        session = self.client.session
        state = session[SESSION_KEY]
        state["scenario"] = 1
        session[SESSION_KEY] = state
        session.save()
        self.send("I'd like one tea, please.")
        self.assertEqual(self.state()["phase"], "order")
        self.send("I'd like one coffee, please.")
        self.assertEqual(self.state()["phase"], "ask")
        self.send("What do you have?")
        self.assertEqual(self.state()["phase"], "choose")
        self.send("Could I have one tea, please?")
        self.assertEqual(self.state()["phase"], "repair")
        self.send("No, one tea, please.")
        self.assertEqual(self.state()["phase"], "done")
