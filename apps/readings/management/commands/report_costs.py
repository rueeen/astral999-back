from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Sum

from apps.readings.models import Reading
from apps.readings.quotas import _period


class Command(BaseCommand):
    help = 'Informa los costos materializados de las lecturas del mes actual.'

    def handle(self, *args, **options):
        start, end = _period()
        readings = Reading.objects.filter(
            created_at__gte=start, created_at__lt=end, cost__isnull=False,
        )
        totals = readings.aggregate(total=Sum('cost'), average=Avg('cost'), count=Count('id'))
        self.stdout.write(f"Gasto del mes: {totals['total'] or 0}")
        self.stdout.write(f"Costo medio por lectura: {totals['average'] or 0}")
        self.stdout.write('\nDesglose por modo:')
        for row in readings.values('mode', 'cost_currency').annotate(
            readings=Count('id'), total=Sum('cost'), average=Avg('cost'),
        ).order_by('mode', 'cost_currency'):
            self.stdout.write(
                f"- {row['mode']}: {row['readings']} lecturas, {row['total']} "
                f"{row['cost_currency']} (media {row['average']})"
            )
        self.stdout.write('\nDiez usuarios con mayor consumo:')
        users = readings.values('user_id', 'user__username', 'cost_currency').annotate(
            readings=Count('id'), total=Sum('cost'),
        ).order_by('-total')[:10]
        for row in users:
            self.stdout.write(
                f"- {row['user__username']} (#{row['user_id']}): {row['readings']} lecturas, "
                f"{row['total']} {row['cost_currency']}"
            )
