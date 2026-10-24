"""Аудит курса (/аудит): количества, реестр, разметка, незарегистрированная лексика."""
import re
from itertools import pairwise
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from django.conf import settings

from apps.curriculum.registry import LEVEL_BY_CODE, LEVELS, NEW_WORDS_PER_STORY, STORY_COVERAGE, validate_plan
from apps.drills.models import Exercise, PracticeItem
from apps.lessons.models import Lesson, LessonLayer
from apps.lexicon.models import CEFR, LexicalUnit, UnitType
from apps.lexicon.phonetics import unknown_symbols
from apps.poems.models import Poem
from apps.stories.models import Story
from apps.taxonomy.markup import find_issues, strip_markup
from apps.taxonomy.registry import validate_registry

WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")
# Отдельный [X1]n't[/] допустим; основа и отрицание требуют разных маркеров.
UNSPLIT_NEGATIVE = re.compile(r"\[([A-Z]\d+)(?:-#[0-9a-fA-F]{6})?\]([^\[]*n['’]t[^\[]*)\[/\]", re.IGNORECASE)
# Окончания форм: books, houses, Anna's — формы слова не плодят новые единицы (раздел 4).
FORM_SUFFIXES = ("'s", "s", "es")
# Сокращения: I'm, it's, you're, don't, isn't.
CONTRACTIONS = ("n't", "'m", "'s", "'re", "'ve", "'ll", "'d")
# Понимание текста без словаря — 95–98% знакомых слов (Hu & Nation, 2000).
# A1 написан до этого правила: его истории нарочно повторяют свои 3–5 новых слов, порог 90%.
STORY_KNOWN_SHARE = 0.95
STORY_KNOWN_SHARE_BY_LEVEL = {"A1": 0.90}
# Повторение прошлого уровня: доля его единиц, встреченных в текстах нового уровня хотя бы RECYCLE_MIN_HITS раз.
RECYCLE_TARGET = 0.70
RECYCLE_MIN_HITS = 2


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
    for unit in LexicalUnit.objects.all():
        words |= unit_words(unit)
    return words


def unit_words(unit) -> set[str]:
    words = {unit.lemma.lower(), *(f.lower() for f in unit.forms or [])}
    if unit.unit_type == UnitType.PHRASE:
        words.update(token.lower() for token in text_tokens(unit.lemma))
    return words


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
        out += [(where, ex.prompt_en.replace("___", "")), (where, ex.answer),
                *[(where, a) for a in ex.accepted], *[(where, a) for a in ex.options]]
    for item in PracticeItem.objects.select_related("lesson"):
        where = f"{item.lesson.slug}/перевод {item.order}"
        out += [(where, item.answer), *[(where, a) for a in item.accepted]]
    for lesson in Lesson.objects.all():
        out += [(f"{lesson.slug}/как это звучит", item["text"]) for item in lesson.sound_notes]
        for pair in lesson.contractions:
            out += [(f"{lesson.slug}/как сокращают", pair.get(key, "")) for key in ("full", "short")]
    return out


def audit_contractions(r: AuditReport, where: str, text: str) -> None:
    for match in UNSPLIT_NEGATIVE.finditer(text):
        if match.group(1).upper() == "X1" and match.group(2).strip().replace("’", "'") == "n't":
            continue
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


# Осознанно новое значение уже известного слова (например, right «правильный» после right «направо»).
NEW_SENSE = "new_sense"


