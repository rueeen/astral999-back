import base64
import json
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from apps.cards.models import TarotCard


# La equivalencia es deliberadamente explícita: los códigos son propios del dataset.
CODE_TO_SLUG = {
    'm00': 'the-fool',
    'm01': 'the-magician',
    'm02': 'the-high-priestess',
    'm03': 'the-empress',
    'm04': 'the-emperor',
    'm05': 'the-hierophant',
    'm06': 'the-lovers',
    'm07': 'the-chariot',
    'm08': 'strength',
    'm09': 'the-hermit',
    'm10': 'wheel-of-fortune',
    'm11': 'justice',
    'm12': 'the-hanged-man',
    'm13': 'death',
    'm14': 'temperance',
    'm15': 'the-devil',
    'm16': 'the-tower',
    'm17': 'the-star',
    'm18': 'the-moon',
    'm19': 'the-sun',
    'm20': 'judgement',
    'm21': 'the-world',
    'w01': 'ace-of-wands',
    'w02': 'two-of-wands',
    'w03': 'three-of-wands',
    'w04': 'four-of-wands',
    'w05': 'five-of-wands',
    'w06': 'six-of-wands',
    'w07': 'seven-of-wands',
    'w08': 'eight-of-wands',
    'w09': 'nine-of-wands',
    'w10': 'ten-of-wands',
    'w11': 'page-of-wands',
    'w12': 'knight-of-wands',
    'w13': 'queen-of-wands',
    'w14': 'king-of-wands',
    'c01': 'ace-of-cups',
    'c02': 'two-of-cups',
    'c03': 'three-of-cups',
    'c04': 'four-of-cups',
    'c05': 'five-of-cups',
    'c06': 'six-of-cups',
    'c07': 'seven-of-cups',
    'c08': 'eight-of-cups',
    'c09': 'nine-of-cups',
    'c10': 'ten-of-cups',
    'c11': 'page-of-cups',
    'c12': 'knight-of-cups',
    'c13': 'queen-of-cups',
    'c14': 'king-of-cups',
    's01': 'ace-of-swords',
    's02': 'two-of-swords',
    's03': 'three-of-swords',
    's04': 'four-of-swords',
    's05': 'five-of-swords',
    's06': 'six-of-swords',
    's07': 'seven-of-swords',
    's08': 'eight-of-swords',
    's09': 'nine-of-swords',
    's10': 'ten-of-swords',
    's11': 'page-of-swords',
    's12': 'knight-of-swords',
    's13': 'queen-of-swords',
    's14': 'king-of-swords',
    'p01': 'ace-of-pentacles',
    'p02': 'two-of-pentacles',
    'p03': 'three-of-pentacles',
    'p04': 'four-of-pentacles',
    'p05': 'five-of-pentacles',
    'p06': 'six-of-pentacles',
    'p07': 'seven-of-pentacles',
    'p08': 'eight-of-pentacles',
    'p09': 'nine-of-pentacles',
    'p10': 'ten-of-pentacles',
    'p11': 'page-of-pentacles',
    'p12': 'knight-of-pentacles',
    'p13': 'queen-of-pentacles',
    'p14': 'king-of-pentacles',
}

SUIT_MAP = {
    'Trump': None,
    'Wands': TarotCard.Suit.WANDS,
    'Cups': TarotCard.Suit.CUPS,
    'Swords': TarotCard.Suit.SWORDS,
    'Pentacles': TarotCard.Suit.PENTACLES,
}
ELEMENT_MAP = {
    'Fire': TarotCard.Element.FIRE,
    'Water': TarotCard.Element.WATER,
    'Air': TarotCard.Element.AIR,
    'Earth': TarotCard.Element.EARTH,
}
PROVISIONAL_PREFIX = '[TEXTO PROVISIONAL EN INGLÉS — luz y sombra, no orientación]'
PROVISIONAL_REVERSED = (
    '[TEXTO PROVISIONAL] La orientación invertida requiere una interpretación '
    'contextual; este dataset de desarrollo no proporciona ese significado.'
)


class Command(BaseCommand):
    help = 'Carga textos provisionales en inglés del dataset de desarrollo de Kaggle.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-images', action='store_true',
            help='Carga también los escaneos Rider-Waite-Smith.',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Permite ejecutar el comando con DEBUG=False.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'seed_dev_deck es solo para desarrollo. Usa --force para continuar '
                'con DEBUG=False.'
            )

        self.stdout.write(self.style.WARNING(
            'ADVERTENCIA: se cargará contenido provisional en inglés; no debe usarse '
            'en producción.'
        ))
        fixture_dir = Path(__file__).resolve().parents[2] / 'fixtures' / 'dev'
        with (fixture_dir / 'tarot_kaggle.json').open(encoding='utf-8') as source:
            dataset = json.load(source)
        cards = dataset['cards'] if isinstance(dataset, dict) else dataset

        updated = 0
        for raw_card in cards:
            image_name = Path(raw_card['img']).name
            code = Path(image_name).stem
            try:
                slug = CODE_TO_SLUG[code]
            except KeyError as error:
                raise CommandError(f'Código de imagen desconocido: {code}') from error

            try:
                card = TarotCard.objects.get(slug=slug)
            except TarotCard.DoesNotExist as error:
                raise CommandError(
                    f'No existe la carta {slug}. Ejecuta seed_cards primero.'
                ) from error

            dataset_element = ELEMENT_MAP.get(raw_card.get('Elemental'))
            if dataset_element and dataset_element != card.element:
                self.stdout.write(self.style.WARNING(
                    f'Elemento distinto para {slug}: base={card.element}, '
                    f'dataset={dataset_element}. No se modifica.'
                ))

            try:
                suit = SUIT_MAP[raw_card['suit']]
            except KeyError as error:
                raise CommandError(
                    f'Palo desconocido para {slug}: {raw_card["suit"]}'
                ) from error

            meanings = raw_card['meanings']
            light_and_shadow = [*meanings.get('light', []), *meanings.get('shadow', [])]
            card.number = int(raw_card['number'])
            card.suit = suit
            card.arcana = (
                TarotCard.Arcana.MAJOR if suit is None else TarotCard.Arcana.MINOR
            )
            card.meaning_up = f'{PROVISIONAL_PREFIX} ' + ' · '.join(light_and_shadow)
            card.meaning_rev = PROVISIONAL_REVERSED
            update_fields = ['number', 'suit', 'arcana', 'meaning_up', 'meaning_rev']

            if options['with_images']:
                image_path = fixture_dir / 'images' / image_name
                encoded_image_path = image_path.with_suffix(image_path.suffix + '.base64')
                if card.image:
                    card.image.delete(save=False)
                if image_path.is_file():
                    with image_path.open('rb') as image_file:
                        card.image.save(image_name, File(image_file), save=False)
                elif encoded_image_path.is_file():
                    try:
                        image_data = base64.b64decode(
                            encoded_image_path.read_text(encoding='ascii').strip(), validate=True
                        )
                    except (ValueError, UnicodeError) as error:
                        raise CommandError(
                            f'La imagen codificada de {slug} no es válida: '
                            f'{encoded_image_path}'
                        ) from error
                    card.image.save(image_name, ContentFile(image_data), save=False)
                else:
                    raise CommandError(
                        f'No se encontró la imagen de {slug}: {image_path} '
                        f'o {encoded_image_path}'
                    )
                update_fields.append('image')

            card.save(update_fields=update_fields)
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Mazo de desarrollo cargado. Cartas actualizadas: {updated}.'
        ))
