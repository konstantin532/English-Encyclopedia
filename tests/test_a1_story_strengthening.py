"""Regression checks for the A1 dialogue, narration and oral-prompt editing pass.

These are editorial/structural checks, not tests of human learning outcomes.
"""
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WEEKS = ROOT / "content" / "seed_weeks"
STORIES = ROOT / "content" / "seed_stories"


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def plain(marked):
    return " ".join(re.sub(r"\[[^]]+\]", "", marked).split())


def test_every_existing_a1_week_has_multiple_open_spoken_acts():
    paths = sorted(WEEKS.glob("a1_w[0-9][0-9].yaml"))
    assert len(paths) == 14  # preserve the existing A1 scope
    # Verify a *pair of different oral actions*, rather than token counts or
    # multiple-choice questions. Full communicative quality needs human review.
    actions = (
        "скажите", "расскажите", "спросите", "попросите", "назовите",
        "представьтесь", "поздоровайтесь", "ответьте", "покажите",
        "закажите", "продиктуйте", "объясните", "представьте",
    )
    for number, path in enumerate(paths, 1):
        data = load(path)
        assert data["week"] == number and data["level"] == "A1"
        mission = data["mission_ru"].casefold()
        found = {verb for verb in actions if verb in mission}
        assert len(found) >= 2, (path.name, found)
        assert not any(key in data for key in ("mission_choices", "mission_options"))

    first = load(WEEKS / "a1_w01.yaml")["mission_ru"]
    assert "1." in first and "2." in first
    assert "без вариантов ответа" in first.casefold()


def test_cafe_polite_response_and_goal_remain_intact():
    data = load(WEEKS / "a1_w03.yaml")
    barista = [plain(line["text"]) for line in data["script"] if line["speaker"] == "barista"]
    assert "Yes! Here you are." in barista
    assert "Yes, you can. Here you are." not in barista
    assert any("Can I have" in plain(line["text"]) for line in data["script"])
    assert any("cookie" in plain(line["text"]) for line in data["script"])
    assert any("photo" in plain(line["text"]) for line in data["script"])


def test_episode_narration_avoids_habitual_or_untaught_tenses():
    for filename in (
        "s02_cafe_on_the_corner.yaml",
        "s04_letter_with_no_name.yaml",
        "s05_big_family_photo.yaml",
    ):
        story = load(STORIES / filename)
        narration = " ".join(plain(row["text"]) for row in story["script"]
                             if row.get("kind") == "narration")
        assert not re.search(r"\bI (?:go|move|drink)\b", narration), filename
        assert not re.search(r"\b(?:am|is|are) \w+ing\b", narration), filename
        retells = " ".join(story["retell_steps"])
        assert "I go" not in retells and "I move" not in retells, filename


def test_episode_story_clues_and_phrase_hunt_stay_aligned():
    cafe = load(STORIES / "s02_cafe_on_the_corner.yaml")
    english = " ".join(plain(line["text"]) for line in cafe["script"])
    for fragment in ("I am at the corner cafe.", "I am at home.", "Box is here!",
                     "here at seven every day"):
        assert fragment in english, fragment
    for item in cafe["phrase_hunt"]:
        assert item["phrase"] in english, item["phrase"]
    assert "Где Анна находится" in cafe["questions"][0]["q"]
    assert "I am at the corner cafe" in cafe["questions"][0]["a"]

    letter = load(STORIES / "s04_letter_with_no_name.yaml")
    letter_text = " ".join(plain(row["text"]) for row in letter["script"])
    assert "I am at the old mailbox." in letter_text
    assert "Rose" in letter_text

    family = load(STORIES / "s05_big_family_photo.yaml")
    photo_text = " ".join(plain(row["text"]) for row in family["script"])
    for clue in ("cupboard", "photo", "Rose", "Park Street"):
        assert clue in photo_text
