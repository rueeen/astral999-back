from django.db import migrations, models


MAJOR_ELEMENTS = {
    'the-fool': 'air', 'the-magician': 'air', 'the-high-priestess': 'water',
    'the-empress': 'earth', 'the-emperor': 'fire', 'the-hierophant': 'earth',
    'the-lovers': 'air', 'the-chariot': 'water', 'strength': 'fire',
    'the-hermit': 'earth', 'wheel-of-fortune': 'fire', 'justice': 'air',
    'the-hanged-man': 'water', 'death': 'water', 'temperance': 'fire',
    'the-devil': 'earth', 'the-tower': 'fire', 'the-star': 'air',
    'the-moon': 'water', 'the-sun': 'fire', 'judgement': 'fire',
    'the-world': 'earth',
}
SUIT_ELEMENTS = {
    'wands': 'fire', 'cups': 'water', 'swords': 'air', 'pentacles': 'earth',
}


def reduced_number(number):
    while number > 9:
        number = sum(int(digit) for digit in str(number))
    return number


def populate_structured_fields(apps, schema_editor):
    TarotCard = apps.get_model('cards', 'TarotCard')
    for card in TarotCard.objects.all().iterator():
        card.element = MAJOR_ELEMENTS.get(card.slug) or SUIT_ELEMENTS.get(card.suit, 'air')
        card.is_court = card.arcana == 'MINOR' and card.number >= 11
        card.numerology = None if card.is_court else reduced_number(card.number)
        card.save(update_fields=('element', 'is_court', 'numerology'))


def clear_structured_fields(apps, schema_editor):
    TarotCard = apps.get_model('cards', 'TarotCard')
    TarotCard.objects.update(element=None, is_court=False, numerology=None)


class Migration(migrations.Migration):
    dependencies = [('cards', '0002_tarotcard_suit')]

    operations = [
        migrations.AddField(
            model_name='tarotcard', name='element',
            field=models.CharField(
                choices=[('fire', 'Fuego'), ('water', 'Agua'), ('air', 'Aire'), ('earth', 'Tierra')],
                max_length=5, null=True,
            ),
        ),
        migrations.AddField(
            model_name='tarotcard', name='is_court',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tarotcard', name='numerology',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tarotcard', name='yes_no',
            field=models.CharField(
                choices=[('yes', 'Sí'), ('no', 'No'), ('maybe', 'Quizás')],
                default='maybe', max_length=5,
            ),
        ),
        migrations.RunPython(populate_structured_fields, clear_structured_fields),
        migrations.AlterField(
            model_name='tarotcard', name='element',
            field=models.CharField(
                choices=[('fire', 'Fuego'), ('water', 'Agua'), ('air', 'Aire'), ('earth', 'Tierra')],
                max_length=5,
            ),
        ),
    ]
