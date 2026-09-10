from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('readings', '0006_modelpricing_reading_token_accounting')]

    operations = [
        migrations.CreateModel(
            name='ApiTopUp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(verbose_name='fecha')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='monto en USD')),
                ('note', models.TextField(blank=True, default='', verbose_name='nota')),
            ],
            options={'verbose_name': 'recarga de API', 'verbose_name_plural': 'recargas de API', 'ordering': ('-date',)},
        ),
        migrations.CreateModel(
            name='AnthropicCostReconciliation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(verbose_name='inicio')),
                ('end_date', models.DateField(verbose_name='fin')),
                ('reported_cost', models.DecimalField(decimal_places=8, max_digits=14, verbose_name='costo informado')),
                ('local_cost', models.DecimalField(decimal_places=8, max_digits=14, verbose_name='costo local')),
                ('difference', models.DecimalField(decimal_places=8, max_digits=14, verbose_name='diferencia')),
                ('synced_at', models.DateTimeField(auto_now_add=True, verbose_name='conciliado')),
            ],
            options={'verbose_name': 'conciliación de costos de Anthropic', 'verbose_name_plural': 'conciliaciones de costos de Anthropic', 'ordering': ('-synced_at',)},
        ),
    ]
