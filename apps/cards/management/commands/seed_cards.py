import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.cards.models import TarotCard


class Command(BaseCommand):
    help = 'Carga los arcanos mayores y menores de forma idempotente.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only',
            choices=('major', 'minor'),
            help='Carga únicamente los arcanos mayores o menores.',
        )

    def handle(self, *args, **options):
        created = 0
        updated = 0
        fixture_dir = Path(__file__).resolve().parents[2] / 'fixtures'
        arcana_to_load = (options['only'],) if options['only'] else ('major', 'minor')

        for arcana_name in arcana_to_load:
            fixture_path = fixture_dir / f'{arcana_name}_arcana.json'
            with fixture_path.open(encoding='utf-8') as fixture_file:
                cards = json.load(fixture_file)

            for card in cards:
                defaults = card.copy()
                slug = defaults.pop('slug')
                defaults['arcana'] = getattr(TarotCard.Arcana, arcana_name.upper())
                _, was_created = TarotCard.objects.update_or_create(
                    slug=slug,
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(
            f'Cartas cargadas. Creadas: {created}. Actualizadas: {updated}.'
        ))
