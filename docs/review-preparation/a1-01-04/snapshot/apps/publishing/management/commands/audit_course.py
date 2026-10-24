from django.core.management.base import BaseCommand

from apps.publishing.audit import run_audit


class Command(BaseCommand):
    help = "Проверить курс: квоты, реестр маркеров, разметку и незарегистрированную лексику"

    def handle(self, *args, **opts):
        r = run_audit()
        for f in r.facts:
            self.stdout.write(f"  {f}")
        for w in r.warnings:
            self.stdout.write(self.style.WARNING(f"Предупреждение: {w}"))
        for e in r.errors:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
        if r.errors:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Ошибок нет."))
