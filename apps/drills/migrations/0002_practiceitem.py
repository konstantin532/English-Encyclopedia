import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("drills", "0001_initial"),
        ("lessons", "0003_lesson_contractions"),
        ("lexicon", "0004_unit_ipa_ru"),
    ]

    operations = [
        migrations.CreateModel(
            name="PracticeItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveSmallIntegerField()),
                ("kind", models.CharField(choices=[("translate", "Перевод на английский")], default="translate",
                                          max_length=10)),
                ("prompt_ru", models.CharField(max_length=240)),
                ("answer", models.CharField(max_length=200)),
                ("accepted", models.JSONField(blank=True, default=list, help_text="Другие правильные варианты")),
                ("hint_ru", models.CharField(blank=True, max_length=240)),
                ("explanation_ru", models.TextField()),
                ("review_of", models.PositiveSmallIntegerField(
                    help_text="Номер основного задания урока, чьё отложенное повторение можно назначить")),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name="practice_items", to="lessons.lesson")),
                ("units", models.ManyToManyField(blank=True, related_name="practice_items", to="lexicon.lexicalunit")),
            ],
            options={
                "ordering": ["lesson", "order"],
                "constraints": [models.UniqueConstraint(fields=("lesson", "order"), name="uniq_practice_order")],
            },
        ),
    ]
