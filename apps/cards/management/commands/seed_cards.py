import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.cards.models import TarotCard


class Command(BaseCommand):
    help = 'Seed the 22 Major Arcana tarot cards.'

    def handle(self, *args, **options):
        fixture_path = Path(__file__).resolve().parents[2] / 'fixtures' / 'major_arcana.json'
        with fixture_path.open(encoding='utf-8') as fixture_file:
            cards = json.load(fixture_file)

        created = 0
        updated = 0
        for card in cards:
            _, was_created = TarotCard.objects.update_or_create(
                slug=card['slug'],
                defaults={
                    'name': card['name'],
                    'arcana': TarotCard.Arcana.MAJOR,
                    'number': card['number'],
                    'meaning_up': card['meaning_up'],
                    'meaning_rev': card['meaning_rev'],
                    'keywords': card['keywords'],
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded Major Arcana cards. Created: {created}. Updated: {updated}.'))
