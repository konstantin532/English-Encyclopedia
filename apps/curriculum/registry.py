"""Количественный план курса: уровни, единицы, истории, стихи, недели."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LevelPlan:
    code: str
    order: int
    block: str
    cefr_band: str
    new_units: int
    weeks: int
    stories: tuple[int, int]  # номера с–по
    poems: tuple[int, int]
    story_words: tuple[int, int]
    phrase_words: tuple[int, int]
    summary_ru: str

    @property
    def story_count(self) -> int:
        return self.stories[1] - self.stories[0] + 1

    @property
    def poem_count(self) -> int:
        return self.poems[1] - self.poems[0] + 1


LEVELS: tuple[LevelPlan, ...] = (
    LevelPlan("A1", 1, "A", "A1", 500, 14, (1, 5), (1, 7), (60, 80), (3, 5),
              "be, have, do, Present Simple, can, there is/are"),
    LevelPlan("A1+", 2, "A", "A1 (переходная ступень курса)", 550, 16, (6, 11), (8, 14), (100, 120), (5, 8),
              "Past Simple, must, have to, реальное if"),
    LevelPlan("A2", 3, "A", "A2", 550, 16, (12, 17), (15, 21), (150, 180), (8, 12),
              "will / going to, сравнение, первые относительные предложения"),
    LevelPlan("A2+", 4, "A", "A2 (расширенный)", 600, 18, (18, 22), (22, 28), (200, 250), (10, 15),
              "устойчивые предлоги, простой пассив, связная речь"),
    LevelPlan("B1", 5, "B", "B1", 950, 22, (23, 32), (29, 36), (220, 300), (10, 14),
              "Present Perfect vs Past Simple, 1st и 2nd Conditional"),
    LevelPlan("B1+", 6, "B", "B1 (расширенный)", 1000, 22, (33, 42), (37, 44), (280, 380), (12, 16),
              "used to / would, reported speech, знакомство с 3rd Conditional"),
    LevelPlan("B2", 7, "B", "B2", 1000, 20, (43, 51), (45, 52), (350, 450), (14, 20),
              "perfect modals, wish / if only, каузативы"),
    LevelPlan("B2+", 8, "B", "B2 (расширенный)", 1050, 22, (52, 60), (53, 60), (400, 550), (16, 25),
              "инверсия, эмфаза, академический регистр"),
)

TOTAL_UNITS = 6200
TOTAL_STORIES = 60
TOTAL_POEMS = 60
TOTAL_WEEKS = 150

# Недельная норма новых единиц = слова + фразы + коллокации/идиомы (раздел 14).
WEEKLY_UNITS = {
    "A1": (30, 39), "A1+": (30, 39), "A2": (30, 39), "A2+": (30, 39),
    "B1": (38, 47), "B1+": (44, 54), "B2": (49, 58), "B2+": (47, 56),
}
LEVEL_BY_CODE = {lv.code: lv for lv in LEVELS}


def validate_plan() -> list[str]:
    errors: list[str] = []
    units = sum(lv.new_units for lv in LEVELS)
    if units != TOTAL_UNITS:
        errors.append(f"Единиц {units}, а должно быть {TOTAL_UNITS}.")
    block_a = sum(lv.new_units for lv in LEVELS if lv.block == "A")
    if block_a != 2200 or units - block_a != 4000:
        errors.append(f"Блоки A/B: {block_a}/{units - block_a}, ожидается 2200/4000.")
    for kind, total, attr in (("историй", TOTAL_STORIES, "stories"), ("стихов", TOTAL_POEMS, "poems")):
        expected = 1
        for lv in LEVELS:
            start, end = getattr(lv, attr)
            if start != expected:
                errors.append(f"{lv.code}: нумерация {kind} начинается с {start}, ожидалось {expected}.")
            expected = end + 1
        if expected - 1 != total:
            errors.append(f"Всего {kind} {expected - 1}, а должно быть {total}.")
    for lv in LEVELS:
        low, high = WEEKLY_UNITS[lv.code]
        per_week = lv.new_units / lv.weeks
        if not low <= per_week <= high:
            errors.append(f"{lv.code}: {per_week:.1f} новых единиц в неделю, норма {low}–{high}.")
    weeks = sum(lv.weeks for lv in LEVELS)
    if weeks != TOTAL_WEEKS:
        errors.append(f"Недель {weeks}, ожидается {TOTAL_WEEKS}.")
    return errors


def cycle_week(level_code: str, index: int, count: int) -> int:
    """Неделя для index-й (с нуля) истории или стиха уровня: равномерно по двухнедельным циклам.

    Работа с историей начинается в пятницу второй недели цикла (раздел 14).
    """
    lv = LEVEL_BY_CODE[level_code]
    cycles = lv.weeks // 2
    cycle = max(1, min(cycles, round((index + 1) * cycles / count)))
    return cycle * 2


# Нормы покрытия: в скольких историях уровня каждая из 11 категорий должна быть тренируемой (раздел 12).
STORY_COVERAGE = {"A1": 3, "A1+": 3, "A2": 3, "A2+": 3, "B1": 4, "B1+": 4, "B2": 5, "B2+": 5}
NEW_WORDS_PER_STORY = {"A": 5, "B": 8}


# Сферы жизни для недель (спецификация «Недели вокруг ситуаций», раздел 3). Смысл занятого кода не меняется.
SPHERES = {
    "meet": "Знакомство и люди",
    "home": "Дом и быт",
    "food": "Еда и кафе",
    "shop": "Магазин и покупки",
    "city": "Город и транспорт",
    "travel": "Путешествия: аэропорт, отель, дорога",
    "health": "Здоровье и врач",
    "work": "Работа и созвоны",
    "study": "Учёба",
    "free": "Свободное время",
    "connect": "Телефон, сообщения, интернет",
    "service": "Услуги: банк, почта, документы",
}

# Длина диалога недели: реплик и слов. Для уровня без нормы проверка длины выдаёт предупреждение.
DIALOGUE_LINES = {"A1": (6, 10)}
DIALOGUE_WORDS = {"A1": (40, 90)}

# Серия скороговорок по уровням (раздел 8).
TWISTER_SERIES = {
    "A1": "sounds", "A1+": "contractions", "A2": "contractions", "A2+": "connected",
    "B1": "connected", "B1+": "fast", "B2": "fast", "B2+": "fast",
}


def global_week(level_code: str, week: int) -> int:
    """Порядковый номер недели в курсе (1–150): недели предыдущих уровней + номер внутри уровня."""
    order = LEVEL_BY_CODE[level_code].order
    return sum(lv.weeks for lv in LEVELS if lv.order < order) + week
