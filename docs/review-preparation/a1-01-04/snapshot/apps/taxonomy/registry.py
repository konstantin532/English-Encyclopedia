"""Неизменяемый реестр визуальной разметки English Encyclopedia.

Единственный источник истины: 11 учебных категорий, их маркеры,
10 цветов палитры и классы внутри каждой категории.

Правило цвета: номер класса = номер цвета палитры. Класс S3 всегда
окрашен цветом №3 — поэтому класс не может получить разные цвета
в разных уроках.

ID классов («S3», «D9») постоянны. Новые классы можно добавлять только
на свободные номера; менять смысл занятого номера нельзя.
"""
from dataclasses import dataclass

PALETTE: dict[int, tuple[str, str]] = {
    1: ("Красный", "#d32f2f"),
    2: ("Оранжевый", "#ef6c00"),
    3: ("Охра", "#b98a00"),
    4: ("Зелёный", "#2e7d32"),
    5: ("Бирюзовый", "#00695c"),
    6: ("Синий", "#1565c0"),
    7: ("Фиолетовый", "#6a1b9a"),
    8: ("Розовый", "#ad1457"),
    9: ("Коричневый", "#5d4037"),
    10: ("Серо-синий", "#37474f"),
}

# Маркер = (CSS text-decoration-line, CSS text-decoration-style, описание)
MARKERS: dict[str, tuple[str, str, str]] = {
    "underline-solid": ("underline", "solid", "Одинарное подчёркивание"),
    "underline-double": ("underline", "double", "Двойное подчёркивание"),
    "underline-wavy": ("underline", "wavy", "Волнистое подчёркивание"),
    "underline-dotted": ("underline", "dotted", "Точечный пунктир снизу"),
    "underline-dashed": ("underline", "dashed", "Штриховой пунктир снизу"),
    "overline-solid": ("overline", "solid", "Одинарная черта сверху"),
    "overline-double": ("overline", "double", "Двойная черта сверху"),
    "overline-wavy": ("overline", "wavy", "Волнистая черта сверху"),
    "overline-dotted": ("overline", "dotted", "Точечный пунктир сверху"),
    "overline-dashed": ("overline", "dashed", "Штриховой пунктир сверху"),
    "strike-dotted": ("line-through", "dotted", "Точечное зачёркивание"),
}


@dataclass(frozen=True)
class Category:
    code: str
    key: str
    name_ru: str
    grammar_term_ru: str
    marker: str
    order: int
    content_word: bool
    classes: tuple[tuple[int, str, str], ...]  # (номер, название RU, название EN)


