"""«Классика»: проверка происхождения и сроков охраны текстов для сайта в России."""
from datetime import date
from functools import lru_cache

import yaml
from django.conf import settings
from django.shortcuts import render

# Консервативная историческая проверка для США (оставлена для совместимости).
# В США точный статус зависит от даты/условий публикации, это не полный правовой тест.
PUBLIC_DOMAIN_BEFORE = 1929
RUSSIAN_COPYRIGHT_YEARS = 70


def _expired_in_russia(item: dict, current_year: int) -> None:
    """Проверка обычного срока жизнь автора + 70 лет; спецслучаи требуют правовой проверки."""
    slug = item.get("slug", "<без slug>")
    death_year = item.get("author_death_year")
    if isinstance(death_year, bool) or not isinstance(death_year, int):
        raise ValueError(f"{slug}: требуется целое author_death_year")
    if death_year <= 0 or death_year > current_year:
        raise ValueError(f"{slug}: некорректный author_death_year={death_year}")
    if death_year + RUSSIAN_COPYRIGHT_YEARS >= current_year:
        raise ValueError(
            f"{slug}: срок охраны в России не истёк "
            f"(author_death_year={death_year}, текущий год={current_year})"
        )


def validate_classics_data(data: dict, *, current_year: int | None = None) -> None:
    """Fail closed: неизвестное авторство и неполные сведения не публикуем."""
    if current_year is None:
        current_year = date.today().year

    for poem in data.get("poems", []):
        slug = poem.get("slug", "<без slug>")
        author = poem.get("author")
        if not isinstance(author, str) or not author.strip():
            raise ValueError(f"{slug}: требуется поле author")
        if author in ("folk", "original"):
            if "author_death_year" in poem:
                raise ValueError(f"{slug}: для {author} поле author_death_year запрещено")
            continue

        _expired_in_russia(poem, current_year)
        year = poem.get("year")
        if isinstance(year, bool) or not isinstance(year, int):
            raise ValueError(f"{slug}: требуется год публикации year")
        if year >= PUBLIC_DOMAIN_BEFORE:
            raise ValueError(
                f"{slug}: публикация {year} не проходит историческую проверку США"
            )
        if not poem.get("source_edition") or not poem.get("source_url"):
            raise ValueError(f"{slug}: у авторского исторического стиха нужны источники издания")

    for twister in data.get("twisters", []):
        slug = twister.get("slug", "<без slug>")
        author = twister.get("author")
        if not isinstance(author, str) or not author.strip():
            raise ValueError(f"{slug}: требуется поле author для скороговорки")
        if author == "folk":
            if "author_death_year" in twister:
                raise ValueError(f"{slug}: фольклор без author_death_year")
        elif author == "original":
            raise ValueError(f"{slug}: в разделе допускаются народные либо исторические скороговорки")
        else:
            _expired_in_russia(twister, current_year)


@lru_cache(maxsize=1)
def classics() -> dict:
    path = settings.CONTENT_DIR / "manifests" / "classics.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    validate_classics_data(data)
    return data


def classics_page(request):
    data = classics()
    return render(request, "core/classics.html", {"twisters": data["twisters"], "poems": data["poems"]})
