# Race-safe idempotency for newly created four-answer batches.
# Existing attempts have an empty token and remain untouched.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0007_independent_teacher_review")]

    operations = [
        migrations.AddField(
            model_name="independentattempt",
            name="batch_token",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="independentattempt",
            constraint=models.UniqueConstraint(
                fields=("user", "lesson", "skill", "batch_token"),
                condition=~models.Q(batch_token=""),
                name="unique_independent_batch_skill_token",
            ),
        ),
    ]
