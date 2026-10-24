"""Реплики по ролям: общий формат для историй и диалогов недель."""
from pathlib import Path

import yaml
from django.conf import settings


def voices_manifest() -> dict:
    """Весь content/manifests/voices.yaml (роли, эмоции, настроения музыки). Нет файла — пустой словарь."""
    path = Path(settings.CONTENT_DIR) / "manifests" / "voices.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {} if path.exists() else {}


def voice_roles() -> dict:
    return voices_manifest().get("roles", {})


def build_lines(script: list[dict]) -> tuple[list[dict], list[dict]]:
    """Строки для шаблона и список говорящих в порядке появления."""
    voices = voices_manifest()
    roles, emotions = voices.get("roles", {}), voices.get("emotions", {})
    lines, speakers, seen = [], [], set()
    for i, line in enumerate(script):
        speaker = line["speaker"]
        emotion = line.get("emotion", "neutral")
        name = roles.get(speaker, {}).get("name_ru", speaker)
        lines.append({
            "i": i, "speaker": speaker, "kind": line.get("kind", "speech"), "text": line["text"],
            "ru": line.get("ru", ""), "spoken": line.get("spoken", ""), "name": name, "emotion": emotion,
            "emotion_ru": "" if emotion == "neutral" else emotions.get(emotion, {}).get("name_ru", ""),
        })
        if speaker not in seen:
            seen.add(speaker)
            speakers.append({"id": speaker, "name": name})
    return lines, speakers
