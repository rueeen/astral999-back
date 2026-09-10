from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('readings', '0005_reading_address_as_reading_is_public')]

    operations = [
        migrations.RenameField(
            model_name='reading', old_name='tokens_used', new_name='legacy_tokens',
        ),
        migrations.CreateModel(
            name='ModelPricing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', models.CharField(max_length=120)),
                ('input_price_per_million', models.DecimalField(decimal_places=6, max_digits=12)),
                ('output_price_per_million', models.DecimalField(decimal_places=6, max_digits=12)),
                ('cache_read_price_per_million', models.DecimalField(blank=True, decimal_places=6, max_digits=12, null=True)),
                ('cache_creation_price_per_million', models.DecimalField(blank=True, decimal_places=6, max_digits=12, null=True)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('effective_from', models.DateTimeField()),
            ],
            options={'ordering': ('-effective_from',)},
        ),
        migrations.AddConstraint(
            model_name='modelpricing',
            constraint=models.UniqueConstraint(fields=('model', 'effective_from'), name='unique_model_pricing_date'),
        ),
        migrations.AddField(model_name='reading', name='input_tokens', field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='reading', name='output_tokens', field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='reading', name='cache_read_tokens', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='reading', name='cache_creation_tokens', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='reading', name='cost', field=models.DecimalField(blank=True, decimal_places=8, max_digits=14, null=True)),
        migrations.AddField(model_name='reading', name='cost_currency', field=models.CharField(blank=True, default='', max_length=3)),
    ]
