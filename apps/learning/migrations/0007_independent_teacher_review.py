# Teacher review is optional. Historic attempts remain unreviewed.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0006_independentattempt_rubric"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="independentattempt",
            name="teacher_verdict",
            field=models.CharField(
                choices=[
                    ("unreviewed", "Не проверено преподавателем"),
                    ("meets_task", "Смысл и форма подходят"),
                    ("needs_work", "Нужна доработка"),
                    ("unclear", "Неоднозначно, обсудить"),
                ],
                default="unreviewed",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="independentattempt",
            name="teacher_rubric",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="independentattempt",
            name="teacher_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="independentattempt",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="independentattempt",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_independent_attempts", to=settings.AUTH_USER_MODEL),
        ),
    ]
