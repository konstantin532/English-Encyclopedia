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
