from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.db import connections, DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from apps.curriculum.models import Level
from apps.curriculum.registry import LEVEL_BY_CODE, TOTAL_POEMS, TOTAL_STORIES, TOTAL_UNITS
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from apps.poems.models import Poem
from apps.stories.models import Story
from apps.taxonomy.models import PartOfSpeech

# Одно предложение уровня A1, в котором встречаются все 11 учебных категорий.
HERO_WORDS = [
    ("Oh", "O", 3, ","), ("well", "F", 1, ","), ("my", "T", 3, ""), ("little", "J", 1, ""),
    ("sister", "S", 1, ""), ("often", "A", 1, ""), ("reads", "D", 2, ""), ("two", "N", 1, ""),
    ("books", "S", 2, ""), ("on", "P", 3, ""), ("Sundays", "S", 7, ""), ("and", "C", 1, ""),
    ("just", "X", 5, ""), ("smiles", "D", 2, "."),
]
HERO_RU = "Ох, ну, моя младшая сестра часто читает две книги по воскресеньям и просто улыбается."
SHORT_NAMES = {
    "S": "существительное", "D": "глагол", "J": "прилагательное", "A": "наречие", "N": "числительное",
    "T": "детерминатив", "P": "предлог", "X": "частица", "C": "союз", "O": "междометие", "F": "дискурс",
}


def hero_tokens():
    from apps.taxonomy.registry import CATEGORY_BY_CODE

    tokens = []
    for word, code, num, punct in HERO_WORDS:
        cls_name = next(n for k, n, _ in CATEGORY_BY_CODE[code].classes if k == num)
        tokens.append({"word": word, "cat": code, "cls": num, "punct": punct,
                       "caption": SHORT_NAMES[code], "label": f"{CATEGORY_BY_CODE[code].name_ru}: {cls_name}"})
    return tokens


@never_cache
def healthz(request):
    """Readiness: a working database, not proof of course/audio quality."""
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


# Герои курса на главной: портреты из «Атласа живого языка», роли — из сюжета A1.
HOME_CHARACTERS = (
    ("anna", "Anna", "Учительница из России. Только что переехала в старый дом — и нашла в нём тайну."),
    ("tom", "Tom", "Сосед и друг. Весёлый, всё теряет, а вещи потом находятся в холодильнике."),
    ("mia", "Mia", "Бариста в кафе на углу. Замечает всё — кроме того, что опаздывает."),
    ("box", "Box", "Кот Анны. Всегда первым находит улику — и садится прямо на неё."),
)


def home(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    from apps.curriculum.views import week_art

    a1_weeks = list(Level.objects.get(code="A1").week_set.select_related("scene")[:4]) \
        if Level.objects.filter(code="A1").exists() else []
    for week in a1_weeks:
        week.art = week_art("A1", week.number)
    levels = list(Level.objects.all())
    for lv in levels:
        plan = LEVEL_BY_CODE.get(lv.code)
        lv.story_count = plan.story_count if plan else 0
        lv.poem_count = plan.poem_count if plan else 0
    return render(request, "core/home.html", {
        "hero": hero_tokens(),
        "hero_ru": HERO_RU,
        "hero_plain": " ".join(w + p for w, _, _, p in HERO_WORDS),
        "categories": PartOfSpeech.objects.prefetch_related("classes"),
        "levels": levels,
        "a1_weeks": a1_weeks,
        "first_week": next((week for week in a1_weeks if week.number == 1), None),
        "characters": [{"key": k, "name": n, "about": a, "img": static(f"img/atlas/portrait-{k}.webp")}
                       for k, n, a in HOME_CHARACTERS],
        "first_lesson": Lesson.objects.filter(is_published=True).first(),
        "lessons": Lesson.objects.filter(is_published=True).select_related("week", "level")[:4],
        "lessons_ready": Lesson.objects.filter(is_published=True).count(),
        "stories_ready": Story.objects.filter(is_published=True).count(),
        "poems_ready": Poem.objects.filter(is_published=True).count(),
        "spotlight_unit": LexicalUnit.objects.filter(uid="LX-00005").select_related("semantic_class").first(),
        "units_ready": LexicalUnit.objects.count(),
        "totals": {"units": TOTAL_UNITS, "stories": TOTAL_STORIES, "poems": TOTAL_POEMS},
    })
