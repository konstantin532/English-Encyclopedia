from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_markers_enabled')]

    operations = [
        # A separate migration also repairs databases that already applied 0002.
        migrations.AlterField(
            model_name='user',
            name='markers_enabled',
            field=models.BooleanField(default=False, db_default=False, verbose_name='маркеры в тексте'),
        ),
    ]
