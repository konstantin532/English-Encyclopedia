# PostgreSQL enforces varchar length (SQLite does not): phrase IPA and source notes in the
# A1 lexicon were longer than the columns and would fail to load into production.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lexicon", "0004_unit_ipa_ru"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lexicalunit",
            name="ipa_us",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AlterField(
            model_name="lexicalunit",
            name="verification_note",
            field=models.CharField(blank=True, max_length=400),
        ),
    ]
