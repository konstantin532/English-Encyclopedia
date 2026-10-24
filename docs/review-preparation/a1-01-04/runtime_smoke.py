"""Preparation-only HTTP evidence; run only against an explicitly marked SQLite fixture.

No migrations, loading, production connection or persistent learner writes. All
temporary user/session/answer rows are rolled back. This is not a language audit,
a browser test, a concurrency test, or a certificate of student understanding.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import uuid


BASE_SHA = "8d3a41d9aa61cbf074caff602d53b22920ca3efa"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    args = parser.parse_args()
    expected = args.database.resolve(strict=True)
    if expected.name == "db.sqlite3" or expected.parent == ROOT:
        raise SystemExit("REFUSED: a dedicated fixture database path is required")
    marker = expected.parent / "REVIEW_DATABASE_ONLY"
    if not marker.is_file() or marker.read_text().strip() != BASE_SHA:
        raise SystemExit("REFUSED: database directory needs REVIEW_DATABASE_ONLY with the pinned SHA")
    if os.environ.get("DJANGO_SETTINGS_MODULE") != "config.settings.test":
        raise SystemExit("REFUSED: set DJANGO_SETTINGS_MODULE=config.settings.test explicitly")
    if os.environ.get("DATABASE_URL"):
        raise SystemExit("REFUSED: unset DATABASE_URL")

    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.db import connection, transaction
    from django.test import Client, override_settings
    from django.test.utils import setup_test_environment, teardown_test_environment
    from django.urls import reverse
    from django.utils import timezone
    from apps.lessons.models import Lesson
    from apps.drills.models import Exercise, PracticeItem
    from apps.drills.retry_guidance import is_open_pilot_response
    from apps.learning.models import ExerciseAttempt, IndependentAttempt, MistakeReview
    from apps.learning.mistake_review import variants_for
    from apps.learning.understanding import get_guide
    from apps.learning.transfer_pilot import PILOTS

    cfg = settings.DATABASES["default"]
    if cfg["ENGINE"] != "django.db.backends.sqlite3" or Path(cfg["NAME"]).resolve() != expected:
        raise SystemExit("REFUSED: actual configured database does not match the marked fixture")
    rows = list(Lesson.objects.filter(level__code="A1", order__in=[1, 2, 3, 4]).order_by("order"))
    if len(rows) != 4:
        raise SystemExit("Fixture is not loaded with four A1 lessons; this script will not load it")
    result = {"source_sha": BASE_SHA, "mode": "isolated_sqlite_transaction_rollback",
              "limitations": ["Django test client, not a real browser", "No audio listening or pronunciation validation",
                               "Sentinel negatives verify key mismatch behavior, not grammatical coverage",
                               "SQLite cannot prove PostgreSQL row-lock or concurrent transaction behavior"],
              "lessons": [], "routes": [], "assertions": 0}

    def require(condition, label):
        result["assertions"] += 1
        if not condition:
            raise AssertionError(label)

    setup_test_environment()
    counts_before = {"users": get_user_model().objects.count(), "attempts": ExerciseAttempt.objects.count(),
                     "independent": IndependentAttempt.objects.count(), "reviews": MistakeReview.objects.count()}
    try:
        with override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"]):
            with transaction.atomic():
                anon = Client(enforce_csrf_checks=True)
                signed = Client(enforce_csrf_checks=True)
                user = get_user_model().objects.create_user(email=f"prep-{uuid.uuid4().hex}@example.invalid")
                signed.force_login(user)
                for lesson in rows:
                    url = reverse("lessons:detail", args=[lesson.slug])
                    page = anon.get(url)
                    signed_page = signed.get(url)
                    require(page.status_code == signed_page.status_code == 200, f"lesson GET {lesson.slug}")
                    token = anon.cookies["csrftoken"].value
                    signed_token = signed.cookies["csrftoken"].value
                    html = page.content.decode()
                    exercises = list(lesson.exercises.all())
                    translations = list(lesson.practice_items.all())
                    require(len(page.context["layers"]) == 7, "seven rendered lesson layers")
                    require(html.count('data-kind="translate"') == len(translations), "rendered translation count")
                    require(html.count("data-drill ") + html.count("data-drill>") == len(exercises) + len(translations),
                            "rendered data-drill forms count")
                    item = {"slug": lesson.slug, "lesson_pk_fixture_only": lesson.pk, "url": url,
                            "exercise_count": len(exercises), "translation_count": len(translations),
                            "rendered_layer_count": 7, "missions_count": len(page.context["extra_missions"]),
                            "exercises": [], "practice": [], "unit_urls": []}

                    def post(client, target, payload, csrf):
                        response = client.post(target, json.dumps(payload), content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
                        require(response.status_code == 200, f"API {target}")
                        return response.json()

                    for exercise in exercises:
                        target = reverse("api:check_exercise", args=[exercise.pk])
                        require(anon.get(target).status_code == 405, "exercise endpoint POST-only")
                        checked = []
                        for answer in [exercise.answer, *exercise.accepted]:
                            data = post(anon, target, {"answer": answer}, token)
                            require(data["correct"] is True, f"canonical/accepted answer {exercise.uid}")
                            checked.append(answer)
                        wrong = post(anon, target, {"answer": "__preparation_unmatched_sentinel__"}, token)
                        require(wrong["correct"] is False, "sentinel mismatch")
                        if is_open_pilot_response(exercise):
                            require(wrong.get("assessment") == "needs_review", "free transfer is not certified wrong")
                        reveal = post(anon, target, {"reveal": True}, token)
                        require(reveal.get("revealed") is True and reveal["answer"] == exercise.answer, "reveal answer")
                        invalid = anon.post(target, json.dumps({"answer": 123}), content_type="application/json", HTTP_X_CSRFTOKEN=token)
                        require(invalid.status_code == 400, "non-text API input rejected")
                        item["exercises"].append({"uid": exercise.uid, "order": exercise.order,
                            "pk_fixture_only": exercise.pk, "check_url": target, "checked_answers": checked,
                            "open_transfer": is_open_pilot_response(exercise), "mismatch_response": wrong,
                            "delayed_card_count": len(variants_for(exercise))})
                    for practice in translations:
                        target = reverse("api:check_practice", args=[practice.pk])
                        for answer in [practice.answer, *practice.accepted]:
                            data = post(anon, target, {"answer": answer}, token)
                            require(data["correct"] is True, f"practice canonical/accepted {lesson.slug}:{practice.order}")
                        # Loose normalizer must tolerate punctuation and curly apostrophes.
                        altered = practice.answer.upper().replace("'", "’") + "!!!"
                        require(post(anon, target, {"answer": altered}, token)["correct"] is True,
                                "practice formatting normalization")
                        wrong = post(anon, target, {"answer": "__preparation_unmatched_sentinel__"}, token)
                        require(wrong.get("assessment") == "needs_review" and wrong["saved"] is False,
                                "practice unmatched is needs_review")
                        item["practice"].append({"order": practice.order, "pk_fixture_only": practice.pk,
                            "check_url": target, "review_of": practice.review_of,
                            "checked_answers": [practice.answer, *practice.accepted], "mismatch_response": wrong})
                    for unit in lesson.units.all():
                        target = reverse("lexicon:detail", args=[unit.uid])
                        require(anon.get(target).status_code == 200, f"dictionary {unit.uid}")
                        item["unit_urls"].append({"uid": unit.uid, "url": target})
                    target = reverse("core:active_a1_topic", args=[lesson.order])
                    lab = anon.get(target)
                    require(lab.status_code == 200, "active lab GET")
                    topic = lab.context["topic"]
                    item["active_url"] = target
                    item["active_dialogue_lines"] = len(topic["dialogue"])
                    item["active_retrieval_line_index_zero_based"] = (lesson.order - 1) % len(topic["dialogue"])
                    item["active_retrieval_line"] = topic["dialogue"][item["active_retrieval_line_index_zero_based"]]
                    item["active_mission_count"] = len(topic["missions"])

                    target = reverse("learning:independent_check", args=[lesson.slug])
                    require(anon.get(target).status_code == 302, "independent page requires login")
                    independent = signed.get(target)
                    require(independent.status_code == 200 and len(independent.context["tasks"]) == 4,
                            "four authenticated independent tasks")
                    item["independent_url"] = target
                    guide = get_guide(lesson.slug)
                    payload = {"action": "batch", "batch_token": independent.context["batch_token"],
                               "transfer_variant": str(independent.context["transfer_variant"]), "assistance": "no_help"}
                    for key in ("meaning", "writing", "transfer", "explain"):
                        payload["answer_" + key] = guide["tasks"][key]["model"]
                    answer_page = signed.post(target, payload, HTTP_X_CSRFTOKEN=signed_token)
                    require(answer_page.status_code == 200, "four-answer independent submission")
                    saved = list(IndependentAttempt.objects.filter(user=user, lesson=lesson).order_by("pk"))
                    require(len(saved) == 4, "four independent rows")
                    require({r.skill: r.outcome for r in saved} == {"meaning": "model_match", "writing": "model_match",
                              "transfer": "self_reported", "explain": "self_reported"}, "distinct evidence types")
                    item["independent_outcomes"] = {r.skill: r.outcome for r in saved}

                    speech = signed.get(reverse("learning:speech_practice"), {"key": "lesson:" + lesson.slug})
                    require(speech.status_code == 200 and speech.json()["count"] == 6, "speech six metadata targets")
                    item["speech_key"] = "lesson:" + lesson.slug
                    if lesson.slug in PILOTS:
                        target = reverse("learning:transfer_pilot", args=[lesson.slug])
                        require(signed.get(target).status_code == 200, "published pilot GET")
                        item["transfer_pilot_url"] = target
                    # A fixed recognition mismatch schedules a five-card 48-hour review for signed-in users.
                    fixed = next(ex for ex in exercises if not is_open_pilot_response(ex))
                    prior = ExerciseAttempt.objects.filter(user=user, exercise=fixed).count()
                    data = post(signed, reverse("api:check_exercise", args=[fixed.pk]),
                                {"answer": "__preparation_unmatched_sentinel__"}, signed_token)
                    require(data.get("retry_count") == 5 and data.get("saved") is True, "signed fixed mismatch schedules review")
                    review = MistakeReview.objects.get(user=user, exercise=fixed)
                    delta = (review.due_at - timezone.now()).total_seconds()
                    require(172740 < delta <= 172800, "48-hour review delay")
                    require(ExerciseAttempt.objects.filter(user=user, exercise=fixed).count() == prior + 1,
                            "one signed fixed attempt saved")
                    item["scheduled_delay_seconds_approx"] = round(delta)
                    result["lessons"].append(item)

                for name, args_ in [("curriculum:week", ["a1", 1]), ("curriculum:week", ["a1", 2]),
                                     ("stories:detail", [1]), ("stories:poem", [1]), ("taxonomy:legend", [])]:
                    target = reverse(name, args=args_)
                    response = anon.get(target)
                    require(response.status_code == 200, f"related page {target}")
                    result["routes"].append({"name": name, "url": target, "status_code": response.status_code})
                transaction.set_rollback(True)
    finally:
        teardown_test_environment()
    counts_after = {"users": get_user_model().objects.count(), "attempts": ExerciseAttempt.objects.count(),
                    "independent": IndependentAttempt.objects.count(), "reviews": MistakeReview.objects.count()}
    require(counts_before == counts_after, "temporary learner rows fully rolled back")
    result["temporary_rows_rolled_back"] = True
    result["status"] = "PASS"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
