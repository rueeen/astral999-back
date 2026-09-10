from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.users.models import User
from apps.users.trial import get_trial_ends_at


class Command(BaseCommand):
    help = 'Concede el plan premium temporal a las cuentas existentes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra cuántas cuentas cambiarían sin modificar la base de datos.',
        )

    def handle(self, *args, **options):
        if not settings.TRIAL_MODE:
            raise CommandError('TRIAL_MODE debe estar activo para conceder la promoción.')

        ends_at = get_trial_ends_at()
        users = User.objects.filter(
            Q(plan=User.Plan.FREE, plan_expires_at__isnull=True)
            | Q(plan=User.Plan.FREE, plan_expires_at__lte=ends_at)
            | Q(plan=User.Plan.PREMIUM, plan_expires_at__lte=ends_at)
        ).exclude(
            plan=User.Plan.PREMIUM,
            plan_expires_at=ends_at,
            is_trial_grant=True,
        )
        affected = users.count()

        if options['dry_run']:
            self.stdout.write(f'Dry run: {affected} cuenta(s) recibirían el plan de prueba.')
            return

        updated = users.update(
            plan=User.Plan.PREMIUM,
            plan_expires_at=ends_at,
            is_trial_grant=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f'{updated} cuenta(s) recibieron el plan de prueba hasta {ends_at.isoformat()}.'
        ))
