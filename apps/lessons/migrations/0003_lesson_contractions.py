from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lessons", "0002_lesson_sound_notes")]

    operations = [
        migrations.AddField(
            model_name="lesson", name="contractions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
