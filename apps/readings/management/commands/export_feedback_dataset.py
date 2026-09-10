import json

from django.core.management.base import BaseCommand, CommandError

from ...services.feedback import serialize_example, top_rated_readings


class Command(BaseCommand):
    help = 'Exporta lecturas bien valoradas como ejemplos JSONL para revisión o few-shot.'

    def add_arguments(self, parser):
        parser.add_argument('--output', help='Archivo destino; por defecto escribe en stdout.')
        parser.add_argument('--min-score', type=int, default=1)
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        if options['limit'] < 1:
            raise CommandError('--limit debe ser mayor que cero.')
        rows = [
            json.dumps(serialize_example(reading), ensure_ascii=False)
            for reading in top_rated_readings(
                limit=options['limit'], min_score=options['min_score'],
            )
        ]
        content = '\n'.join(rows) + ('\n' if rows else '')
        if options['output']:
            with open(options['output'], 'w', encoding='utf-8') as destination:
                destination.write(content)
            self.stdout.write(self.style.SUCCESS(f'Exportadas {len(rows)} lecturas.'))
        else:
            self.stdout.write(content, ending='')
