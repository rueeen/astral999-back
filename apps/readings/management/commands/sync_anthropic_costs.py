import json
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum

from apps.readings.models import AnthropicCostReconciliation, Reading


class Command(BaseCommand):
    help = 'Concilia el costo local con el informe de costos de la Admin API de Anthropic.'

    def add_arguments(self, parser):
        parser.add_argument('--start', type=date.fromisoformat, help='Fecha inicial inclusiva (AAAA-MM-DD).')
        parser.add_argument('--end', type=date.fromisoformat, help='Fecha final inclusiva (AAAA-MM-DD).')

    def handle(self, *args, **options):
        api_key = settings.ANTHROPIC_ADMIN_API_KEY
        if not api_key:
            self.stdout.write(self.style.WARNING(
                'ANTHROPIC_ADMIN_API_KEY no está configurada; se omite la conciliación.'
            ))
            return

        end = options['end'] or date.today()
        start = options['start'] or end.replace(day=1)
        if end < start:
            raise CommandError('--end no puede ser anterior a --start.')
        end_exclusive = end + timedelta(days=1)

        try:
            reported = self._fetch_cost(api_key, start, end_exclusive)
        except (HTTPError, URLError, TimeoutError, ValueError, InvalidOperation) as error:
            self.stdout.write(self.style.WARNING(
                f'No se pudo consultar la Admin API de Anthropic; se omite la conciliación: {error}'
            ))
            return

        start_at = datetime.combine(start, time.min, tzinfo=datetime_timezone.utc)
        end_at = datetime.combine(end_exclusive, time.min, tzinfo=datetime_timezone.utc)
        local = Reading.objects.filter(
            created_at__gte=start_at, created_at__lt=end_at, cost__isnull=False,
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0')
        reconciliation = AnthropicCostReconciliation.objects.create(
            start_date=start,
            end_date=end,
            reported_cost=reported,
            local_cost=local,
            difference=reported - local,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Conciliación guardada: Anthropic USD {reconciliation.reported_cost}; '
            f'local USD {reconciliation.local_cost}; diferencia USD {reconciliation.difference}.'
        ))

    def _fetch_cost(self, api_key, start, end_exclusive):
        total = Decimal('0')
        page = None
        while True:
            query = {
                'starting_at': f'{start.isoformat()}T00:00:00Z',
                'ending_at': f'{end_exclusive.isoformat()}T00:00:00Z',
                'bucket_width': '1d',
            }
            if page:
                query['page'] = page
            request = Request(
                f'https://api.anthropic.com/v1/organizations/cost_report?{urlencode(query)}',
                headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01'},
            )
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
            for bucket in payload.get('data', []):
                for result in bucket.get('results', []):
                    if result.get('currency', 'USD') == 'USD':
                        total += Decimal(str(result['amount']))
            if not payload.get('has_more'):
                return total
            page = payload.get('next_page')
            if not page:
                raise ValueError('La Admin API indicó otra página sin enviar next_page.')
