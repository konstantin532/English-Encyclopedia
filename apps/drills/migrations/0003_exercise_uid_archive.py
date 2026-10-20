from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("drills", "0002_practiceitem"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="exercise",
            options={"base_manager_name": "all_objects", "ordering": ["lesson", "order"]},
        ),
        migrations.AddField(
            model_name="exercise",
            name="uid",
            field=models.CharField(blank=True, help_text="Постоянный ID (EX-00001): ответы учеников не «переезжают» при смене порядка",
                                   max_length=12, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="exercise",
            name="is_archived",
            field=models.BooleanField(default=False, help_text="Убрано из курса, но у учеников есть история по нему"),
        ),
    ]
