from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='TarotCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(unique=True)),
                ('arcana', models.CharField(choices=[('MAJOR', 'Major'), ('MINOR', 'Minor')], max_length=5)),
                ('number', models.IntegerField()),
                ('meaning_up', models.TextField()),
                ('meaning_rev', models.TextField()),
                ('keywords', models.JSONField(default=list)),
                ('image', models.ImageField(blank=True, null=True, upload_to='cards/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ('arcana', 'number', 'name')},
        ),
    ]
