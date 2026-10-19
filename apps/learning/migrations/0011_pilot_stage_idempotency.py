# Generated for the opt-in 7/30-day transfer pilot; existing rows stay intact.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0010_independent_prompt_snapshot"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="independentattempt",
            constraint=models.UniqueConstraint(
                fields=("user", "lesson", "skill", "task_variant"),
                condition=models.Q(skill="transfer", task_variant__in=[100, 101, 102]),
                name="unique_pilot_stage_per_learner",
            ),
        ),
    ]
