from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [
        # Existing learners keep their lines and their saved color preference.
        migrations.AddField(
            model_name='user', name='markers_enabled',
            field=models.BooleanField(default=True, verbose_name='маркеры в тексте'),
        ),
        # Only accounts created after this migration start with markers off.
        migrations.AlterField(
            model_name='user', name='markers_enabled',
            field=models.BooleanField(default=False, verbose_name='маркеры в тексте'),
        ),
    ]
