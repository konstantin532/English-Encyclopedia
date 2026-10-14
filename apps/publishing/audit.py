"""Аудит курса (/аудит): количества, реестр, разметка, незарегистрированная лексика."""
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from django.conf import settings

from apps.curriculum.registry import LEVEL_BY_CODE, LEVELS, NEW_WORDS_PER_STORY, STORY_COVERAGE, validate_plan
from apps.drills.models import Exercise
from apps.lessons.models import Lesson, LessonLayer
from apps.lexicon.models import CEFR, LexicalUnit
from apps.lexicon.phonetics import unknown_symbols
from apps.poems.models import Poem
from apps.stories.models import Story
from apps.taxonomy.markup import find_issues, strip_markup
from apps.taxonomy.registry import validate_registry

WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")
# Отдельный [X1]n't[/] допустим; основа и отрицание требуют разных маркеров.
UNSPLIT_NEGATIVE = re.compile(r"\[[A-Z]\d+(?:-#[0-9a-fA-F]{6})?\][^\[]+n['’]t\[/\]", re.IGNORECASE)
# Окончания форм: books, houses, Anna's — формы слова не плодят новые единицы (раздел 4).
FORM_SUFFIXES = ("'s", "s", "es")
# Сокращения: I'm, it's, you're, don't, isn't.
CONTRACTIONS = ("n't", "'m", "'s", "'re", "'ve", "'ll", "'d")


@dataclass
class AuditReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    unknown_words: dict[str, set[str]] = field(default_factory=dict)


def character_names() -> set[str]:
    path = Path(settings.CONTENT_DIR) / "manifests" / "characters.yaml"
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {c["name"].lower() for c in data.get("characters", [])}


def known_vocabulary() -> set[str]:
    words = set(character_names())
    for lemma, forms in LexicalUnit.objects.values_list("lemma", "forms"):
        words.add(lemma.lower())
        words.update(f.lower() for f in forms or [])
    return words


def unit_words(unit) -> set[str]:
    return {unit.lemma.lower(), *(f.lower() for f in unit.forms or [])}


def vocab_until(level, week_number: int, exclude_ids=()) -> set[str]:
    """Слова, изученные к указанной неделе уровня (включительно), плюс имена героев."""
    words = set(character_names())
    for u in LexicalUnit.objects.select_related("internal_level", "week").exclude(pk__in=exclude_ids):
        lv = u.internal_level
        if lv.order < level.order or (lv.pk == level.pk and (u.week is None or u.week.number <= week_number)):
            words |= unit_words(u)
    return words


def text_tokens(text: str) -> list[str]:
    return WORD.findall(strip_markup(text))


def is_known(token: str, vocab: set[str]) -> bool:
    t = token.lower().replace("’", "'")
    if t in vocab:
        return True
    for c in CONTRACTIONS:
        if t.endswith(c) and len(t) > len(c):
            base = t[: -len(c)]
            if c == "n't" and base == "ca":  # can't
                base = "can"
            if base in vocab or (c == "n't" and base + "n" in vocab):
                return True
    return any(t.endswith(suf) and t[: -len(suf)] in vocab for suf in FORM_SUFFIXES)


def english_lines() -> list[tuple[str, str]]:
    """Английские примеры слов, строки «> » в уроках, задания и sound_notes."""
    out = []
    for u in LexicalUnit.objects.all():
        out.append((u.uid, u.example_en))
        out += [(f"{u.uid}/фраза", c) for c in u.chunks or []]
    for layer in LessonLayer.objects.select_related("lesson"):
        for line in layer.body.splitlines():
            if line.startswith("> "):
                text = line[2:].split(" — ")[0]  # после тире идёт русский перевод
                out.append((f"{layer.lesson.slug}/слой {layer.number}", text))
    for ex in Exercise.objects.select_related("lesson"):
        where = f"{ex.lesson.slug}/задание {ex.order}"
        out += [(where, ex.prompt_en.replace("___", "")), (where, ex.answer), *[(where, a) for a in ex.accepted]]
    for lesson in Lesson.objects.all():
        out += [(f"{lesson.slug}/как это звучит", item["text"]) for item in lesson.sound_notes]
    return out


def audit_contractions(r: AuditReport, where: str, text: str) -> None:
    for match in UNSPLIT_NEGATIVE.finditer(text):
        r.errors.append(f"{where}: {match.group()} — слитная форма: основа и n't должны иметь отдельные маркеры.")