def audit_duplicate_words(r: AuditReport, units) -> None:
    """Новое слово не должно повторять уже изученное: ни как отдельное слово, ни как его форму.

    went — форма go, cats — форма cat: это не новые единицы, а формы в поле forms.
    teacher и teach — разные слова, такое правило их не трогает.
    Второе значение того же слова допустимо только явно: grammar_features: [new_sense].
    """
    def rank(u):
        return (u.internal_level.order, u.week.number if u.week_id else 0, u.uid)

    # Готовые фразы тоже не повторяются: «Good morning!» дважды — ошибка.
    seen_phrases = {}
    for u in sorted((u for u in units if u.unit_type == UnitType.PHRASE or " " in u.lemma.strip()), key=rank):
        key = " ".join(re.sub(r"[^\w' ]", " ", u.lemma.lower().replace("’", "'")).split())
        if key in seen_phrases and NEW_SENSE not in (u.grammar_features or []):
            first = seen_phrases[key]
            r.errors.append(f"{u.uid} {u.lemma}: фраза уже есть в словаре ({first.uid}, {first.internal_level.code}).")
        seen_phrases.setdefault(key, u)

    words = sorted((u for u in units if u.unit_type != UnitType.PHRASE and " " not in u.lemma.strip()), key=rank)
    lemmas, forms = {}, {}
    for u in words:
        lemma = u.lemma.strip().lower()
        new_sense = NEW_SENSE in (u.grammar_features or [])
        if lemma in lemmas and not new_sense:
            first = lemmas[lemma]
            r.errors.append(f"{u.uid} {u.lemma}: слово уже есть в словаре ({first.uid}, {first.internal_level.code}). "
                            f"Если это другое значение, добавьте grammar_features: [{NEW_SENSE}].")
        elif lemma in forms and forms[lemma].uid != u.uid:
            base = forms[lemma]
            r.errors.append(f"{u.uid} {u.lemma}: это форма слова {base.lemma} ({base.uid}), а не новое слово. "
                            f"Добавьте её в forms у {base.uid} и объясните в уроке.")
        lemmas.setdefault(lemma, u)
        for form in u.forms or []:
            form = str(form).strip().lower()
            if not form or "'" in form or form == lemma:
                continue
            owner = lemmas.get(form)
            if owner is not None and owner.uid != u.uid and NEW_SENSE not in (owner.grammar_features or []):
                r.errors.append(f"{u.uid} {u.lemma}: форма {form} совпадает с отдельным словом {owner.uid}.")
            forms.setdefault(form, u)


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
    audit_duplicate_words(r, units)

    for layer in LessonLayer.objects.select_related("lesson"):
        audit_contractions(r, f"{layer.lesson.slug}, слой {layer.number}", layer.body)
        for i in find_issues(layer.body):
            r.errors.append(f"{layer.lesson.slug}, слой {layer.number}: {i.token} — {i.problem}")

    audit_stories_and_poems(r)
    audit_recycling(r)
    from apps.publishing.audit_weeks import audit_weeks

    audit_weeks(r)

    vocab = known_vocabulary()
    for where, text in english_lines():
        if "/слой " not in where:
            audit_contractions(r, where, text)
            for issue in find_issues(text):
                r.errors.append(f"{where}: {issue.token} — {issue.problem}")
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
        for issue in find_issues(story.body):
            r.errors.append(f"{where}: {issue.token} — {issue.problem}")
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
        need = STORY_KNOWN_SHARE_BY_LEVEL.get(story.level.code, STORY_KNOWN_SHARE)
        if share < need:
            r.errors.append(f"{where}: знакомых слов {share:.0%}, нужно не меньше {need:.0%}.")
        for code in "SD":
            if f"[{code}" not in story.body:
                r.errors.append(f"{where}: не размечены категории {code}.")

    for poem in poems:
        if not poem.is_published:
            continue
        where = f"Стихотворение {poem.number}"
        audit_contractions(r, where, poem.body)
        for issue in find_issues(poem.body):
            r.errors.append(f"{where}: {issue.token} — {issue.problem}")
        known = vocab_until(poem.level, poem.week.number if poem.week else 99)
        stray = sorted({t.lower() for t in text_tokens(poem.body) if not is_known(t, known)})
        if stray:
            r.errors.append(f"{where}: незапланированные слова {', '.join(stray)} — стих не должен вводить новую лексику.")
        n = poem.target_units.count()
        if not 6 <= n <= 10:
            r.errors.append(f"{where}: целевых единиц {n}, нужно 6–10.")
        if not 2 <= len(poem.phonetic_goals) <= 3:
            r.warnings.append(f"{where}: фонетических задач {len(poem.phonetic_goals)}, нужно 2–3.")
        lines = [ln for ln in poem.body.strip().splitlines() if ln.strip()]
        if poem.pronunciation and len(poem.pronunciation) != len(lines):
            r.errors.append(f"{where}: строк {len(lines)}, а разборов произношения {len(poem.pronunciation)}.")
        for gap in poem.gaps:
            line = strip_markup(lines[gap["line"] - 1]) if gap["line"] <= len(lines) else ""
            if gap["word"].lower() not in line.lower():
                r.errors.append(f"{where}: пропуск «{gap['word']}» не найден в строке {gap['line']}.")


