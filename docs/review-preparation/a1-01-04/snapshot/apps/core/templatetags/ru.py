from django import template

register = template.Library()


@register.filter
def plural_ru(number, forms: str) -> str:
    """{{ n|plural_ru:"учебная единица,учебные единицы,учебных единиц" }} → «3 учебные единицы»."""
    one, few, many = forms.split(",")
    n = abs(int(number))
    if n % 10 == 1 and n % 100 != 11:
        word = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = few
    else:
        word = many
    return f"{number} {word}"


@register.filter
def ru_ipa(ipa, override=""):
    """{{ unit.ipa_us|ru_ipa:unit.ipa_ru }} → русская транскрипция с подсказками трудных звуков."""
    from apps.lexicon.phonetics import render_html

    return render_html(ipa or "", override or "")


@register.simple_tag
def sound_hints():
    """Памятка трудных звуков: [(ключ, русская буква, IPA, название, как произносить)]."""
    from apps.lexicon.phonetics import HINT_LETTERS, HINTS, IPA_OF_HINT

    return [(k, HINT_LETTERS[k], IPA_OF_HINT[k], label, tip) for k, (label, tip) in HINTS.items()]


@register.filter
def ru_tr(item):
    """{{ unit|ru_tr }} или {{ sound_note|ru_tr }}: берёт IPA и ручной русский вариант, если он есть."""
    from apps.lexicon.phonetics import render_html

    if isinstance(item, dict):
        return render_html(item.get("ipa", ""), item.get("ru", ""))
    return render_html(getattr(item, "ipa_us", ""), getattr(item, "ipa_ru", ""))
