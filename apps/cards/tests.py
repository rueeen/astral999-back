from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import TarotCard
from .serializers import TarotCardSerializer


class SeedCardsTests(TestCase):
    def seed(self, only=None):
        options = {'stdout': StringIO()}
        if only:
            options['only'] = only
        call_command('seed_cards', **options)

    def test_only_major_loads_22_cards(self):
        self.seed('major')

        self.assertEqual(TarotCard.objects.count(), 22)
        self.assertEqual(TarotCard.objects.filter(arcana=TarotCard.Arcana.MAJOR).count(), 22)

    def test_complete_seed_loads_full_deck_structure(self):
        self.seed()

        self.assertEqual(TarotCard.objects.count(), 78)
        self.assertEqual(TarotCard.objects.filter(arcana=TarotCard.Arcana.MAJOR).count(), 22)
        self.assertEqual(TarotCard.objects.filter(arcana=TarotCard.Arcana.MINOR).count(), 56)
        for suit, _ in TarotCard.Suit.choices:
            self.assertEqual(TarotCard.objects.filter(suit=suit).count(), 14)
        self.assertEqual(TarotCard.objects.filter(is_court=True).count(), 16)
        self.assertEqual(
            TarotCard.objects.values('slug').distinct().count(),
            TarotCard.objects.count(),
        )

    def test_seed_is_idempotent(self):
        self.seed()
        self.seed()

        self.assertEqual(TarotCard.objects.count(), 78)

    def test_serializer_exposes_structured_fields(self):
        self.seed('minor')
        data = TarotCardSerializer(TarotCard.objects.get(slug='page-of-cups')).data

        self.assertEqual(data['element'], TarotCard.Element.WATER)
        self.assertTrue(data['is_court'])
        self.assertIsNone(data['numerology'])
        self.assertIn(data['yes_no'], TarotCard.YesNo.values)
