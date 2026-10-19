# Historical attempts have not_stated; do not reinterpret them as independent.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0008_independent_batch_idempotency")]

    operations = [
        migrations.AddField(
            model_name="independentattempt",
            name="assistance",
            field=models.CharField(
                max_length=16,
                choices=[
                    ("not_stated", "Не указано (старая попытка)"),
                    ("no_help", "Без конспекта и переводчика"),
                    ("notes", "С конспектом или объяснением"),
                    ("translator", "С онлайн-переводчиком или готовым ответом"),
                ],
                default="not_stated",
            ),
        ),
    ]
