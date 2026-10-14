from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lessons", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="lesson",
            name="sound_notes",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
