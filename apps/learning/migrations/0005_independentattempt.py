# Distinguish model agreement from independently verified human language use.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0004_mistakereview"),
        ("lessons", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IndependentAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("skill", models.CharField(max_length=12)),
                ("submitted", models.CharField(max_length=400)),
                ("outcome", models.CharField(choices=[("model_match", "Совпало с образцом"), ("needs_review", "Нужна проверка"), ("self_reported", "Самооценка ученика")], max_length=16)),
                ("self_rating", models.CharField(blank=True, max_length=16)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="independent_attempts", to="lessons.lesson")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="independent_attempts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["user", "lesson", "-created_at"], name="independent_user_lesson_idx")],
            },
        ),
    ]
