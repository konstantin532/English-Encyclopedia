"""Reviewed pilot content and deliberately narrow, server-side recall assessment.

This is not an English grammar checker. Unlisted answers remain uncertain.
Returned models are private: the encounter service decides when to reveal them.
"""
import json
import re
import unicodedata

from django.conf import settings

PILOT_ID = "a1-vocabulary-phrase-pilot"
CONTENT_VERSION = "1.0"
PILOT_SLUG = "a1-cafe-order"
UNIT_UIDS = ("LX-00055", "LX-00285", "LX-00084")
_PREREQUISITES = {
    "lesson_slug": PILOT_SLUG, "lesson_order": 5, "week": 3, "exposure_only": True,
}
_LEXICON_SOURCES = {
    "LX-00055": "a1_w03_pilot.yaml",
    "LX-00285": "a1_w03_cafe_plus.yaml",
    "LX-00084": "a1_w03_pilot.yaml",
}


def normalize_answer(text: str) -> str:
    """Ignore cosmetic sentence punctuation, never apostrophes or hyphens.

    In particular, don't delete negations, stem words, or use substring matches.
    This normalization is local to the trainer and does not alter other graders.
    """
    if not isinstance(text, str):
        raise ValueError("Ответ должен быть текстом.")
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.translate(str.maketrans({"’": "'", "‘": "'", "ʼ": "'"}))
    return " ".join(re.sub(r'[.,!?;:"“”()]', " ", text).split())


def _require(condition, message):
    if not condition:
        raise ValueError("Неполный или несовместимый контент тренажёра: " + message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _texts(values, minimum=1):
    return (isinstance(values, list) and len(values) >= minimum
            and all(_text(value) for value in values))


def _validate_task(task):
    _require(isinstance(task, dict), "задание")
    for key in ("task_id", "family_id", "prompt", "model", "evidence_kind"):
        _require(_text(task.get(key)), key)
    _require(task["evidence_kind"] in ("target_recall", "target_pattern_transfer"),
             "тип свидетельства")
    _require(_texts(task.get("accepted")), "допустимые варианты")
    _require(task["model"] in task["accepted"], "образец вне допустимых вариантов")
    accepted = {normalize_answer(answer) for answer in task["accepted"]}
    _require("" not in accepted, "пустой нормализованный вариант")
    errors = task.get("meaning_errors")
    _require(isinstance(errors, list) and bool(errors), "контрасты смысла")
    error_answers = set()
    for error in errors:
        _require(isinstance(error, dict) and _text(error.get("answer"))
                 and _text(error.get("feedback")), "разбор смысловой ошибки")
        error_answers.add(normalize_answer(error["answer"]))
    alternatives = task.get("valid_alternatives")
    _require(isinstance(alternatives, list) and all(_text(a) for a in alternatives),
             "альтернативные способы достичь цели")
    alternate_answers = {normalize_answer(answer) for answer in alternatives}
    _require(not (accepted & error_answers or accepted & alternate_answers
                  or error_answers & alternate_answers), "противоречивые ключи")
    _require(normalize_answer(task["model"]) not in normalize_answer(task["prompt"]),
             "образец в условии")


def _validate_versions(document, task_ids):
    versions = document.get("compatibility")
    current = document.get("content_version")
    revision = document.get("assessment_revision")
    _require(_text(current) and _text(revision) and isinstance(versions, dict)
             and current in versions, "нет карты версии")
    _require(all(_text(version) and isinstance(mapping, dict)
                 for version, mapping in versions.items()), "карта версии")
    for version, mapping in versions.items():
        _require(_text(version) and isinstance(mapping, dict), "карта версии")
        _require(mapping.get("history_policy") == "preserve", "история не сохраняется")
        _require(_text(mapping.get("assessment_revision")), "ревизия проверки")
        previous = mapping.get("compatible_with")
        _require(isinstance(previous, list) and all(_text(v) and v in versions
                 and v != version for v in previous), "неизвестная совместимая версия")
        task_mapping = mapping.get("task_mapping")
        _require(isinstance(task_mapping, dict) and all(_text(old)
                 and (_text(new) and new in task_ids or new is None)
                 for old, new in task_mapping.items()), "карта заданий")
        change = mapping.get("change")
        _require(change in ("initial", "cosmetic", "assessment"), "вид редакции")
        if change == "initial":
            _require(version == "1.0" and mapping["assessment_revision"] == "1"
                     and not previous and not task_mapping, "начальная версия")
        elif change == "cosmetic":
            _require(bool(previous) and not task_mapping and all(
                versions[v].get("assessment_revision") == mapping["assessment_revision"]
                for v in previous), "косметическая редакция меняет проверку")
        else:
            _require(bool(task_mapping) and not previous,
                     "изменение проверки требует явной карты заданий без автоматической совместимости")
    _require(versions[current]["assessment_revision"] == revision,
             "текущая ревизия не совпадает с картой")


def _validate_document(document):
    _require(isinstance(document, dict), "документ")
    _require(document.get("pilot_id") == PILOT_ID
             and document.get("pilot_slug") == PILOT_SLUG
             and document.get("level") == "A1", "неизвестный пилот")
    _require(document.get("prerequisites") == _PREREQUISITES, "пререквизиты")
    _require(_text(document.get("review_scope")), "границы рецензии")
    units = document.get("units")
    _require(isinstance(units, list) and len(units) == 3
             and all(isinstance(unit, dict) for unit in units), "ровно три единицы")
    _require(tuple(unit.get("uid") for unit in units) == UNIT_UIDS, "состав пилота")
    task_ids = []
    for unit in units:
        uid = unit["uid"]
        _require(unit.get("source") == {
            "lexicon": "content/seed_lexicon/" + _LEXICON_SOURCES[uid],
            "lesson": "content/seed_lessons/a1_w03_l05_cafe.yaml",
        }, "источники " + uid)
        _require(unit.get("prerequisites") == _PREREQUISITES, "пререквизиты " + uid)
        for key in ("title", "meaning", "explanation", "mnemonic", "reviewer_note"):
            _require(_text(unit.get(key)), key + " " + uid)
        _require(unit.get("mnemonic_review") == "ai_reviewed_not_human_validated",
                 "нет рецензии мнемоники " + uid)
        examples = unit.get("examples")
        _require(isinstance(examples, list) and len(examples) >= 2
                 and all(isinstance(e, dict) and _text(e.get("en"))
                         and _text(e.get("ru")) for e in examples), "примеры " + uid)
        tasks = unit.get("recall_tasks")
        _require(isinstance(tasks, list) and len(tasks) == 2, "две ситуации извлечения " + uid)
        for task in tasks:
            _validate_task(task)
            if uid == "LX-00055":
                _require({normalize_answer(a) for a in task["accepted"]} == {"tea"},
                         "задание на название чая")
            task_ids.append(task["task_id"])
        _require(len({task["family_id"] for task in tasks}) == 2
                 and len({task["prompt"] for task in tasks}) == 2,
                 "разные семейства ситуаций " + uid)
        applications = unit.get("applications")
        _require(isinstance(applications, list) and len(applications) == 2,
                 "две ситуации применения " + uid)
        for task in applications:
            _require(isinstance(task, dict) and _text(task.get("task_id"))
                     and _text(task.get("prompt")) and _texts(task.get("criteria"))
                     and _texts(task.get("valid_examples"), 3)
                     and task.get("assessment") == "self_report_only"
                     and not any(key in task for key in ("accepted", "meaning_errors", "correct")),
                     "применение без автоматической оценки " + uid)
            task_ids.append(task["task_id"])
        _require(len({task["prompt"] for task in applications}) == 2,
                 "разные ситуации применения " + uid)
        spoken = unit.get("spoken")
        _require(isinstance(spoken, dict) and spoken.get("evidence") == "self_report_only"
                 and "audio" in spoken and spoken["audio"] is None
                 and all(_text(spoken.get(k)) for k in ("prompt", "comparison", "text_alternative")),
                 "устная самооценка без непроверенного аудио " + uid)
    _require(len(task_ids) == len(set(task_ids)), "повторяющиеся ID заданий")
    _validate_versions(document, set(task_ids))


def pilot_content() -> dict:
    """Load a fresh private copy; malformed editorial content disables the pilot."""
    path = settings.CONTENT_DIR / "manifests" / "a1_vocabulary_trainer.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Контент тренажёра недоступен.") from exc
    _validate_document(document)
    return document


