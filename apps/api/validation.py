"""Одинаковая проверка ответа для упражнений, повторения и стихов."""
import json


def read_answer_payload(request) -> dict:
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Неверный JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Ожидается объект JSON")
    if not isinstance(payload.get("reveal", False), bool):
        raise ValueError("reveal должен быть true или false")
    if payload.get("reveal"):
        return payload
    answer = payload.get("answer", "")
    if not isinstance(answer, str):
        raise ValueError("Ответ должен быть текстом")
    answer = answer.strip()
    if not answer:
        raise ValueError("Введите ответ")
    if len(answer) > 200:
        raise ValueError("Ответ должен быть не длиннее 200 символов")
    try:
        answer.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Ответ содержит некорректный символ") from exc
    return {**payload, "answer": answer}
