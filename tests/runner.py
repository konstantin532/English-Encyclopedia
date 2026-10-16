"""Запуск тестов: контент курса загружается в тестовую базу один раз на весь прогон.

Раньше каждый класс тестов сам вызывал load_content (~3 с), и прогон рос вместе с курсом.
Теперь классы зовут ensure_content(): если курс уже в базе, повторной загрузки нет.
Тесты, которые проверяют сам загрузчик, по-прежнему вызывают load_content явно.
"""
from django.core.management import call_command
from django.test.runner import DiscoverRunner


class ContentLoadedRunner(DiscoverRunner):
    """Курс загружается сразу после создания тестовой базы — до копий для --parallel,
    поэтому каждая параллельная копия уже содержит курс."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.parallel > 1:
            try:
                import tblib  # noqa: F401
            except ImportError:
                print("Внимание: tblib не установлен (uv sync). Если тест упадёт, --parallel покажет "
                      "«cannot pickle 'traceback'» вместо ошибки — тогда запустите этот файл тестов без --parallel.")

    def setup_databases(self, **kwargs):
        from django.db import connections

        for conn in connections.all():
            original = conn.creation.create_test_db

            def create_with_content(*args, _original=original, **kw):
                name = _original(*args, **kw)
                call_command("load_content", verbosity=0)
                return name

            conn.creation.create_test_db = create_with_content
        return super().setup_databases(**kwargs)


def ensure_content() -> None:
    from apps.lexicon.models import LexicalUnit

    if not LexicalUnit.objects.exists():
        call_command("load_content", verbosity=0)
