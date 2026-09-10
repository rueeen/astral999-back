from datetime import datetime, time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


def get_trial_ends_at():
    """Devuelve TRIAL_ENDS_AT como datetime consciente de zona horaria."""
    configured_value = settings.TRIAL_ENDS_AT
    if isinstance(configured_value, datetime):
        ends_at = configured_value
    else:
        value = str(configured_value).strip()
        ends_at = parse_datetime(value)
        if ends_at is None:
            date_value = parse_date(value)
            ends_at = datetime.combine(date_value, time.min) if date_value else None

    if ends_at is None:
        raise ImproperlyConfigured(
            'TRIAL_ENDS_AT debe contener una fecha ISO válida cuando TRIAL_MODE=True.'
        )
    if timezone.is_naive(ends_at):
        ends_at = timezone.make_aware(ends_at)
    return ends_at
