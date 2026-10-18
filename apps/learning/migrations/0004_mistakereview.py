# A1 spaced review: five new questions become available after 48 hours.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0003_speechpracticeprogress"),
        ("drills", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MistakeReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("due_at", models.DateTimeField()),
                ("current_index", models.PositiveSmallIntegerField(default=0)),
                ("correct_count", models.PositiveSmallIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("exercise", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name="delayed_reviews", to="drills.exercise")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name="mistake_reviews", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["due_at", "pk"],
                "indexes": [
                    models.Index(fields=["user", "completed_at", "due_at"], name="mistake_review_due_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=["user", "exercise"], name="unique_mistake_review"),
                ],
            },
        )
    ]
