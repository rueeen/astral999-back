from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('readings', '0009_alter_reading_mode')]

    operations = [
        migrations.AddField(
            model_name='reading',
            name='is_exemplar',
            field=models.BooleanField(default=False, verbose_name='es ejemplar'),
        ),
    ]
