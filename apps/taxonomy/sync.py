from .registry import CATEGORIES


def sync_registry(PartOfSpeech, SemanticClass) -> None:
    """Записывает реестр в базу. Идемпотентно: можно запускать сколько угодно раз."""
    for cat in CATEGORIES:
        pos, _ = PartOfSpeech.objects.update_or_create(
            code=cat.code,
            defaults=dict(key=cat.key, name_ru=cat.name_ru, grammar_term_ru=cat.grammar_term_ru,
                          marker=cat.marker, order=cat.order, content_word=cat.content_word),
        )
        for number, name_ru, name_en in cat.classes:
            SemanticClass.objects.update_or_create(
                category=pos, number=number, defaults=dict(name_ru=name_ru, name_en=name_en)
            )