CATEGORIES: tuple[Category, ...] = (
    Category("S", "NOUNS", "Существительные", "имя существительное", "underline-solid", 1, True, (
        (1, "Люди и семья", "People & family"),
        (2, "Дом и предметы", "Home & objects"),
        (3, "Еда и напитки", "Food & drink"),
        (4, "Места и город", "Places & city"),
        (5, "Тело и здоровье", "Body & health"),
        (6, "Природа и животные", "Nature & animals"),
        (7, "Время и календарь", "Time & calendar"),
        (8, "Чувства и мысли", "Feelings & mind"),
        (9, "Работа, учёба, общение", "Work, study & communication"),
        (10, "Общество и идеи", "Society & ideas"),
    )),
    Category("D", "VERBS", "Глаголы", "глагол", "underline-double", 2, True, (
        (1, "Опорные и вспомогательные", "Core & auxiliary"),
        (2, "Повседневные действия", "Daily actions"),
        (3, "Состояния и чувства", "States & feelings"),
        (4, "Движение", "Movement"),
        (5, "Речь и передача слов", "Speech & reporting"),
        (6, "Мышление и восприятие", "Thinking & perception"),
        (7, "Модальные", "Modal verbs"),
        (8, "Фазовые и связочные", "Phase & linking"),
        (9, "Фразовые глаголы", "Phrasal verbs"),
        (10, "Каузативы и идиомы", "Causatives & idioms"),
    )),
    Category("J", "ADJECTIVES", "Прилагательные", "имя прилагательное", "underline-wavy", 3, True, (
        (1, "Размер и форма", "Size & shape"),
        (2, "Физические свойства", "Physical properties"),
        (3, "Оценка", "Evaluation"),
        (4, "Эмоции и ощущения", "Emotions & sensations"),
        (5, "Внешность", "Appearance"),
        (6, "Характер", "Character"),
        (7, "Причастные -ed/-ing", "Participial -ed/-ing"),
        (8, "Степень и градуируемость", "Degree & gradability"),
        (9, "Сложные и префиксальные", "Compound & prefixed"),
        (10, "Точная и формальная оценка", "Precise & formal evaluation"),
    )),
    Category("A", "ADVERBS", "Наречия", "наречие", "underline-dotted", 4, True, (
        (1, "Частотность", "Frequency"),
        (2, "Время", "Time"),
        (3, "Место", "Place"),
        (4, "Образ действия", "Manner"),
        (5, "Степень", "Degree"),
        (6, "Вопросительные", "Interrogative"),
        (7, "Связующие", "Linking"),
        (8, "Комментирующие и модальные", "Comment & stance"),
        (9, "Аргументация", "Argumentation"),
        (10, "Формальный стиль", "Formal style"),
    )),
    Category("N", "NUMERALS", "Числительные", "числительное", "underline-dashed", 5, True, (
        (1, "Количественные", "Cardinal"),
        (2, "Порядковые", "Ordinal"),
        (3, "Время на часах", "Clock time"),
        (4, "Даты и годы", "Dates & years"),
        (5, "Возраст", "Age"),
        (6, "Цены и деньги", "Prices & money"),
        (7, "Номера и коды", "Numbers & codes"),
        (8, "Дроби и проценты", "Fractions & percentages"),
        (9, "Приблизительность и сравнение", "Approximation & comparison"),
        (10, "Статистика и данные", "Statistics & data"),
    )),
    Category("T", "DETERMINERS", "Детерминативы", "детерминатив (определитель)", "overline-solid", 6, False, (
        (1, "Артикли", "Articles"),
        (2, "Указательные", "Demonstratives"),
        (3, "Притяжательные детерминативы", "Possessive determiners"),
        (4, "Количественные (кванторы)", "Quantifiers"),
        (5, "Распределительные", "Distributives"),
        (6, "Универсальные и парные", "Universal & dual"),
        (7, "Выражения с of", "Of-expressions"),
        (8, "Личные местоимения (pronouns)", "Personal pronouns"),
        (9, "Притяжательные и другие местоимения (pronouns)", "Possessive & other pronouns"),
        (10, "Формальные выражения количества", "Formal quantity expressions"),
    )),
    Category("P", "PREPOSITIONS", "Предлоги", "предлог", "overline-double", 7, False, (
        (1, "Место", "Place"),
        (2, "Направление и движение", "Direction & movement"),
        (3, "Время", "Time"),
        (4, "Инструмент и способ", "Instrument & means"),
        (5, "Причина и цель", "Cause & purpose"),
        (6, "Абстрактные отношения", "Abstract relations"),
        (7, "Управление глаголов", "Verb + preposition"),
        (8, "Управление прилагательных", "Adjective + preposition"),
        (9, "Составные предлоги", "Complex prepositions"),
        (10, "Формальные конструкции", "Formal prepositional phrases"),
    )),
    Category("X", "PARTICLES", "Частицы", "частица", "overline-wavy", 8, False, (
        (1, "Отрицание", "Negation"),
        (2, "Инфинитивное to", "Infinitive to"),
        (3, "Частицы фразовых глаголов: направление", "Phrasal particles: direction"),
        (4, "Частицы фразовых глаголов: переносные", "Phrasal particles: figurative"),
        (5, "Ограничительные", "Restrictive"),
        (6, "Усилительные", "Intensifying"),
        (7, "Эмфатические", "Emphatic"),
        (8, "Разговорные", "Conversational"),
        (9, "Формальные конструкции", "Formal constructions"),
    )),
    Category("C", "CONJUNCTIONS", "Союзы", "союз", "overline-dotted", 9, False, (
        (1, "Сочинительные", "Coordinating"),
        (2, "Время", "Time"),
        (3, "Причина и следствие", "Cause & result"),
        (4, "Условие", "Condition"),
        (5, "Противопоставление", "Contrast"),
        (6, "Уступка", "Concession"),
        (7, "Парные (коррелятивные)", "Correlative"),
        (8, "Относительные связи", "Relative links"),
        (9, "Формальные условия и уступки", "Formal conditions & concessions"),
    )),
    Category("O", "INTERJECTIONS", "Междометия и реакции", "междометие", "overline-dashed", 10, False, (
        (1, "Приветствие и прощание", "Greetings & farewells"),
        (2, "Благодарность и извинение", "Thanks & apologies"),
        (3, "Эмоциональные реакции", "Emotional reactions"),
        (4, "Согласие и несогласие", "Agreement & disagreement"),
        (5, "Удивление", "Surprise"),
        (6, "Сочувствие", "Sympathy"),
        (7, "Заполнители пауз", "Fillers"),
        (8, "Смягчение", "Softeners"),
        (9, "Разговорные реакции", "Conversational reactions"),
    )),
    Category("F", "DISCOURSE", "Дискурсивные маркеры", "дискурсивный маркер", "strike-dotted", 11, False, (
        (1, "Управление разговором", "Conversation management"),
        (2, "Уточнение", "Clarification"),
        (3, "Переформулирование", "Reformulation"),
        (4, "Структура речи", "Structuring"),
        (5, "Привлечение внимания", "Getting attention"),
        (6, "Смена темы", "Topic shift"),
        (7, "Проверка понимания", "Checking understanding"),
        (8, "Реакция на новость", "Reacting to news"),
        (9, "Аргументация", "Argumentation"),
        (10, "Академический дискурс", "Academic discourse"),
    )),
)

CATEGORY_BY_CODE = {c.code: c for c in CATEGORIES}


def class_id(code: str, number: int) -> str:
    return f"{code}{number}"


def color_for(number: int) -> str:
    return PALETTE[number][1]


def validate_registry() -> list[str]:
    """Возвращает список нарушений правил реестра (пустой — всё в порядке)."""
    errors: list[str] = []
    if len(CATEGORIES) != 11:
        errors.append(f"Категорий {len(CATEGORIES)}, а должно быть 11.")
    markers = [c.marker for c in CATEGORIES]
    if len(set(markers)) != len(markers):
        errors.append("Два раздела используют один и тот же маркер.")
    for c in CATEGORIES:
        if c.marker not in MARKERS:
            errors.append(f"{c.code}: неизвестный маркер {c.marker}.")
        nums = [n for n, _, _ in c.classes]
        if len(set(nums)) != len(nums):
            errors.append(f"{c.code}: повторяются номера классов.")
        if any(n not in PALETTE for n in nums):
            errors.append(f"{c.code}: номер класса вне палитры 1–10.")
    return errors
