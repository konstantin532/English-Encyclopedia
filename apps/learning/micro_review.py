"""Render editor-authored five-case micro-skill review specifications.

Each source exercise may have five original contextual variations with the
same diagnosed language rule. Data is trusted, static, versioned JSON;
no generated questions, API calls or client-side correct answers.
"""
import json
from functools import lru_cache
from string import Formatter

from django.conf import settings

_MICRO_FILES = ("09_12", "13_16", "17_20", "21_24", "25_28")
_ALLOWED_FIELDS = set("abcdefghijklmnopqrstuvwxyz_0123456789")
_FORM = Formatter()


def _fields(template):
    fields = [field for _, field, _, _ in _FORM.parse(template) if field is not None]
    if any(not field or any(c not in _ALLOWED_FIELDS for c in field)
           for field in fields):
        raise ValueError("Micro-skill placeholders must be plain identifiers.")
    return set(fields)


def compile_skill(slug, order, spec):
    """Five 5-column review rows: RU prompt, EN context, 3 answers, key, rationale."""
    keys = spec.get("keys", [])
    cases = spec.get("cases", [])
    options = spec.get("options", [])
    templates = [spec.get("prompt", ""), spec.get("en", ""), *options]
    if (len(cases) != 5 or len(options) != 3 or
            len(keys) != len(set(keys)) or
            any(not isinstance(key, str) or not key.isidentifier() for key in keys) or
            any(not isinstance(v, str) or not v.strip() for v in options) or
            not spec.get("reason", "").strip() or not spec.get("prompt", "").strip()):
        raise ValueError(f"Incomplete micro-skill pack: {slug}#{order}")
    used = set().union(*(_fields(s) for s in templates))
    if used != set(keys):
        raise ValueError(f"Micro-skill key mismatch: {slug}#{order}")
    rows = []
    for idx, case in enumerate(cases):
        if len(case) != len(keys) or any(not isinstance(v, str) or not v.strip() for v in case):
            raise ValueError(f"Incorrect case: {slug}#{order} #{idx + 1}")
        values = dict(zip(keys, case))
        prompt, en, *choices = (s.format_map(values) for s in templates)
        if len(set(choices)) != 3:
            raise ValueError(f"Ambiguous alternatives: {slug}#{order} #{idx + 1}")
        # Rotate the answer location to avoid positional memorisation.
        rotate = idx % 3
        rotated = choices[rotate:] + choices[:rotate]
        rows.append([prompt, en, rotated, (-rotate) % 3, spec["reason"]])
    if len({row[0] for row in rows}) != 5:
        raise ValueError(f"Repeated learner situation: {slug}#{order}")
    return rows


@lru_cache(maxsize=1)
def micro_bank():
    root = settings.CONTENT_DIR / "manifests"
    bank = {}
    for suffix in _MICRO_FILES:
        path = root / f"a1_micro_review_{suffix}.json"
        if not path.exists():
            continue  # Safe staged rollout: other lessons use the existing bank.
        packet = json.loads(path.read_text(encoding="utf-8"))
        for slug, exercises in packet.items():
            if slug in bank:
                raise ValueError(f"Duplicate micro-skill lesson: {slug}")
            if set(exercises) != {str(i) for i in range(1, 7)}:
                raise ValueError(f"Micro-skill lesson must contain six exercises: {slug}")
            bank[slug] = {str(i): compile_skill(slug, i, exercises[str(i)])
                          for i in range(1, 7)}
    return bank