def audit_russian_transcription(r: AuditReport, units) -> None:
    """Русская транскрипция строится из IPA по таблице; неизвестный символ — пробел в записи."""
    items = [(f"{u.uid} {u.lemma}", u.ipa_us, u.ipa_ru) for u in units]
    for lesson in Lesson.objects.all():
        items += [(f"{lesson.slug}/как это звучит «{n['text']}»", n.get("ipa", ""), n.get("ru", ""))
                  for n in lesson.sound_notes]
    for poem in Poem.objects.all():
        items += [(f"стих {poem.number}, строка {i}", pr.get("ipa", ""), pr.get("ru", ""))
                  for i, pr in enumerate(poem.pronunciation, 1)]
    for where, ipa, manual in items:
        if manual:
            continue
        if not ipa:
            r.warnings.append(f"{where}: нет транскрипции — ни IPA, ни ручной русской.")
        elif bad := unknown_symbols(ipa):
            r.warnings.append(f"{where}: русская транскрипция неполная, неизвестные символы IPA: "
                              f"{' '.join(sorted(bad))}. Добавьте их в таблицу или впишите ручной вариант.")


def run_audit() -> AuditReport:
    r = AuditReport()
    r.errors += validate_plan()
    r.errors += validate_registry()

    units = list(LexicalUnit.objects.select_related("internal_level"))
    r.facts.append(f"Единиц в корпусе: {len(units)} из 6200.")
    for lv in LEVELS:
        n = sum(1 for u in units if u.internal_level.code == lv.code)
        if n:
            r.facts.append(f"{lv.code}: {n} из {lv.new_units}.")
            if n > lv.new_units:
                r.errors.append(f"{lv.code}: единиц {n}, больше квоты {lv.new_units}.")
    unverified = sum(1 for u in units if u.cefr == CEFR.UNVERIFIED)
    if unverified:
        r.warnings.append(f"CEFR не сверен у {unverified} единиц — нужна проверка по Oxford 3000/5000 и EVP.")
    partial = sum(1 for u in units if u.verification_status == "partial")
    if partial:
        r.facts.append(f"CEFR подтверждён на уровне слова (Oxford 3000) у {partial} единиц; сверка значений по EVP впереди.")
    for u in units:
        if u.cefr != CEFR.UNVERIFIED and u.verification_status == "pending":
            r.errors.append(f"{u.uid}: уровень {u.cefr} указан без подтверждения источником.")

    audit_russian_transcription(r, units)

    for u in units:
        for i in find_issues(u.example_en):
            r.errors.append(f"{u.uid}: {i.token} — {i.problem}")
    for layer in LessonLayer.objects.select_related("lesson"):
        audit_contractions(r, f"{layer.lesson.slug}, слой {layer.number}", layer.body)
        for i in find_issues(layer.body):
            r.errors.append(f"{layer.lesson.slug}, слой {layer.number}: {i.token} — {i.problem}")

    audit_stories_and_poems(r)

    vocab = known_vocabulary()
    for where, text in english_lines():
        if "/слой " not in where:
            audit_contractions(r, where, text)
        for tok in WORD.findall(strip_markup(text)):
            if not is_known(tok, vocab):
                r.unknown_words.setdefault(tok.lower(), set()).add(where)
    preview: dict[str, set[str]] = {}
    for u in LexicalUnit.objects.all():
        for sub_text in u.substitutions or []:
            for tok in WORD.findall(sub_text):
                if not is_known(tok, vocab):
                    r.errors.append(f"{u.uid}: подстановка «{sub_text}» содержит неизученное слово {tok}.")
        for col in u.collocations or []:
            for tok in WORD.findall(col):
                if not is_known(tok, vocab):
                    preview.setdefault(tok.lower(), set()).add(u.uid)
    if preview:
        r.warnings.append("Опережающие слова в сочетаниях (допустимо, но их нужно ввести позже): "
                          + ", ".join(f"{w} ({', '.join(sorted(p))})" for w, p in sorted(preview.items())) + ".")
    if r.unknown_words:
        listed = "; ".join(f"{w} ({', '.join(sorted(p))})" for w, p in sorted(r.unknown_words.items()))
        r.warnings.append(f"Незарегистрированные слова в учебных текстах ({len(r.unknown_words)}): {listed}.")
    return r