def unit_content(uid: str) -> dict:
    """Return only an existing reviewed pilot sense, without shared mutations."""
    for unit in pilot_content()["units"]:
        if unit["uid"] == uid:
            return unit
    raise KeyError(uid)


def assess_recall(unit: dict, answer: str, *, task_id=None) -> dict:
    """Assess one authored narrow task, including a frozen session snapshot.

    A valid alternative goal is separate from evidence of the target expression.
    Neither a match nor a transfer result evaluates pronunciation or proficiency.
    """
    tasks = unit.get("recall_tasks", [])
    if task_id is None and tasks:
        task_id = tasks[0]["task_id"]
    task = next((task for task in tasks if task.get("task_id") == task_id), None)
    _require(task is not None, "неизвестное задание")
    _validate_task(task)
    answer = normalize_answer(answer)
    outcome, goal, target = "uncertain", None, False
    feedback = "Этот вариант не проверен автоматически. Сравните смысл с образцом; несовпадение само по себе не означает ошибку."
    if answer in {normalize_answer(a) for a in task["accepted"]}:
        outcome, goal, target = "correct", True, True
        feedback = "Ответ соответствует проверенному варианту этого задания. Это свидетельство об этой попытке, а не оценка общего уровня."
    elif answer in {normalize_answer(a) for a in task["valid_alternatives"]}:
        goal = True
        feedback = "Так можно достичь цели. Целевое выражение в этой попытке не подтверждено; сравните его с образцом отдельно."
    else:
        error = next((e for e in task["meaning_errors"]
                      if normalize_answer(e["answer"]) == answer), None)
        if error:
            outcome, goal = "incorrect", False
            feedback = error["feedback"]
    return {
        "outcome": outcome, "feedback": feedback,
        "canonical_answer": task["model"], "goal_achieved": goal,
        "target_used": target, "task_id": task["task_id"],
        "family_id": task["family_id"], "evidence_kind": task["evidence_kind"],
    }
