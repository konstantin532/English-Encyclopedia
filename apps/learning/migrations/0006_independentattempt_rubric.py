# Generated for independent practice; all existing attempts retain variant 0.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0005_independentattempt"),
    ]

    operations = [
        migrations.AddField(
            model_name="independentattempt",
            name="task_variant",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="independentattempt",
            name="self_rubric",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