def audit_stories_and_poems(r: AuditReport) -> None:
    stories = list(Story.objects.select_related("level", "week").prefetch_related("new_units"))
    poems = list(Poem.objects.select_related("level", "week").prefetch_related("target_units"))
    r.facts.append(f"Историй в карте: {len(stories)} из 60, с текстом: {sum(s.is_published for s in stories)}.")
    r.facts.append(f"Стихов в карте: {len(poems)} из 60, с текстом: {sum(p.is_published for p in poems)}.")
    if stories and len(stories) != 60:
        r.errors.append(f"В карте {len(stories)} историй, нужно 60.")
    if poems and len(poems) != 60:
        r.errors.append(f"В карте {len(poems)} стихов, нужно 60.")
    for lv in LEVELS:
        for kind, items, rng in (("История", stories, lv.stories), ("Стихотворение", poems, lv.poems)):
            for item in items:
                if rng[0] <= item.number <= rng[1] and item.level.code != lv.code:
                    r.errors.append(f"{kind} {item.number} стоит на {item.level.code}, по плану — {lv.code}.")
        level_stories = [s for s in stories if s.level.code == lv.code]
        if level_stories:
            need = STORY_COVERAGE[lv.code]
            for code in "SDJANTPXCOF":
                n = sum(code in s.focus for s in level_stories)
                if n < need:
                    r.errors.append(f"{lv.code}: категория {code} тренируется в {n} историях, нужно не меньше {need}.")

    for story in stories:
        if not story.is_published:
            continue
        where = f"История {story.number}"
        audit_contractions(r, where, story.body)
        plan = LEVEL_BY_CODE[story.level.code]
        new = list(story.new_units.all())
        limit = NEW_WORDS_PER_STORY[plan.block]
        if len(new) > limit:
            r.errors.append(f"{where}: новых слов {len(new)}, лимит {limit}.")
        for u in new:
            if u.internal_level_id != story.level_id or (u.week and story.week and u.week.number > story.week.number):
                r.errors.append(f"{where}: новое слово {u.uid} зарегистрировано позже истории.")
        tokens = text_tokens(story.body)
        low, high = plan.story_words
        if not low <= len(tokens) <= high:
            r.warnings.append(f"{where}: {len(tokens)} слов, норма уровня {low}–{high}.")
        known = vocab_until(story.level, story.week.number if story.week else 99, exclude_ids=[u.pk for u in new])
        new_words = set().union(*(unit_words(u) for u in new)) if new else set()
        unknown = [t for t in tokens if not is_known(t, known)]
        stray = sorted({t.lower() for t in unknown if not is_known(t, new_words)})
        if stray:
            r.errors.append(f"{where}: слова не из программы и не объявлены новыми: {', '.join(stray)}.")
        share = 1 - len(unknown) / max(len(tokens), 1)
        r.facts.append(f"{where}: {len(tokens)} слов, знакомых {share:.0%}, новых единиц {len(new)}.")
        if share < 0.9:
            r.errors.append(f"{where}: знакомых слов {share:.0%}, нужно не меньше 90%.")
        for code in "SD":
            if f"[{code}" not in story.body:
                r.errors.append(f"{where}: не размечены категории {code}.")

    for poem in poems:
        if not poem.is_published:
            continue
        where = f"Стихотворение {poem.number}"
        audit_contractions(r, where, poem.body)
        known = vocab_until(poem.level, poem.week.number if poem.week else 99)
        stray = sorted({t.lower() for t in text_tokens(poem.body) if not is_known(t, known)})
        if stray:
            r.errors.append(f"{where}: незапланированные слова {', '.join(stray)} — стих не должен вводить новую лексику.")
        n = poem.target_units.count()
        if not 6 <= n <= 10:
            r.errors.append(f"{where}: целевых единиц {n}, нужно 6–10.")
        if not 2 <= len(poem.phonetic_goals) <= 3:
            r.warnings.append(f"{where}: фонетических задач {len(poem.phonetic_goals)}, нужно 2–3.")
        lines = poem.body.strip().splitlines()
        for gap in poem.gaps:
            line = strip_markup(lines[gap["line"] - 1]) if gap["line"] <= len(lines) else ""
            if gap["word"].lower() not in line.lower():
                r.errors.append(f"{where}: пропуск «{gap['word']}» не найден в строке {gap['line']}.")
