from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

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


@override_settings(DEBUG=True)
class SeedDevDeckTests(TestCase):
    def setUp(self):
        call_command('seed_cards', stdout=StringIO())

    def test_updates_all_official_cards_without_creating_records(self):
        stdout = StringIO()

        call_command('seed_dev_deck', stdout=stdout)

        self.assertEqual(TarotCard.objects.count(), 78)
        self.assertFalse(TarotCard.objects.filter(meaning_up='').exists())
        fool = TarotCard.objects.get(slug='the-fool')
        self.assertIn('PROVISIONAL EN INGLÉS', fool.meaning_up)
        self.assertIn('luz y sombra, no orientación', fool.meaning_up)
        self.assertIn('orientación invertida', fool.meaning_rev)
        self.assertIn('contenido provisional en inglés', stdout.getvalue())

    @override_settings(DEBUG=False)
    def test_refuses_to_run_outside_debug_without_force(self):
        with self.assertRaisesMessage(CommandError, 'solo para desarrollo'):
            call_command('seed_dev_deck', stdout=StringIO())

    @override_settings(DEBUG=False)
    def test_force_allows_running_outside_debug(self):
        call_command('seed_dev_deck', force=True, stdout=StringIO())

        self.assertFalse(TarotCard.objects.filter(meaning_up='').exists())

    def test_element_warning_names_slug_and_does_not_overwrite(self):
        fool = TarotCard.objects.get(slug='the-fool')
        fool.element = TarotCard.Element.FIRE
        fool.save(update_fields=['element'])
        stdout = StringIO()

        call_command('seed_dev_deck', stdout=stdout)

        fool.refresh_from_db()
        self.assertEqual(fool.element, TarotCard.Element.FIRE)
        self.assertIn('Elemento distinto para the-fool', stdout.getvalue())

    def test_with_images_loads_dataset_files(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            call_command('seed_dev_deck', with_images=True, stdout=StringIO())
            fool = TarotCard.objects.get(slug='the-fool')

            self.assertEqual(fool.image.name, 'cards/m00.jpg')
            self.assertTrue(fool.image.storage.exists(fool.image.name))
