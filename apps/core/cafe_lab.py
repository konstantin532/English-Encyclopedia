"""Standalone A1 café lab and optional, verified-source Kokoro audio.

Never serve test-tone manifests as speech, and never require generated audio for
the text exercises to work. No models, content seeds or database migrations.
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_GET


CAFE_DIALOGUE = (
    {"speaker": "mia", "speaker_ru": "Мия", "text": "Good morning, Tom! What would you like?"},
    {"speaker": "tom", "speaker_ru": "Том", "text": "I'd like one tea and one coffee, please."},
    {"speaker": "mia", "speaker_ru": "Мия", "text": "Two coffees?"},
    {"speaker": "tom", "speaker_ru": "Том", "text": "No, sorry. One tea and one coffee, please."},
    {"speaker": "mia", "speaker_ru": "Мия", "text": "One tea and one coffee. Here you are."},
    {"speaker": "tom", "speaker_ru": "Том", "text": "Thank you!"},
)
TEMPOS = ("very_slow", "slow", "natural")
AUDIO_ROOT = "audio/cafe-lab"


def safe_audio_manifest(static_root: Path):
    """Return only locally present Kokoro voice tracks with valid timings.

    Ignore missing, malformed, stale or test-tone manifests. Never trust a
    manifest path to escape the dedicated audio directory, even via symlinks.
    """
    folder = static_root / AUDIO_ROOT
    try:
        raw = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("engine") != "kokoro":
            return None
        if not str(raw.get("model", "")).startswith("kokoro-v"):
            return None
        if raw.get("voices", {}).get("mia") != "af_bella" or raw["voices"].get("tom") != "am_michael":
            return None
        tracks = {}
        previous_path = set()
        for tempo in TEMPOS:
            item = raw.get(tempo)
            if not isinstance(item, dict):
                return None
            relative = item.get("file")
            pattern = rf"audio/cafe-lab/voice_{tempo}\.(mp3|wav)"
            if not isinstance(relative, str) or not re.fullmatch(pattern, relative):
                return None
            path = static_root / relative
            if not path.is_file() or not path.resolve().is_relative_to(folder.resolve()):
                return None
            if path.stat().st_size <= 1024 or relative in previous_path:
                return None
            previous_path.add(relative)
            duration, timings = item.get("seconds"), item.get("timings")
            if not isinstance(duration, (float, int)) or isinstance(duration, bool) or duration <= 0:
                return None
            if not isinstance(timings, list) or len(timings) != len(CAFE_DIALOGUE):
                return None
            cleaned = []
            end_before = 0
            for index, timing in enumerate(timings):
                if not isinstance(timing, dict) or timing.get("line") != index:
                    return None
                start, end = timing.get("start"), timing.get("end")
                if (not isinstance(start, (int, float)) or isinstance(start, bool)
                        or not isinstance(end, (int, float)) or isinstance(end, bool)
                        or not 0 <= end_before <= start < end <= duration + 0.2):
                    return None
                cleaned.append({"line": index, "start": start, "end": end})
                end_before = end
            tracks[tempo] = {"url": static(relative), "timings": cleaned}
        return {"engine": "kokoro", "verified": bool(raw.get("verified") is True), "tracks": tracks}
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        return None


@require_GET
def cafe_lab(request):
    """Pilot without saving answers or microphone audio in the database."""
    return render(request, "core/cafe_lab.html", {
        "cafe_dialogue": CAFE_DIALOGUE,
        "cafe_audio": safe_audio_manifest(Path(settings.BASE_DIR) / "static"),
    })
