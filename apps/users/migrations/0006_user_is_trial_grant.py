from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0005_user_address_as')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_trial_grant',
            field=models.BooleanField(default=False),
        ),
    ]