def token_keys(token: str) -> set[str]:
    """Все основы, по которым токен считается знакомым (как в is_known): сам токен, без сокращения, без окончания."""
    t = token.lower().replace("’", "'")
    keys = {t}
    for c in CONTRACTIONS:
        if t.endswith(c) and len(t) > len(c):
            base = t[: -len(c)]
            keys |= {"can"} if c == "n't" and base == "ca" else {base, base + "n"} if c == "n't" else {base}
    keys |= {t[: -len(suf)] for suf in FORM_SUFFIXES if t.endswith(suf) and len(t) > len(suf)}
    return keys


def level_texts(level) -> list[str]:
    """Связные тексты уровня: опубликованные истории, стихи и диалоги недель."""
    from apps.curriculum.models import WeekScene

    texts = [s.body for s in Story.objects.filter(level=level) if s.is_published]
    texts += [p.body for p in Poem.objects.filter(level=level) if p.is_published]
    for scene in WeekScene.objects.filter(week__level=level):
        texts += [line.get("text", "") for line in scene.script]
    return [t for t in texts if t]


def recycling_counts(prev_units, texts: list[str]) -> dict[str, int]:
    """Сколько раз каждая единица прошлого уровня встречается в текстах: слово — по формам, фраза — целиком."""
    counts = {u.uid: 0 for u in prev_units}
    by_word: dict[str, set[str]] = {}
    phrases = []
    for u in prev_units:
        if u.unit_type == UnitType.PHRASE or len(text_tokens(u.lemma)) != 1:  # T-shirt, ice cream
            phrases.append((u.uid, " ".join(text_tokens(u.lemma)).lower()))
        else:
            for w in {u.lemma.lower(), *(f.lower() for f in u.forms or [])}:
                by_word.setdefault(w, set()).add(u.uid)
    for text in texts:
        tokens = text_tokens(text)
        for tok in tokens:
            for uid in set().union(*(by_word.get(k, set()) for k in token_keys(tok))):
                counts[uid] += 1
        flat = f" {' '.join(tokens).lower()} "
        for uid, phrase in phrases:
            if phrase:
                counts[uid] += flat.count(f" {phrase} ")
    return counts


def audit_recycling(r: AuditReport) -> None:
    """Отчёт «Повторение A1 в A1+»: сколько единиц прошлого уровня снова звучат в текстах нового.

    Это сведения и предупреждение, а не ошибка: уровень строится по неделям, и до конца уровня доля растёт.
    """
    from apps.curriculum.models import Level

    levels = list(Level.objects.order_by("order"))
    for prev, cur in pairwise(levels):
        prev_units = list(LexicalUnit.objects.filter(internal_level=prev))
        if not prev_units:
            continue
        texts = level_texts(cur)
        title = f"Повторение {prev.code} в {cur.code}"
        if not texts:
            if cur.code == "A1+":
                r.facts.append(f"{title}: текстов {cur.code} пока нет.")
            continue
        counts = recycling_counts(prev_units, texts)
        lemma = {u.uid: u.lemma for u in prev_units}
        enough = sum(1 for n in counts.values() if n >= RECYCLE_MIN_HITS)
        share = enough / len(prev_units)
        r.facts.append(f"{title}: {enough} из {len(prev_units)} единиц ({share:.0%}) встречаются "
                       f"не меньше {RECYCLE_MIN_HITS} раз, цель {RECYCLE_TARGET:.0%}.")
        if share < RECYCLE_TARGET:
            missing = sorted(lemma[uid] for uid, n in counts.items() if n == 0)
            shown = ", ".join(missing[:40]) + (f" и ещё {len(missing) - 40}" if len(missing) > 40 else "")
            r.warnings.append(f"{title}: ниже цели. Ещё не встречались ({len(missing)}): {shown}.")
