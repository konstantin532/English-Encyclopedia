from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0009_independent_assistance")]

    operations = [
        migrations.AddField(
            model_name="independentattempt", name="prompt_snapshot",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="independentattempt", name="model_snapshot",
            field=models.TextField(blank=True, default=""),
        ),
    ]
