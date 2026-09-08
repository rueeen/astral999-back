from calendar import monthrange
from datetime import UTC, timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException

from .models import Reading


class QuotaDenied(APIException):
    status_code = 403

    def __init__(self, detail):
        self.detail = detail


def _period(now=None):
    now = now or timezone.now()
    local_now = timezone.localtime(now)
    local_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = monthrange(local_now.year, local_now.month)[1]
    local_end = local_start.replace(day=last_day) + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def get_quota(user):
    start, resets_at = _period()
    plan = 'premium' if user.is_premium else 'free'
    plan_settings = settings.READING_PLAN_LIMITS[plan]
    used = Reading.objects.filter(
        user=user,
        status=Reading.Status.READY,
        created_at__gte=start,
    ).count()
    return {
        'plan': plan,
        'used': used,
        'limit': plan_settings['monthly_limit'],
        'resets_at': resets_at.isoformat(),
        'available_spreads': list(plan_settings['spreads']),
    }


def validate_quota(user, spread):
    quota = get_quota(user)
    if spread not in quota['available_spreads']:
        raise QuotaDenied({
            'detail': 'Esta tirada no está disponible en tu plan.',
            'code': 'spread_not_available',
            **{key: quota[key] for key in ('plan', 'used', 'limit', 'resets_at')},
        })
    if quota['limit'] is not None and quota['used'] >= quota['limit']:
        raise QuotaDenied({
            'detail': 'Alcanzaste el límite mensual de lecturas de tu plan.',
            'code': 'quota_exceeded',
            **{key: quota[key] for key in ('plan', 'used', 'limit', 'resets_at')},
        })
    return quota
