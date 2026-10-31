"""Генератор фраз English Encyclopedia: семейства конструкций, подсчёт, выборка.

Идея: каждое семейство — это шаблон со слотами. Слот заполняется не списком слов,
а ПРАВИЛОМ по признакам разметки. Поэтому новые слова уровня A2, B1 … попадают
в старые шаблоны автоматически, а новые грамматические темы открывают новые шаблоны.

Единица подсчёта:
  каркас  — набор знаменательных слов (кто, действие, что, где). Determiner, число,
            тип предложения и обстоятельства времени каркас не меняют.
  фраза   — уникальная строка, которую видит ученик (без вариантов сокращений:
            I'm / I am — одна фраза; проверка принимает оба написания).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from . import morph
from .lexicon import markup_dir
from .spoken import spoken

# ─────────────────────────── 1. Точки разблокировки грамматики ───────────────────────────
# (уровень, неделя). Основание: первое появление конструкции в сценарии недели
# content/seed_weeks/*.yaml (поиск по текстам реплик) и can_do_ru недели. Черновик — редактор
# подтверждает, с какой недели конструкция считается ИЗУЧЕННОЙ, а не только встреченной.
G = {
    "be_aff": (0, 1), "be_neg": (0, 2), "be_q": (0, 2), "this_is": (0, 1),
    "have_poss": (0, 2), "like": (0, 2), "do_q": (0, 2), "want": (0, 3),
    "plural": (0, 3), "numbers_np": (0, 3), "can_i_have": (0, 2),
    "there_is": (0, 5), "some": (0, 5),
    "ps_lexical": (0, 6), "habit_time": (0, 6), "have_meal": (0, 6),
    "ps_3sg": (0, 7), "doesnt": (0, 7),
    "imperative": (0, 8), "freq_adv": (0, 10),
    "cannot": (0, 11), "feel": (0, 11), "have_illness": (0, 11),
    "dont": (0, 12), "dont_imperative": (0, 12), "can_ability": (0, 13),
    # A1+
    "very": (1, 1), "pres_cont": (1, 1), "was_were": (1, 2), "past_time": (1, 2),
    "past_reg": (1, 3), "past_irr": (1, 4), "did": (1, 5), "ago": (1, 6),
    "any": (1, 7), "must": (1, 8), "have_to": (1, 9), "put": (1, 9),
    "could_you": (1, 10), "too_enough": (1, 12), "go_to": (1, 14), "if_will": (1, 15),
}

def _load_usage():
    sets, too, ifw = {}, {}, {}
    path = markup_dir() / "usage.txt"
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cols = [c.strip() for c in line.split("|")]
        name = cols[0]
        if name.startswith("too:"):
            too[name[4:]] = cols[1].split()
        elif name.startswith("if:"):
            # первая колонка — одиночные глаголы через пробел, остальные — готовые группы
            first = [] if cols[1] == "-" else cols[1].split()
            ifw[name[3:]] = first + cols[2:]
        else:
            sets[name] = set(cols[1].split())
    return sets, too, ifw


USAGE, TOO_MAP, IF_ACTIONS = _load_usage()
SIZE = {"S": 1, "M": 2, "L": 3, "X": 4}
TOO_OK = {"expensive", "cheap", "difficult", "easy", "busy", "tired", "sleepy", "hungry", "young", "old", "noisy", "quiet"}
FOOD_CONTAINERS = {"fridge", "cupboard", "box", "bag", "basket", "backpack", "plate"}
MOVABLE = {"obj", "wear", "dish", "utensil", "tool", "instrument", "toy", "device", "mail", "medical"}
FOODISH = {"food", "drink"}
NUM_WORDS = ["two", "three", "four", "five"]  # для «two apples»: ограничено до 5 ради естественности


@dataclass
class Item:
    key: str                      # для подсчёта каркасов
    variants: list                # [(текст, согласование)] ; согласование: 1sg 2 3sg 1pl 3pl -
    unit: object = None


@dataclass
class Row:
    slots: list                   # [(list[Item], skeletal: bool)]
    render: object                # fn(chosen_items_variants, stype) -> str
    stypes: list
    note: str = ""
    new_skeletons: bool = True    # False: строки-варианты уже посчитанных каркасов (отрицание/вопрос)

    def counts(self):
        sk, su = 1, 1
        for pool, skeletal in self.slots:
            if not pool:
                return 0, 0
            if skeletal:
                sk *= len(pool)
            su *= sum(len(i.variants) for i in pool)
        return (sk if self.new_skeletons else 0), su * len(self.stypes)


# ─────────────────────────── 2. Контекст: что ученику уже доступно ───────────────────────────
class Ctx:
    def __init__(self, units, pos):
        self.U = units
        self.pos = pos

    def has(self, gkey):
        return G[gkey] <= self.pos

    def avail(self, lemma):
        u = self.U.get(lemma)
        return u is not None and u.pos <= self.pos

    def words(self, letter=None, pred=None):
        out = []
        for u in self.U.values():
            if u.pos > self.pos:
                continue
            if letter and u.pos_letter != letter:
                continue
            if pred and not pred(u):
                continue
            out.append(u)
        return sorted(out, key=lambda u: u.lemma)


# ─────────────────────────── 3. Признаки существительных ───────────────────────────
DERIVED_TAGS = {
    "weather_time": {"weather", "day", "morning", "afternoon", "evening", "night"},
    "water": {"lake", "river", "sea", "ocean", "water"},
    "area_water": {"lake", "river", "sea", "ocean", "water"},
    "lamp": {"lamp"},
}
TAG_ALIASES = {"person_role": "role"}


def matches(u, spec_tokens):
    for tok in spec_tokens:
        if tok.startswith("#"):
            t = TAG_ALIASES.get(tok[1:], tok[1:])
            if t in u.tags or (u.cls.startswith("S") and u.flags.get(t)) or u.lemma in DERIVED_TAGS.get(t, ()):
                return True
        elif tok == u.lemma:
            return True
    return False


def is_noun(u):
    return u.cls[0] in "S" or u.cls in ("N6", "N9")


def size(u):
    return SIZE.get(u.flags.get("size", "M"), 2)


# ─────────────────────────── 4. Именные группы ───────────────────────────
SUBJ_PRON = {"I": "1sg", "you": "2", "he": "3sg", "she": "3sg", "it": "3sg", "we": "1pl", "they": "3pl"}
OBJ_PRON = ["me", "you", "him", "her", "it", "us", "them"]
POSS = ["my", "your", "his", "her", "our", "their"]


NOT_OWNED_TAGS = {"building", "area", "street", "point", "nature", "weather", "outdoor", "water", "sound", "time",
                  "partday", "weekday", "month", "season", "unit", "money"}


def possessable(u):
    """Можно ли сказать my/your/his … + это слово."""
    if "person" in u.tags:
        return bool(u.flags.get("rel"))
    if u.flags.get("public"):
        return False
    if "home" in u.tags:
        return True
    return not (u.tags & NOT_OWNED_TAGS)


def dets_def(ctx, u, with_the=True):
    out = []
    if with_the and ctx.avail("the") and "kin" not in u.tags:
        out.append("the")
    if possessable(u):
        out += [d for d in POSS if ctx.avail(d)]
    return out


def np_def(ctx, u, allow_pl=True, with_the=True):
    """the/my/… + существительное: [(текст, согласование)]"""
    if u.count == "P":
        return [(u.lemma, "3sg")]
    v = []
    pl_ok = allow_pl and ctx.has("plural") and u.count in ("C", "CU") and not u.flags.get("coll") and "time" not in u.tags
    for d in dets_def(ctx, u, with_the):
        if u.count == "PL":
            v.append((f"{d} {u.lemma}", "3pl"))
            continue
        v.append((f"{d} {u.lemma}", "3sg"))
        if pl_ok and ("person" not in u.tags or d == "the" or u.flags.get("pl_ok")):
            if "kin" in u.tags and not u.flags.get("pl_ok"):
                continue
            v.append((f"{d} {morph.plural(u)}", "3pl"))
    return v


def numbers_ok(u, mode):
    """Где «two/three … + мн.ч.» звучит естественно: родственники, животные, еда, мелкие вещи в покупке."""
    if mode == "have":
        return bool(u.flags.get("pl_ok")) or "animal" in u.tags
    if mode == "want":
        return "food" in u.tags
    if mode == "there":
        return u.count == "C" and "kin" not in u.tags
    return False


def np_indef(ctx, u, numbers="there", some=True):
    """a/an + sg, two..five + pl, some + pl/U, голое U: для have / want / there is."""
    v = []
    if u.count in ("C", "CU"):
        if ctx.avail("a"):
            v.append((f"{morph.article(u)} {u.lemma}", "3sg"))
        if numbers and ctx.has("numbers_np") and u.count == "C" and numbers_ok(u, numbers):
            v += [(f"{n} {morph.plural(u)}", "3pl") for n in NUM_WORDS if ctx.avail(n)]
        if some and ctx.has("some") and ctx.avail("some") and u.count == "C":
            v.append((f"some {morph.plural(u)}", "3pl"))
    if u.count in ("U", "CU"):
        v.append((u.lemma, "3sg"))
        if some and ctx.has("some") and ctx.avail("some"):
            v.append((f"some {u.lemma}", "3sg"))
    if u.count == "PL":
        v.append((u.lemma, "3pl"))
        if some and ctx.has("some") and ctx.avail("some"):
            v.append((f"some {u.lemma}", "3pl"))
    return v


def np_generic(ctx, u):
    """«вообще»: I like apples / I like coffee — мн.ч. исчисляемых, голое неисчисляемое."""
    if u.count in ("U", "CU", "P"):
        return [(u.lemma, "3sg")]
    if u.count == "PL":
        return [(u.lemma, "3pl")]
    if ctx.has("plural"):
        return [(morph.plural(u), "3pl")]
    return []


def subjects(ctx, spec=("#person",), allow_it=False, pronouns=True, need_3sg_ok=True, verb=None, coll=True):
    items = []
    if pronouns and "#person" in spec:
        for p, agr in SUBJ_PRON.items():
            if p == "it" or not ctx.avail(p):
                continue
            items.append(Item(f"pron:{p}", [(p, agr)]))
    if allow_it and ctx.avail("it"):
        items.append(Item("pron:it", [("it", "3sg")]))
    for u in ctx.words("S", lambda u: matches(u, spec)):
        if u.count == "P":
            continue
        if u.flags.get("nonagent") and (verb is None or verb not in USAGE["baby_ok"]):
            continue
        if not coll and u.flags.get("coll"):
            continue
        v = np_def(ctx, u)
        if v:
            items.append(Item(u.lemma, v, u))
    if not need_3sg_ok:  # до введения -s у смысловых глаголов
        items = [Item(i.key, [x for x in i.variants if x[1] != "3sg"], i.unit) for i in items]
        items = [i for i in items if i.variants]
    return items


# ─────────────────────────── 5. Глагольные формы ───────────────────────────
def be(agr, past=False):
    if past:
        return "was" if agr in ("1sg", "3sg") else "were"
    return {"1sg": "am", "3sg": "is"}.get(agr, "are")


def cap(s):
    return s[0].upper() + s[1:]


def present(vu, agr):
    if vu.lemma == "have":
        return "has" if agr == "3sg" else "have"
    return morph.third(vu) if agr == "3sg" else vu.lemma


def clause_ps(subj, agr, vu, rest, stype):
    """Present Simple: утверждение / отрицание / общий вопрос."""
    tail = f" {rest}" if rest else ""
    if stype == "aff":
        return cap(f"{subj} {present(vu, agr)}{tail}.")
    aux = "does" if agr == "3sg" else "do"
    if stype == "neg":
        return cap(f"{subj} {aux} not {vu.lemma}{tail}.")
    return cap(f"{aux} {subj} {vu.lemma}{tail}?")


def ps_types(ctx, agr_set):
    """Какие типы предложений Present Simple уже доступны для данного согласования."""
    t = ["aff"]
    third = "3sg" in agr_set
    if (ctx.has("doesnt") if third else ctx.has("dont")):
        t.append("neg")
    if (ctx.has("doesnt") if third else ctx.has("do_q")):
        t.append("q")
    return t


# ─────────────────────────── 6. Обстоятельства времени ───────────────────────────
def habit_times(ctx):
    out = []
    for pd in ("morning", "afternoon", "evening"):
        if ctx.avail(pd) and ctx.avail("in"):
            out.append(f"in the {pd}")
    if ctx.avail("night") and ctx.avail("at"):
        out.append("at night")
    if ctx.avail("every"):
        out += [f"every {w}" for w in ("day", "week", "morning", "evening", "night", "weekend") if ctx.avail(w)]
    days = [u for u in ctx.words("S", lambda u: "weekday" in u.tags)]
    if ctx.avail("on"):
        out += [f"on {morph.plural(d)}" for d in days]
        if ctx.avail("weekend"):
            out.append("on weekends")
    if ctx.avail("at") and ctx.has("habit_time"):
        hours = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
        out += [f"at {h}" for h in hours if ctx.avail(h)]
    return out


def recent_times(ctx):
    """Недавнее прошлое — для was/were и глаголов состояния."""
    out = []
    if ctx.avail("yesterday"):
        out.append("yesterday")
        out += [f"yesterday {p}" for p in ("morning", "afternoon", "evening") if ctx.avail(p)]
    if ctx.avail("last"):
        out += [f"last {w}" for w in ("night", "weekend") if ctx.avail(w)]
        out += [f"last {d.lemma}" for d in ctx.words("S", lambda u: "weekday" in u.tags)]
    return out


def past_times(ctx):
    out = []
    if ctx.avail("yesterday"):
        out.append("yesterday")
        out += [f"yesterday {p}" for p in ("morning", "afternoon", "evening") if ctx.avail(p)]
    if ctx.avail("last"):
        out += [f"last {w}" for w in ("night", "week", "weekend") if ctx.avail(w)]
        out += [f"last {d.lemma}" for d in ctx.words("S", lambda u: "weekday" in u.tags)]
    if ctx.avail("ago"):  # недавнее прошлое: two days ago, a week ago (*five years ago для мелких действий)
        if ctx.avail("day"):
            out += [f"{n} days ago" for n in ("two", "three") if ctx.avail(n)]
        if ctx.avail("week"):
            out.append("a week ago")
    return out


# ─────────────────────────── 7. Отношения места ───────────────────────────
_LOC_CACHE: dict = {}


def loc_ok(x, prep, y):
    """Может ли X находиться PREP the Y. Результат не зависит от недели ученика — кэшируется."""
    key = (x.lemma, prep, y.lemma)
    hit = _LOC_CACHE.get(key)
    if hit is None:
        hit = _LOC_CACHE[key] = _loc_ok(x, prep, y)
    return hit


def _loc_ok(x, prep, y):
    """Может ли X находиться PREP the Y. Только по признакам разметки."""
    xt, yt, yf = x.tags, y.tags, y.flags
    if x is y:
        return False
    movable = bool(xt & MOVABLE) or bool(xt & FOODISH)
    person, animal = "person" in xt, "animal" in xt
    building = bool(xt & {"building"})
    furniture = bool(xt & {"furniture", "appliance"})
    liquid = "drink" in xt
    if "home" in yt and y.lemma == "home":
        return False  # at home обрабатывается отдельно (без артикля)
    if x.flags.get("coll"):
        return False  # *My family is near the sofa — собирательное не ставим в фразы о месте
    food = bool(xt & FOODISH)
    if food and prep in ("near", "behind", "under", "at", "opposite"):
        return False  # еда лежит НА/В чём-то; *The soup is near the door
    if prep == "in":
        if "container" in yt or "container_mass" in yt:
            if not (movable or animal) or person:
                return False
            holds = yf.get("holds")
            if holds == "food" and not (xt & FOODISH):
                return False
            if holds == "mail" and not (xt & {"mail"}):
                return False
            if holds == "money" and x.lemma not in {"card", "receipt", "ticket", "photo", "stamp", "cash", "money"}:
                return False
            if holds == "dish" and not (xt & {"dish", "utensil"}):
                return False
            if holds == "tool" and not (xt & {"tool"}):
                return False
            if liquid and holds != "food":
                return False
            if animal and x.lemma != "ant" and y.lemma not in ("box", "basket", "bag"):
                return False
            if food and y.lemma not in FOOD_CONTAINERS:
                return False
            capv = SIZE.get(yf.get("cap", "M"), 2)
            return size(x) <= capv and size(x) <= size(y) if "obj" in yt else size(x) <= capv
        if "room_like" in yt:
            return person or animal  # in the shower / in the elevator — только люди
        if yt & {"room", "room_like"}:
            if food:
                return False  # еда — в холодильнике или на столе, а не «в комнате»
            return movable or person or animal or (furniture and not x.flags.get("public")) or "plant" in xt
        if yt & {"building", "building_like"} or "home" in yt:
            return person or animal  # *The pen is in the bank — мелкие вещи в здании не генерируем
        if "vehicle_in" in yt:
            return person or animal or (movable and not liquid and size(x) <= 3)
        if "area" in yt:
            if "water" in yt:
                return person or animal
            return person or animal or (building and y.lemma in ("city", "town", "country", "state")) or ("plant" in xt and y.lemma in ("park", "garden"))
        return False
    if prep == "on":
        if y.lemma == "wall":
            return bool(x.flags.get("wall"))
        if y.lemma == "ceiling":
            return x.lemma in ("lamp", "bulb", "ant")
        if "vehicle_on" in yt:
            return person or (movable and not food and y.lemma != "bike")
        if "street" in yt:
            if y.lemma in ("avenue", "block"):
                return False
            if y.lemma == "corner":
                return person or building
            return person or ("vehicle_in" in xt) or ("vehicle_on" in xt and x.lemma in ("bus", "bike"))
        if yf.get("surf"):
            if yf.get("holds") == "food":
                return "food" in xt
            if y.lemma == "tray":
                return bool(xt & {"dish", "utensil"}) or bool(xt & FOODISH)
            if person:
                return y.lemma in ("sofa", "bed", "chair", "bench", "floor", "grass", "stairs", "rug", "seat", "sand")
            if animal:
                return True
            if furniture:
                return y.lemma in ("floor", "rug") and "furniture" in xt and x.lemma not in ("rug",) and not x.flags.get("public")
            if movable or "plant" in xt:
                if food and y.lemma not in ("table", "counter", "tray", "plate", "desk", "shelf", "bench"):
                    return False
                if y.lemma in ("chair", "seat") and size(x) > 2:
                    return False
                return size(x) <= size(y)
        return False
    if prep == "under":
        if not yf.get("under"):
            return False
        if y.lemma == "tree":
            return person or animal or x.lemma == "bench"
        if y.lemma == "rug":
            return movable and size(x) == 1
        if y.lemma == "sink":
            return x.lemma in ("bucket", "box", "tool", "hammer", "bag", "basket") or animal
        return (movable and not liquid and size(x) <= 3) or animal
    if prep in ("near", "behind"):
        if not yf.get("lm"):
            return False
        y_small_scale = bool(yt & {"furniture", "appliance", "fixture", "obj", "plant"}) and not (yt & {"building", "area", "outdoor"})
        if y.lemma == "tree":
            y_small_scale = False
        if prep == "behind" and "water" in yt:
            return False  # *behind the river
        y_big = (bool(yt & {"building", "outdoor", "area"}) or y.lemma == "tree") and "furniture" not in yt
        if building or "vehicle_in" in xt or "vehicle_on" in xt:
            return y_big
        if person:
            return y_big or bool(yt & {"vehicle_in", "vehicle_on"}) or y.lemma in ("door", "window", "table", "desk", "counter")
        if animal:
            return True
        if movable and not liquid:
            return y_small_scale
        if furniture:
            return y_small_scale and size(y) >= 3 and not x.flags.get("public") and "outdoor" not in yt and y.lemma != "grill"
        return False
    if prep == "at":
        if person or animal:
            return bool(yt & {"building", "point"}) or y.lemma in ("door", "window", "table", "desk", "counter")
        if xt & {"vehicle_on"} and x.lemma in ("bus", "train"):
            return y.lemma in ("station", "stop")
        return False
    if prep == "opposite":
        if "plant" in yt:
            return False  # *opposite the tree
        if "furniture" in yt:
            return False  # *opposite the bench
        return building and bool(yt & {"building", "outdoor"} | ({"area"} if y.lemma in ("park", "square", "garden") else set()))
    return False


PLACE_PREPS = ["in", "on", "under", "near", "behind", "at", "opposite"]


def y_np(ctx, y):
    """Как назвать ориентир: the + сущ.; для своих вещей и комнат — ещё и притяжательные."""
    if not ctx.avail("the"):
        return []
    v = [f"the {y.lemma}"]
    if possessable(y) and y.tags & {"container", "furniture", "room", "home", "obj", "vehicle_in", "appliance"}:
        v += [f"{d} {y.lemma}" for d in ("my", "your") if ctx.avail(d)]  # *Put my milk on her shelf — без «салата» притяжательных
    return v


def x_items(ctx, pred, kind="def"):
    """Подлежащие-«что/кто» для фраз о месте."""
    items = []
    for u in ctx.words("S", pred):
        v = np_def(ctx, u) if kind == "def" else np_indef(ctx, u)
        if v:
            items.append(Item(u.lemma, v, u))
    return items


# ─────────────────────────── 8. Семейства ───────────────────────────
@dataclass
class Family:
    fid: str
    name_ru: str
    unlock: str
    example: str
    build: object
    checks: list = field(default_factory=list)  # какие правила проверки покрывает


def fam_be_adj(ctx, past=False, degree=None):
    rows = []
    stypes = ["aff"] + (["neg"] if ctx.has("be_neg") else []) + (["q"] if ctx.has("be_q") else [])
    times = recent_times(ctx) if past else []
    for a in ctx.words("J", lambda a: a.position in ("both", "pred") and "X" not in a.applies):
        if degree and (a.lemma not in TOO_MAP or "X" in TOO_MAP[a.lemma]):
            continue  # *too beautiful, *lucky enough — too/enough только «мешает / хватает»
        if past and a.lemma not in USAGE["temporary_adj"]:
            continue  # *The colleges were large yesterday — постоянное свойство
        applies = set(TOO_MAP[a.lemma]) if degree else a.applies
        subj = []
        if any(t in applies for t in ("#person", "#person_role", "#kin", "#role")):
            subj += [Item(f"pron:{p}", [(p, agr)]) for p, agr in SUBJ_PRON.items() if p != "it" and ctx.avail(p)]
        if "#weather_time" in applies and ctx.avail("it"):
            subj.append(Item("pron:it", [("it", "3sg")]))
        for u in ctx.words("S", lambda u: u.count != "P" and matches(u, applies) and not u.flags.get("nonagent") or (u.lemma == "baby" and a.lemma in ("happy", "hungry", "sick", "sleepy", "thirsty", "tired"))):
            if u.count == "P":
                continue
            if u.flags.get("coll") and a.cls in ("J4",):
                continue  # *The family is hungry — допустимо, но не для тренажёра
            v = np_def(ctx, u)
            if ctx.avail("this") and u.count in ("C", "CU", "U") and "kin" not in u.tags and "person" not in u.tags:
                v += [(f"this {u.lemma}", "3sg")] + ([(f"that {u.lemma}", "3sg")] if ctx.avail("that") else [])
            if v:
                subj.append(Item(u.lemma, v, u))
        if not subj:
            continue
        if degree == "too":
            adjv = [f"too {a.lemma}"]
        elif degree == "enough":
            if a.lemma not in USAGE["enough_ok"]:
                continue
            adjv = [f"{a.lemma} enough"]
        else:
            adjv = [a.lemma] + ([f"very {a.lemma}"] if a.gradable and ctx.has("very") and ctx.avail("very") else [])
        st = stypes if degree != "enough" else ["neg", "q"]  # *The box is big enough — норм., но в задании «не хватает»
        if degree == "enough":
            st = ["aff", "neg", "q"]

        def render(ch, stype, past=past):
            (s, agr), (adj, _), *rest = ch
            t = f" {rest[0][0]}" if rest and rest[0][0] else ""
            b = be(agr, past)
            if stype == "aff":
                return cap(f"{s} {b} {adj}{t}.")
            if stype == "neg":
                return cap(f"{s} {b} not {adj}{t}.")
            return cap(f"{b} {s} {adj}{t}?")
        slots = [(subj, True), ([Item(a.lemma, [(x, "-") for x in adjv], a)], True)]
        if past:
            slots.append(([Item("t", [(t, "-") for t in times])], False))
        rows.append(Row(slots, render, st))
    return rows


def matches_any_person(a):
    return any(t in a.applies for t in ("#person", "#person_role", "#kin", "#role"))


def loc_rows(ctx, kind, past=False):
    """Общая логика для «X is in the Y», «There is a X in the Y». Кэш на контекст."""
    memo = ctx.__dict__.setdefault("_loc_rows", {})
    if kind not in memo:
        memo[kind] = _loc_rows(ctx, kind)
    return memo[kind]


def _loc_rows(ctx, kind):
    rows = []
    for prep in PLACE_PREPS:
        if not ctx.avail(prep):
            continue
        for y in ctx.words("S", lambda y: y.count != "P"):
            ynp = y_np(ctx, y)
            if not ynp:
                continue
            xs = x_items(ctx, lambda x: x.count != "P" and loc_ok(x, prep, y), kind)
            if kind == "def":
                xs += [Item(f"pron:{p}", [(p, agr)]) for p, agr in SUBJ_PRON.items()
                       if p != "it" and ctx.avail(p) and loc_ok_person(prep, y)]
            if xs:
                rows.append((prep, y, ynp, xs))
    if ctx.avail("home") and ctx.avail("at"):  # at home — без артикля
        xs = [Item(f"pron:{p}", [(p, agr)]) for p, agr in SUBJ_PRON.items() if p != "it" and ctx.avail(p)]
        xs += x_items(ctx, lambda x: "person" in x.tags or "animal" in x.tags, kind)
        rows.append(("at", ctx.U["home"], ["home"], xs))
    return rows


def loc_ok_person(prep, y):
    class P:  # фиктивный «человек» для проверки правила
        tags = {"person"}; flags = {}; lemma = "_person"
    return loc_ok(P, prep, y)


def fam_be_loc(ctx, past=False):
    stypes = ["aff"] + (["neg"] if ctx.has("be_neg") else []) + (["q"] if ctx.has("be_q") else [])
    times = recent_times(ctx) if past else []
    rows = []
    for prep, y, ynp, xs in loc_rows(ctx, "def"):
        if past:  # *Our beds were in your bedroom last Monday — в прошлом «где был» — люди и вещи, которые носят с собой
            xs = [i for i in xs if i.unit is None or i.unit.tags & ({"person", "animal"} | MOVABLE) and not (i.unit.tags & {"medical"})]
            if not xs:
                continue
        def render(ch, stype, prep=prep):
            (s, agr), (yy, _), *rest = ch
            t = f" {rest[0][0]}" if rest and rest[0][0] else ""
            b = be(agr, past)
            if stype == "aff":
                return cap(f"{s} {b} {prep} {yy}{t}.")
            if stype == "neg":
                return cap(f"{s} {b} not {prep} {yy}{t}.")
            return cap(f"{b} {s} {prep} {yy}{t}?")
        slots = [(xs, True), ([Item(f"{prep}:{y.lemma}", [(v, "-") for v in ynp], y)], True)]
        if past:
            slots.append(([Item("t", [(t, "-") for t in times])], False))
        rows.append(Row(slots, render, stypes))
    return rows


def fam_there(ctx, quant=None):
    rows = []
    for prep, y, ynp, xs in loc_rows(ctx, "indef"):
        if y.lemma == "home":
            continue
        new_xs = []
        for it in xs:
            u = it.unit
            if u is None or "kin" in u.tags:
                continue  # *There are two daughters in the school — родственники требуют «чьи»
            if "person" in u.tags and (prep not in ("in", "at") or not (y.tags & {"building", "room", "area", "vehicle_in", "vehicle_on"})):
                continue  # *There are three bosses behind the shop
            if quant == "any":
                v = []
                if u.count in ("U", "CU"):
                    v.append((f"any {u.lemma}", "3sg"))
                if u.count in ("C",) and ctx.has("plural"):
                    v.append((f"any {morph.plural(u)}", "3pl"))
                if u.count == "PL":
                    v.append((f"any {u.lemma}", "3pl"))
            else:
                v = [x for x in it.variants if not x[0].startswith("some ") or ctx.has("some")]
            if v:
                new_xs.append(Item(it.key, v, u))

        def render(ch, stype, prep=prep):
            (x, agr), (yy, _) = ch
            b = "is" if agr == "3sg" else "are"
            if stype == "aff":
                return cap(f"there {b} {x} {prep} {yy}.")
            if stype == "neg":
                return cap(f"there {b} not {x} {prep} {yy}.")
            return cap(f"{b} there {x} {prep} {yy}?")
        ypool = [Item(f"{prep}:{y.lemma}", [(v, "-") for v in ynp], y)]
        if quant == "any":
            rows.append(Row([(new_xs, True), (ypool, True)], render, ["neg", "q"]))
            continue
        # отрицание без any возможно только с a/an: There is not a cat in the box.
        neg_xs = [Item(i.key, [v for v in i.variants if v[0].startswith(("a ", "an "))], i.unit) for i in new_xs]
        q_xs = [Item(i.key, [v for v in i.variants if not v[0].startswith("some ")], i.unit) for i in new_xs]
        rows.append(Row([(new_xs, True), (ypool, True)], render, ["aff"]))
        rows.append(Row([([i for i in neg_xs if i.variants], True), (ypool, True)], render, ["neg"], new_skeletons=False))
        rows.append(Row([([i for i in q_xs if i.variants], True), (ypool, True)], render, ["q"], new_skeletons=False))
    return rows


def fam_this_is(ctx):
    stypes = ["aff"] + (["neg"] if ctx.has("be_neg") else []) + (["q"] if ctx.has("be_q") else [])
    demos = [d for d in ("this", "that") if ctx.avail(d)]
    rows = []
    for u in ctx.words("S", lambda u: u.count in ("C", "CU") and (u.tags & (MOVABLE | {"kin", "role", "building", "home", "room", "animal", "furniture", "appliance", "vehicle_in", "vehicle_on"}))):
        dets = ([d for d in POSS if ctx.avail(d)] if possessable(u) else []) + \
               ([morph.article(u)] if ctx.avail("a") and "kin" not in u.tags else [])
        adjs = [""]
        if "person" not in u.tags:  # *This is my careful customer — без прилагательных у людей
            adjs += [a.lemma for a in ctx.words("J", lambda a: a.lemma in USAGE["this_adj"] and a.position in ("both", "attr") and "X" not in a.applies and matches(u, a.applies))]
        nps = []
        for d in dets:
            for a in adjs:
                art = d
                if d in ("a", "an") and a:
                    art = morph.article_for_word(a, ctx.U)
                nps.append((f"{art} {a+' ' if a else ''}{u.lemma}", "3sg"))

        def render(ch, stype):
            (dm, _), (np, _) = ch
            if stype == "aff":
                return cap(f"{dm} is {np}.")
            if stype == "neg":
                return cap(f"{dm} is not {np}.")
            return cap(f"is {dm} {np}?")
        rows.append(Row([([Item("demo", [(d, "-") for d in demos])], False), ([Item(u.lemma, nps, u)], True)], render, stypes))
    return rows


def obj_items(ctx, vu, spec, mode):
    items = []
    for u in ctx.words(None, lambda u: is_noun(u) and matches(u, spec)):
        if vu.lemma == "eat" and "seasoning" in u.tags:
            continue
        if u.count == "P":
            v = [(u.lemma, "-")]
        elif "meal" in u.tags:
            v = [(u.lemma, "-")]
        elif u.lemma in ("hand", "face", "hair") and vu.lemma == "wash":
            v = [(f"{d} {morph.plural(u) if u.lemma == 'hand' else u.lemma}", "-") for d in POSS if ctx.avail(d)]
        elif "instrument" in u.tags and vu.lemma == "play":
            v = [(f"the {morph.plural(u) if u.lemma == 'drum' else u.lemma}", "-")]
        elif u.lemma == "TV" and vu.lemma == "watch":
            v = [("TV", "-")]
        elif u.lemma in ("music",) or "lang" in u.tags or "subject" in u.tags or u.lemma == "home":
            v = [(u.lemma, "-")]
        elif "person" in u.tags:
            if not u.flags.get("rel"):
                continue  # *She helps the singers — дополнение-человек: свой (my teacher) или местоимение
            v = [(x, "-") for x, _ in np_def(ctx, u)]
        elif mode == "generic":
            v = [(x, "-") for x, _ in np_generic(ctx, u)]
            if vu.lemma not in ("eat", "drink", "cook"):  # I like the soup — да; *She eats the egg on Tuesdays — нет
                v += [(x, "-") for x, _ in np_def(ctx, u, allow_pl=False, with_the=True)[:1]]
        elif mode == "indef":
            v = [(x, "-") for x, _ in np_indef(ctx, u, numbers="want")] + [(f"the {u.lemma}", "-")]
        elif mode == "wear":
            v = [(x, "-") for x, _ in np_indef(ctx, u, numbers=None, some=False)] + [(f"the {u.lemma}", "-")]
        else:
            # дополнение «определённое»: the + сущ., my/your + сущ. Мн.ч. — только для предметов
            v = [(f"the {u.lemma}", "-")]
            if possessable(u):
                v += [(f"{d} {u.lemma}", "-") for d in ("my", "your") if ctx.avail(d)]
        v = list(dict.fromkeys(v))
        if v:
            items.append(Item(u.lemma, v, u))
    if "#person" in spec or "#kin" in spec or "#role" in spec:
        items += [Item(f"pron:{p}", [(p, "-")]) for p in OBJ_PRON if p != "it" and ctx.avail(p) and p != "you"]
    return items


OBJ_MODE = {"like": "generic", "love": "generic", "hate": "generic", "enjoy": "generic",
            "want": "indef", "need": "indef", "have": "indef", "buy": "indef", "order": "indef",
            "make": "indef", "bake": "indef", "cook": "generic", "eat": "generic", "drink": "generic",
            "read": "indef", "write": "indef", "send": "indef", "draw": "indef", "sell": "indef",
            "wear": "wear", "pack": "wear", "recommend": "generic", "drop": "def", "lose": "def", "find": "def"}

# Точное время (at seven) — только для распорядка дня; остальным глаголам — «как часто / когда вообще»
CLOCK_OK = {"work", "start", "finish", "open", "close", "arrive", "leave", "come", "eat", "drink", "cook",
            "walk", "swim", "relax", "rest", "read", "watch", "study", "sleep", "call", "have_meal"}


def times_for(ctx, lemma, stative):
    if stative or lemma in ("live", "know"):
        return []
    t = habit_times(ctx)
    if lemma not in CLOCK_OK:
        t = [x for x in t if not x.split()[-1] in ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")]
    return t


def verb_frames(vu):
    out = []
    for f in vu.frames:
        if f == "X":
            return []
        if f == "I":
            out.append(("I", None, None))
        elif f.startswith("T:"):
            out.append(("T", None, f[2:].split()))
        elif f.startswith("P:") or f.startswith("L:"):
            _, prep, spec = f.split(":", 2)
            out.append((f[0], prep, spec.split()))
        elif f.startswith("SI:"):
            out.append(("SI", None, f[3:].split()))
    return out


def subj_spec(vu):
    for f in vu.frames:
        if f.startswith("S:"):
            return tuple(f[2:].split())
    return ("#person",)


REFL = {"I": "me", "we": "us", "he": "him", "she": "her", "they": "them"}


def no_reflexive(res):
    """*We love us. Если в дополнениях есть местоимения, подлежащее-местоимение
    не сочетается со «своим» объектным местоимением (это требует -self, тема B1)."""
    out = []
    for ftype, subj, objs in res:
        pron_objs = [o for o in objs if o.key.startswith("pron:")]
        if not pron_objs and not ({o.key for o in objs} & {x.key for x in subj}):
            out.append((ftype, subj, objs))
            continue
        nonpron = [x for x in subj if not x.key.startswith("pron:")]
        okeys = {o.key for o in objs}
        plain = [x for x in nonpron if x.key not in okeys]
        if plain:
            out.append((ftype, plain, objs))
        for x in nonpron:  # *The server calls the server
            if x.key in okeys:
                out.append((ftype, [x], [o for o in objs if o.key != x.key]))
        for x in subj:
            if not x.key.startswith("pron:"):
                continue
            p = x.key[5:]
            bad = REFL.get(p)
            o2 = [o for o in objs if not (o.key == f"pron:{bad}" or (bad and o.variants[0][0].endswith(" " + bad)))]
            out.append((ftype, [x], o2))
    return out


def verb_rest_pools(ctx, vu, kind):
    return no_reflexive(_verb_rest_pools(ctx, vu, kind))


def _verb_rest_pools(ctx, vu, kind):
    """Для глагола: список (тип рамки, пул подлежащих, пул «остального»)."""
    res = []
    for ftype, prep, spec in verb_frames(vu):
        if ftype == "SI":
            subj = []
            for u in ctx.words("S", lambda u: matches(u, spec)):
                v = np_def(ctx, u)
                if v:
                    subj.append(Item(u.lemma, v, u))
            res.append(("SI", subj, [Item("-", [("", "-")])]))
            continue
        subj = subjects(ctx, subj_spec(vu), verb=vu.lemma)
        if ftype == "I":
            res.append(("I", subj, [Item("-", [("", "-")])]))
        elif ftype == "T":
            mode = OBJ_MODE.get(vu.lemma, "def")
            objs = obj_items(ctx, vu, spec, mode)
            if objs:
                res.append(("T", subj, objs))
        elif ftype in ("P", "L"):
            if not ctx.avail(prep):
                continue
            objs = []
            for u in ctx.words(None, lambda u: is_noun(u) and matches(u, spec)):
                if u.lemma == "home":
                    objs.append(Item("home", [("at home" if prep == "at" else "", "-")], u))
                    continue
                if "person" in u.tags:
                    if not u.flags.get("rel"):
                        continue
                    v = [f"{prep} {x}" for x, _ in np_def(ctx, u)]
                elif "area" in u.tags or "building" in u.tags:
                    v = [f"{prep} the {u.lemma}"]
                else:
                    v = [f"{prep} {x}" for x, _ in np_def(ctx, u, allow_pl=False)]
                v = [x for x in v if x.strip()]
                if v:
                    objs.append(Item(f"{prep}:{u.lemma}", [(x, "-") for x in dict.fromkeys(v)], u))
            if "#person" in spec:
                objs += [Item(f"pron:{p}", [(f"{prep} {p}", "-")]) for p in OBJ_PRON if ctx.avail(p) and p not in ("it", "you")]
            if objs:
                res.append((ftype, subj, objs))
    return res


def fam_present_simple(ctx, transitive=True, freq=False):
    rows = []
    if not ctx.has("ps_lexical"):
        return rows
    three_ok = ctx.has("ps_3sg")
    times = habit_times(ctx)
    advs = [a for a in ("always", "usually", "often", "sometimes", "never") if ctx.avail(a)] if freq else []
    if freq and not advs:
        return rows
    verbs = [v for v in ctx.words("D") if v.cls[:2] in ("D2", "D3", "D4", "D5", "D6", "D8")]
    for vu in verbs:
        if transitive and vu.lemma not in USAGE["habitual"]:
            continue  # глаголы-«события» (sell the phone) в привычке неестественны
        if vu.lemma in ("like", "love", "hate", "want", "need", "enjoy", "miss"):
            continue  # отдельное семейство F05
        for ftype, subj, rest in verb_rest_pools(ctx, vu, "ps"):
            if transitive != (ftype in ("T", "P")):
                continue
            if vu.lemma == "buy":
                rest = [i for i in rest if i.unit is not None and matches(i.unit, USAGE["habitual_buy"])]
                if not rest:
                    continue
            if not three_ok:
                subj = [Item(i.key, [x for x in i.variants if x[1] != "3sg"], i.unit) for i in subj]
                subj = [i for i in subj if i.variants]
            if not subj:
                continue
            agrs = {a for i in subj for _, a in i.variants}
            st = ["aff"] if freq else ps_types(ctx, agrs)
            times = times_for(ctx, vu.lemma, not vu.prog)
            if freq:
                times = [t for t in times if not t.startswith("every")]  # *I never read every day
            if freq and not vu.prog:
                continue  # *I always like coffee — частотность с глаголами состояния не генерируем

            def render(ch, stype, vu=vu):
                (s, agr), (r, _), (t, _), *adv = ch
                tail = " ".join(x for x in (r, t) if x)
                if freq:
                    a = adv[0][0]
                    return cap(f"{s} {a} {present(vu, agr)}{' ' + tail if tail else ''}.")
                return clause_ps(s, agr, vu, tail, stype)
            slots = [(subj, True), (rest, True), ([Item("t", [("", "-")] + [(t, "-") for t in times])], False)]
            if freq:
                slots.append(([Item("adv", [(a, "-") for a in advs])], False))
            rows.append(Row(slots, render, st, note=vu.lemma))
    if transitive and ctx.has("have_meal"):
        meals = [m for m in ctx.words("S", lambda u: "meal" in u.tags)]
        subj = subjects(ctx, ("#person",), need_3sg_ok=three_ok)
        hv = ctx.U["have"]

        def render(ch, stype):
            (s, agr), (m, _), (t, _), *adv = ch
            tail = " ".join(x for x in (m, t) if x)
            if freq:
                return cap(f"{s} {adv[0][0]} {present(hv, agr)} {tail}.")
            return clause_ps(s, agr, hv, tail, stype)
        times = times_for(ctx, "have_meal", False)
        slots = [(subj, True), ([Item(m.lemma, [(m.lemma, "-")], m) for m in meals], True),
                 ([Item("t", [("", "-")] + [(t, "-") for t in times])], False)]
        if freq:
            slots.append(([Item("adv", [(a, "-") for a in advs])], False))
        rows.append(Row(slots, render, ["aff"] if freq else ps_types(ctx, {"3sg", "1sg"}), note="have_meal"))
    return rows


def fam_have(ctx):
    rows = []
    hv = ctx.U["have"]
    subj = subjects(ctx, ("#person",), coll=False, verb="have")
    st = ["aff"] + (["neg"] if ctx.has("dont") else []) + (["q"] if ctx.has("do_q") else [])
    spec = [t for f in hv.frames if f.startswith("T:") for t in f[2:].split()]
    objs = []
    for u in ctx.words("S", lambda u: matches(u, spec)):
        v = [x for x, _ in np_indef(ctx, u, numbers="have")]
        if u.lemma in ("bus", "train", "plane", "taxi"):
            continue  # *The tourist has some buses
        if u.count == "C" and not u.flags.get("pl_ok"):
            v = [x for x in v if not x.startswith("some ")]  # *I have some phones; но I have some friends
        if v:
            objs.append(Item(u.lemma, [(x, "-") for x in v], u))
    rows.append(Row([(subj, True), (objs, True)], lambda ch, s: clause_ps(ch[0][0], ch[0][1], hv, ch[1][0], s), st, note="have-1 possession"))
    if ctx.has("have_illness"):
        ill = []
        for u in ctx.words("S", lambda u: "illness" in u.tags and u.lemma not in ("pain", "allergy")):
            if u.lemma == "flu":
                ill.append(Item(u.lemma, [("the flu", "-")], u))
            elif u.count in ("C", "CU"):
                ill.append(Item(u.lemma, [(f"{morph.article(u)} {u.lemma}", "-")], u))
        rows.append(Row([(subj, True), (ill, True)], lambda ch, s: clause_ps(ch[0][0], ch[0][1], hv, ch[1][0], s), st, note="have + illness"))
    return rows


def fam_like_want(ctx):
    rows = []
    for lemma in ("like", "love", "hate", "want", "need", "enjoy", "miss"):
        if not ctx.avail(lemma):
            continue
        if lemma in ("like", "love", "hate") and not ctx.has("like"):
            continue
        vu = ctx.U[lemma]
        for ftype, subj, objs in verb_rest_pools(ctx, vu, "ps"):
            if ftype != "T":
                continue
            if not ctx.has("ps_3sg"):
                subj = [Item(i.key, [x for x in i.variants if x[1] != "3sg" or i.key in ("pron:he", "pron:she")], i.unit) for i in subj]
                subj = [i for i in subj if i.variants]
            st = ["aff"] + (["neg"] if ctx.has("dont") else []) + (["q"] if ctx.has("do_q") else [])
            rows.append(Row([(subj, True), (objs, True)], lambda ch, s, vu=vu: clause_ps(ch[0][0], ch[0][1], vu, ch[1][0], s), st, note=lemma))
    return rows


def fam_can(ctx, kind="ability"):
    rows = []
    if kind == "ability":
        if not ctx.has("can_ability"):
            return rows
        ability = {"swim", "dance", "sing", "cook", "drive", "draw", "paint", "speak", "read", "write", "play",
                   "ride", "fix", "repair", "bake", "spell", "teach", "hike", "fly"}
        st = ["aff", "q"] + (["neg"] if ctx.has("cannot") else [])
        for vu in ctx.words("D", lambda v: v.lemma in ability):
            for ftype, subj, rest in verb_rest_pools(ctx, vu, "can"):
                if ftype == "SI":
                    continue

                def render(ch, stype, vu=vu):
                    (s, agr), (r, _) = ch
                    tail = f" {r}" if r else ""
                    if stype == "aff":
                        return cap(f"{s} can {vu.lemma}{tail}.")
                    if stype == "neg":
                        return cap(f"{s} cannot {vu.lemma}{tail}.")
                    return cap(f"can {s} {vu.lemma}{tail}?")
                rows.append(Row([(subj, True), (rest, True)], render, st, note=vu.lemma))
        return rows
    # Can I have …, please? — просьба в кафе / магазине
    if not ctx.has("can_i_have"):
        return rows
    objs = []
    cafe_items = {"napkin", "menu", "receipt", "bag", "fork", "spoon", "knife", "glass", "cup", "plate", "ticket", "map", "towel", "pen"}
    for u in ctx.words("S", lambda u: ((u.tags & FOODISH) or u.lemma in cafe_items) and "meal" not in u.tags):
        v = [x for x, _ in np_indef(ctx, u, numbers="want", some=True)]
        if v:
            objs.append(Item(u.lemma, [(x, "-") for x in v], u))
    please = ctx.avail("please")
    rows.append(Row([(objs, True)], lambda ch, s: cap(f"can I have {ch[0][0]}{', please' if please else ''}?"), ["q"], note="can I have"))
    return rows


def fam_feel(ctx):
    if not ctx.has("feel"):
        return []
    fu = ctx.U["feel"]
    adjs = [a for a in ctx.words("J", lambda a: a.cls == "J4" and a.lemma not in ("alone", "ready", "sure", "afraid", "proud", "allergic", "busy", "lucky", "sore", "well", "glad") or a.lemma in ("cold", "hot", "warm"))]
    subj = subjects(ctx, ("#person",), coll=False, verb="feel")
    st = ps_types(ctx, {"3sg", "1sg"})
    items = [Item(a.lemma, [(a.lemma, "-")] + ([(f"very {a.lemma}", "-")] if ctx.has("very") and a.gradable else []), a) for a in adjs]
    return [Row([(subj, True), (items, True)], lambda ch, s: clause_ps(ch[0][0], ch[0][1], fu, ch[1][0], s), st, note="feel")]


def fam_imperative(ctx):
    if not ctx.has("imperative"):
        return []
    rows = []
    request = {"open", "close", "help", "call", "repeat", "spell", "explain", "show", "bring", "wait", "fix", "check",
               "send", "print", "sign", "carry", "hold", "wash", "clean", "read", "write", "answer", "take", "use",
               "listen", "look", "follow", "cross", "drink", "eat", "pack", "wear", "turn", "move", "feed", "keep"}
    st = ["aff"] + (["neg"] if ctx.has("dont_imperative") else [])
    please = ctx.avail("please")
    for vu in ctx.words("D", lambda v: v.lemma in request):
        for ftype, subj, rest in _verb_rest_pools(ctx, vu, "imp"):  # без подлежащего — без разбиения
            if ftype not in ("T", "P", "I"):
                continue
            rest2 = [Item(i.key, [(x if not x.startswith("a ") else x, "-") for x, _ in i.variants if (x.split() or [""])[0] not in ("two", "three", "four", "five", "some")], i.unit) for i in rest]
            rest2 = [i for i in rest2 if i.variants]

            def render(ch, stype, vu=vu):
                r = ch[0][0]
                p = ch[1][0] if len(ch) > 1 else ""
                tail = f" {r}" if r else ""
                if stype == "aff":
                    return cap(f"{vu.lemma}{tail}{p}.")
                return cap(f"do not {vu.lemma}{tail}.")
            rows.append(Row([(rest2, True), ([Item("p", [("", "-")] + ([(", please", "-")] if please else []))], False)], render, ["aff"], note=vu.lemma))
            if "neg" in st:
                rows.append(Row([(rest2, True)], render, ["neg"], note=vu.lemma + ":neg", new_skeletons=False))
    # turn left / go straight
    dirs = [d for d in ("left", "right") if ctx.avail(d)]
    if ctx.avail("turn") and dirs:
        rows.append(Row([([Item(d, [(d, "-")]) for d in dirs], True)], lambda ch, s: cap(f"turn {ch[0][0]}."), ["aff"], note="turn"))
    if ctx.has("put") and ctx.avail("put"):
        for prep in ("in", "on", "under", "near"):
            if not ctx.avail(prep):
                continue
            for y in ctx.words("S", lambda y: y.count != "P"):
                xs = [Item(x.lemma, [(v, "-") for v, _ in np_def(ctx, x) if v.split()[0] in ("the", "your", "my")], x)
                      for x in ctx.words("S", lambda x: bool(x.tags & (MOVABLE | FOODISH)) and loc_ok(x, prep, y))]
                xs = [i for i in xs if i.variants]
                ynp = y_np(ctx, y)
                if xs and ynp:
                    rows.append(Row([(xs, True), ([Item(f"{prep}:{y.lemma}", [(f"{prep} {v}", "-") for v in ynp], y)], True)],
                                    lambda ch, s: cap(f"put {ch[0][0]} {ch[1][0]}.") if s == "aff" else cap(f"do not put {ch[0][0]} {ch[1][0]}."),
                                    st, note="put"))
    return rows


def fam_could_you(ctx):
    if not ctx.has("could_you"):
        return []
    rows = []
    polite = USAGE["polite_verbs"]
    for r in fam_imperative(ctx):
        if r.note not in polite:
            continue
        slots = r.slots[:1]
        rows.append(Row(slots, (lambda ch, s, n=r.note: " ".join(cap(f"could you {n} {ch[0][0]}, please?").split()).replace(" ,", ",")), ["q"], note=r.note))
    return rows


def fam_pres_cont(ctx):
    if not ctx.has("pres_cont"):
        return []
    rows = []
    times = [t for t in ("now", "today") if ctx.avail(t)]
    for vu in ctx.words("D", lambda v: v.prog and v.cls[:2] in ("D2", "D3", "D4", "D5", "D6", "D8")):
        if vu.lemma not in USAGE["habitual"] | USAGE["progressive_ok"] and not any(f == "I" or f.startswith(("L:", "SI:")) for f in vu.frames):
            continue  # *The strangers are trying your fruit now
        for ftype, subj, rest in verb_rest_pools(ctx, vu, "pc"):
            def render(ch, stype, vu=vu):
                (s, agr), (r, _), (t, _) = ch
                tail = " ".join(x for x in (r, t) if x)
                b = be(agr)
                vi = morph.ing(vu)
                if stype == "aff":
                    return cap(f"{s} {b} {vi}{' ' + tail if tail else ''}.")
                if stype == "neg":
                    return cap(f"{s} {b} not {vi}{' ' + tail if tail else ''}.")
                return cap(f"{b} {s} {vi}{' ' + tail if tail else ''}?")
            rows.append(Row([(subj, True), (rest, True), ([Item("t", [("", "-")] + [(t, "-") for t in times])], False)], render, ["aff", "neg", "q"], note=vu.lemma))
    # I'm having breakfast — have в значении «есть» допускает -ing, have «иметь» — нет
    meals = [m for m in ctx.words("S", lambda u: "meal" in u.tags)]
    subj = subjects(ctx, ("#person",))
    rows.append(Row([(subj, True), ([Item(m.lemma, [(m.lemma, "-")], m) for m in meals], True)],
                    lambda ch, s: cap({"aff": f"{ch[0][0]} {be(ch[0][1])} having {ch[1][0]}.",
                                       "neg": f"{ch[0][0]} {be(ch[0][1])} not having {ch[1][0]}.",
                                       "q": f"{be(ch[0][1])} {ch[0][0]} having {ch[1][0]}?"}[s]), ["aff", "neg", "q"], note="have_meal"))
    return rows


def fam_past(ctx):
    if not ctx.has("past_reg"):
        return []
    rows = []
    times = past_times(ctx)
    for vu in ctx.words("D", lambda v: v.cls[:2] in ("D2", "D3", "D4", "D5", "D6", "D8")):
        if not morph.is_regular(vu) and not ctx.has("past_irr"):
            continue
        tpool = [] if not vu.prog else times  # *Our nurse knew your name last Sunday — у глаголов состояния без точки во времени
        for ftype, subj, rest in verb_rest_pools(ctx, vu, "past"):
            st = ["aff"] + (["neg", "q"] if ctx.has("did") else [])

            def render(ch, stype, vu=vu):
                (s, agr), (r, _), (t, _) = ch
                tail = " ".join(x for x in (r, t) if x)
                tail = f" {tail}" if tail else ""
                if stype == "aff":
                    return cap(f"{s} {morph.past(vu)}{tail}.")
                if stype == "neg":
                    return cap(f"{s} did not {vu.lemma}{tail}.")
                return cap(f"did {s} {vu.lemma}{tail}?")
            rows.append(Row([(subj, True), (rest, True), ([Item("t", [("", "-")] + [(t, "-") for t in tpool])], False)], render, st, note=vu.lemma))
    return rows


def fam_modal(ctx, kind):
    if kind == "must" and not ctx.has("must"):
        return []
    if kind == "have_to" and not ctx.has("have_to"):
        return []
    rows = []
    for vu in ctx.words("D", lambda v: v.lemma in USAGE["rule_verbs"] - {"bring"}):
        for ftype, subj, rest in verb_rest_pools(ctx, vu, "modal"):
            if ftype == "SI":
                continue

            def render(ch, stype, vu=vu):
                (s, agr), (r, _) = ch
                tail = f" {r}" if r else ""
                if kind == "must":
                    return cap(f"{s} must {vu.lemma}{tail}.") if stype == "aff" else cap(f"{s} must not {vu.lemma}{tail}.")
                hv = "has" if agr == "3sg" else "have"
                if stype == "aff":
                    return cap(f"{s} {hv} to {vu.lemma}{tail}.")
                if stype == "neg":
                    return cap(f"{s} {'does' if agr == '3sg' else 'do'} not have to {vu.lemma}{tail}.")
                return cap(f"{'does' if agr == '3sg' else 'do'} {s} have to {vu.lemma}{tail}?")
            st = ["aff", "neg"] + (["q"] if kind == "have_to" else [])
            rows.append(Row([(subj, True), (rest, True)], render, st, note=vu.lemma))
    return rows


def fam_some_any(ctx):
    if not ctx.has("any"):
        return []
    rows = fam_there(ctx, quant="any")
    hv = ctx.U["have"]
    subj = subjects(ctx, ("#person",))
    objs = []
    for u in ctx.words("S", lambda u: (u.tags & FOODISH or u.tags & MOVABLE) and "meal" not in u.tags):
        v = []
        if u.count in ("U", "CU"):
            v.append(f"any {u.lemma}")
        elif u.count == "C":
            v.append(f"any {morph.plural(u)}")
        elif u.count == "PL":
            v.append(f"any {u.lemma}")
        objs.append(Item(u.lemma, [(x, "-") for x in v], u))
    rows.append(Row([(subj, True), (objs, True)], lambda ch, s: clause_ps(ch[0][0], ch[0][1], hv, ch[1][0], s), ["neg", "q"], note="have any"))
    return rows


def fam_if_will(ctx):
    if not ctx.has("if_will"):
        return []
    rows = []
    subj = [(p, a) for p, a in SUBJ_PRON.items() if p != "it" and ctx.avail(p)]
    for w, acts in IF_ACTIONS.items():
        if not ctx.avail(w):
            continue
        ok = []
        for act in acts:
            words = [x for x in act.replace(",", " ").split() if x not in ("a", "an", "the", "to")]
            if all(ctx.avail(x) or x in ("go",) for x in words) and (not act.startswith("go ") or ctx.has("go_to")):
                ok.append(act)
        if not ok:
            continue

        def render(ch, stype, w=w):
            (s, _), (act, _), (order, _) = ch
            neg = " not" if stype == "neg" else ""
            main = f"{s} will{neg} {act}"
            cond = f"if it is {w}"
            return cap(f"{cond}, {main}.") if order == "if_first" else cap(f"{main} {cond}.")
        rows.append(Row([([Item(p, [(p, ag)]) for p, ag in subj], True), ([Item(f"{w}:{x}", [(x, "-")]) for x in ok], True),
                         ([Item("order", [("if_first", "-"), ("if_last", "-")])], False)], render, ["aff"], note=w))
    return rows


FAMILIES = [
    Family("F01", "be + прилагательное", "A1 нед.1", "The soup is hot. Are you tired?", fam_be_adj, ["be_agreement", "adj_fit", "predicative_only"]),
    Family("F02", "be + место", "A1 нед.1 (предлоги — по их неделе)", "The keys are in my bag.", fam_be_loc, ["be_agreement", "prep_fit", "article"]),
    Family("F03", "This/That is + сущ.", "A1 нед.1", "That is a big box. Is this your phone?", fam_this_is, ["article_a_an", "adj_order"]),
    Family("F04", "have/has + сущ.", "A1 нед.2; болезни нед.11", "Tom has two sisters. I have a headache.", fam_have, ["have_has", "do_support", "countability"]),
    Family("F05", "like/want/need + сущ.", "A1 нед.2–3", "I like apples. She wants some water.", fam_like_want, ["generic_plural", "countability", "do_support"]),
    Family("F06", "There is/are", "A1 нед.5", "There are two cups on the table.", fam_there, ["there_agreement", "a_vs_some", "prep_fit"]),
    Family("F07", "Present Simple: действие + что", "A1 нед.6 (he/she — нед.7)", "Mia drinks coffee in the morning.", lambda c: fam_present_simple(c, True), ["third_person_s", "do_support", "verb_object_fit"]),
    Family("F08", "Present Simple: без дополнения / где", "A1 нед.6", "The bank opens at nine. I live in the city.", lambda c: fam_present_simple(c, False), ["third_person_s", "required_place", "nonhuman_subject"]),
    Family("F09", "Наречия частоты", "A1 нед.10", "I always read on Saturdays.", lambda c: fam_present_simple(c, True, freq=True) + fam_present_simple(c, False, freq=True), ["adverb_position"]),
    Family("F10", "can / can't (умение)", "A1 нед.13", "I can swim. Can you drive?", fam_can, ["bare_infinitive_after_modal"]),
    Family("F11", "Can I have …, please?", "A1 нед.2", "Can I have some water, please?", lambda c: fam_can(c, "request"), ["countability", "politeness"]),
    Family("F12", "feel + прилагательное", "A1 нед.11", "I feel tired. Does she feel sick?", fam_feel, ["linking_verb_no_be"]),
    Family("F13", "Повелительное наклонение", "A1 нед.8; put — A1+ нед.9", "Close the door, please. Put the cup on the table.", fam_imperative, ["no_subject", "required_place"]),
    Family("F14", "Present Continuous", "A1+ нед.1", "Mia is baking cookies now. The sink is leaking.", fam_pres_cont, ["be_plus_ing", "stative_verbs"]),
    Family("F15", "was / were", "A1+ нед.2", "I was at the park yesterday.", lambda c: fam_be_adj(c, past=True) + fam_be_loc(c, past=True), ["was_were"]),
    Family("F16", "Past Simple", "A1+ нед.3 (-ed), нед.4 (неправ.), нед.5 (did)", "Tom bought a gift yesterday. Did you call your mom?", fam_past, ["past_form", "did_plus_base"]),
    Family("F17", "some / any", "A1+ нед.7", "Is there any milk in the fridge?", fam_some_any, ["some_any"]),
    Family("F18", "must / must not", "A1+ нед.8", "You must wear a uniform.", lambda c: fam_modal(c, "must"), ["bare_infinitive_after_modal"]),
    Family("F19", "have to / don't have to", "A1+ нед.9", "She has to call the plumber.", lambda c: fam_modal(c, "have_to"), ["have_to_agreement"]),
    Family("F20", "Could you …, please?", "A1+ нед.10", "Could you open the window, please?", fam_could_you, ["politeness"]),
    Family("F21", "too / enough", "A1+ нед.12", "The soup is too hot. The box is not big enough.", lambda c: fam_be_adj(c, degree="too") + fam_be_adj(c, degree="enough") if c.has("too_enough") else [], ["gradable_only", "enough_position"]),
    Family("F22", "if + will", "A1+ нед.15", "If it is sunny, we will go to the beach.", fam_if_will, ["if_present_not_will"]),
]


SOME_OK_IN_QUESTIONS = {"F11", "F17"}  # Can I have some water? — some в просьбе правилен


def split_polarity(rows):
    """some в отрицании и обычном вопросе заменяется на any: *I don't have some milk.
    До введения any (A1+ нед. 7) такие варианты просто не порождаются."""
    out = []
    for r in rows:
        has_some = any(v[0].startswith("some ") or " some " in f" {v[0]}" for pool, _ in r.slots for i in pool for v in i.variants)
        other = [t for t in r.stypes if t != "aff"]
        if not has_some or not other:
            out.append(r)
            continue
        if "aff" in r.stypes:
            out.append(Row(r.slots, r.render, ["aff"], r.note, r.new_skeletons))
        slots = []
        for pool, sk in r.slots:
            np = [Item(i.key, [v for v in i.variants if not (v[0].startswith("some ") or " some " in f" {v[0]}")], i.unit) for i in pool]
            slots.append(([i for i in np if i.variants], sk))
        out.append(Row(slots, r.render, other, r.note, new_skeletons=False if "aff" in r.stypes else r.new_skeletons))
    return out


def build(units, pos):
    ctx = Ctx(units, pos)
    out = {}
    for f in FAMILIES:
        rows = f.build(ctx) or []
        if f.fid not in SOME_OK_IN_QUESTIONS:
            rows = split_polarity(rows)
        out[f.fid] = rows
    return ctx, out


def count(rows):
    sk = su = 0
    for r in rows:
        a, b = r.counts()
        sk += a
        su += b
    return sk, su


def sample(rows, n, rng):
    """Случайные фразы, равномерно по уникальным строкам (вес строки = её число фраз)."""
    weights = [r.counts()[1] for r in rows]
    total = sum(weights)
    out, tries = [], 0
    if not total:
        return out
    seen = set()
    while len(out) < n and tries < n * 40:
        tries += 1
        r = rng.choices(rows, weights)[0]
        chosen = []
        for pool, _ in r.slots:
            it = rng.choice(pool)
            chosen.append(rng.choice(it.variants))
        st = rng.choice(r.stypes)
        s = r.render(chosen, st)
        if s and s not in seen:
            seen.add(s)
            out.append(" ".join(s.split()))
    return out


# ─────────────────────────── 9. Фраза для тренировки ───────────────────────────
@dataclass
class Phrase:
    """Одна фраза для ученика: текст, допустимые ответы и какие единицы в ней участвуют."""
    text: str
    family: str
    family_name_ru: str
    stype: str
    target: str                       # лемма целевого слова
    lemmas: list                      # леммы всех слов фразы по порядку токенов
    accepted: list                    # все верные написания (без учёта сокращений)

    @property
    def tokens(self):
        return tokenize(self.text)


STYPE_RU = {"aff": "утверждение", "neg": "отрицание", "q": "вопрос"}


def tokenize(text):
    import re
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)


@lru_cache(maxsize=1)
def _family_by_id():
    return {f.fid: f for f in FAMILIES}


def form_index(units):
    """форма слова → леммы, у которых есть такая форма (lemma, forms, мн.ч., -s, -ing, прош.вр.)."""
    idx = {}

    def add(form, lemma):
        idx.setdefault(form.lower(), [])
        if lemma not in idx[form.lower()]:
            idx[form.lower()].append(lemma)
    for u in units.values():
        add(u.lemma, u.lemma)
        for f in u.forms:
            for part in tokenize(f):
                add(part, u.lemma)
        if u.cls.startswith("S") and u.count in ("C", "CU"):
            add(morph.plural(u), u.lemma)
        if u.cls.startswith("D") and u.frames:
            for fn in (morph.third, morph.ing, morph.past):
                try:
                    add(fn(u), u.lemma)
                except Exception:  # pragma: no cover - редкая форма без данных
                    pass
    add("an", "a")
    return idx


def row_mentions(row, lemma):
    """Какой слот строки может содержать лемму (None — лемма в глаголе строки)."""
    if row.note == lemma:
        return "verb"
    for i, (pool, _) in enumerate(row.slots):
        for it in pool:
            if (it.unit is not None and it.unit.lemma == lemma) or it.key == lemma or it.key.endswith(":" + lemma):
                return i
    return None


def repeats_noun(lemmas, units):
    """Одно существительное дважды (My mother has a mother) — фраза бессмысленна."""
    nouns = [l for l in lemmas if l and l in units and units[l].cls.startswith("S")]
    return len(nouns) != len(set(nouns))


def spoken_length(text):
    """Сколько слов видит ученик: сокращение (don't, I'm) — одно слово."""
    return len(tokenize(spoken(text)))


def make_phrase(ctx, fams, target, rng, familiar=frozenset(), index=None, tries=40, max_words=None):
    """Фраза, где целевое слово обязательно есть. Остальные знаменательные слова —
    по возможности знакомые (в familiar); иначе — с наименьшим числом незнакомых.
    max_words — потолок длины в живой форме (см. spoken); длиннее фраза не выдаётся.
    Фразы с повтором существительного не выдаются никогда."""
    index = index or form_index(ctx.U)
    cands = []
    for fid, rows in fams.items():
        for r in rows:
            where = row_mentions(r, target)
            if where is not None and r.counts()[1] > 0:
                cands.append((fid, r, where))
    if not cands:
        return None
    best, best_bad = None, None
    for _ in range(tries):
        fid, r, where = rng.choice(cands)
        chosen = []
        for i, (pool, _) in enumerate(r.slots):
            p = pool
            if i == where:
                p = [it for it in pool if (it.unit is not None and it.unit.lemma == target)
                     or it.key == target or it.key.endswith(":" + target)]
            it = rng.choice(p)
            chosen.append(rng.choice(it.variants))
        stype = rng.choice(r.stypes)
        text = r.render(chosen, stype)
        if not text:
            continue
        text = " ".join(text.split())
        if max_words is not None and spoken_length(text) > max_words:
            continue
        lemmas = lemmas_for(text, index, ctx.U, target)
        if repeats_noun(lemmas, ctx.U):
            continue
        content = [l for l in lemmas if l and l != target and ctx.U[l].cls[0] in "SDJ" and ctx.U[l].cls != "D1"]
        bad = sum(1 for l in content if l not in familiar)
        if best is None or bad < best_bad:
            alt = alternatives(fid, r, chosen, stype)
            best = Phrase(text, fid, _family_by_id()[fid].name_ru, stype, target, lemmas, alt)
            best_bad = bad
        if bad == 0:
            break
    return best


def lemmas_for(text, index, units, target=None):
    out = []
    for tok in tokenize(text):
        base = tok.split("'")[0].lower()
        if base == "i":
            base = "I"
        cands = index.get(base.lower(), []) or index.get(base, [])
        if not cands and base in units:
            cands = [base]
        if target in cands:
            out.append(target)
        else:
            out.append(cands[0] if cands else None)
    return out


def alternatives(fid, row, chosen, stype):
    """Все верные ответы для тех же карточек. if + will — обе последовательности частей."""
    first = " ".join(row.render(chosen, stype).split())
    alts = [first]
    if fid == "F22":
        flip = list(chosen)
        flip[-1] = ("if_last", "-") if chosen[-1][0] == "if_first" else ("if_first", "-")
        other = row.render(flip, stype)
        if other:
            alts.append(" ".join(other.split()))
    return alts


@lru_cache(maxsize=24)
def build_cached(version, pos):
    """Сборка семейств для позиции ученика (порядок уровня, неделя). Кэш на процесс."""
    from .lexicon import load
    units, _ = load(version)
    ctx, fams = build(units, pos)
    return ctx, fams, form_index(units)
