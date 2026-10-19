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


def test_episode_narration_preserves_actions_and_level():
    """Narrative Present Simple can depict one-time events; actions must remain."""
    expected_actions = {
        "s02_cafe_on_the_corner.yaml": (
            "I go to the corner cafe.",
            "I drink my coffee.",
            "I go home at eight.",
        ),
        "s04_letter_with_no_name.yaml": ("I go to the old mailbox.",),
        "s05_big_family_photo.yaml": ("I move the old cupboard.",),
    }
    for filename, actions in expected_actions.items():
        story = load(STORIES / filename)
        narration = " ".join(
            plain(row["text"]) for row in story["script"]
            if row.get("kind") == "narration"
        )
        spoken = " ".join(
            plain(row.get("spoken", row["text"])) for row in story["script"]
            if row.get("kind") == "narration"
        )
        positions = [narration.find(action) for action in actions]
        assert all(pos >= 0 for pos in positions), (filename, actions)
        assert positions == sorted(positions), filename
        assert all(action in spoken for action in actions), filename
        # Do not introduce Present Continuous before it is taught.
        assert not re.search(r"\b(?:am|is|are) [a-z]+ing\b", narration), filename


def test_episode_story_clues_and_phrase_hunt_stay_aligned():
    cafe = load(STORIES / "s02_cafe_on_the_corner.yaml")
    english = " ".join(plain(line["text"]) for line in cafe["script"])
    for fragment in (
        "I go to the corner cafe.", "I drink my coffee.",
        "I go home at eight.", "Box is at home!",
        "here at seven every day",
    ):
        assert fragment in english, fragment
    for item in cafe["phrase_hunt"]:
        assert item["phrase"] in english, item["phrase"]
    assert "Во сколько Анна идёт" in cafe["questions"][0]["q"]
    assert "It is seven o'clock." in cafe["questions"][0]["a"]
    assert "I go" in cafe["retell_steps"][1]

    letter = load(STORIES / "s04_letter_with_no_name.yaml")
    letter_text = " ".join(plain(row["text"]) for row in letter["script"])
    assert "I go to the old mailbox." in letter_text
    assert "I go to" in letter["retell_steps"][1]
    assert "Rose" in letter_text

    family = load(STORIES / "s05_big_family_photo.yaml")
    photo_lines = [plain(row["text"]) for row in family["script"]]
    assert "I move the old cupboard." in photo_lines[0]
    assert "There is a photo behind the cupboard!" in photo_lines[1]
    assert "I move" in family["retell_steps"][1]
    for clue in ("cupboard", "photo", "Rose", "Park Street"):
        assert clue in " ".join(photo_lines)
