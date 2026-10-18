# Added for resumable, privacy-preserving speech self-review.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0002_weekgoal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SpeechPracticeProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content_key", models.CharField(max_length=110)),
                ("fragment", models.PositiveSmallIntegerField()),
                ("stage", models.PositiveSmallIntegerField(default=0)),
                ("result", models.CharField(
                    choices=[("again", "Повторить сейчас"), ("hard", "С подсказкой"), ("good", "Самостоятельно")],
                    default="again", max_length=5,
                )),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("next_review_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="speech_practice", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["next_review_at", "content_key", "fragment"],
                "indexes": [models.Index(fields=["user", "next_review_at"], name="speech_due_by_user_idx")],
                "constraints": [models.UniqueConstraint(
                    fields=("user", "content_key", "fragment"), name="uniq_speech_progress_per_fragment"
                )],
            },
        )
    ]
