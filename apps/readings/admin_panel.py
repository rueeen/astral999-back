from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Min, Max, Q, Sum
from django.db.models.functions import TruncDate, TruncWeek
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import ApiTopUp, Reading, ReadingFeedback


def _decimal_setting(name):
    try:
        return Decimal(str(getattr(settings, name, '0')))
    except InvalidOperation:
        return Decimal('0')


def panel(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('admin:login')}?next={request.path}")
    if not request.user.is_staff:
        raise PermissionDenied

    today = timezone.localdate()
    chart_start = today - timedelta(days=29)
    chart_start_at = timezone.make_aware(datetime.combine(chart_start, time.min))
    month_start = today.replace(day=1)
    month_start_at = timezone.make_aware(datetime.combine(month_start, time.min))
    base = Reading.objects.filter(created_at__gte=chart_start_at)

    readings_by_day = list(base.annotate(day=TruncDate('created_at')).values('day', 'mode').annotate(
        count=Count('id'),
    ).order_by('day', 'mode'))
    costs_by_day = list(base.annotate(day=TruncDate('created_at')).values('day').annotate(
        cost=Sum('cost'),
    ).order_by('day'))
    failures_by_day = list(base.annotate(day=TruncDate('created_at')).values('day').annotate(
        total=Count('id'), failed=Count('id', filter=Q(status=Reading.Status.FAILED)),
    ).order_by('day'))
    spreads = list(base.values('spread').annotate(count=Count('id')).order_by('spread'))
    active_users = list(base.annotate(day=TruncDate('created_at')).values('day').annotate(
        count=Count('user_id', distinct=True),
    ).order_by('day'))

    month = Reading.objects.filter(created_at__gte=month_start_at).aggregate(
        readings=Count('id'), cost=Sum('cost'), users=Count('user_id', distinct=True),
    )
    month_cost = month['cost'] or Decimal('0')
    average_cost = month_cost / month['readings'] if month['readings'] else Decimal('0')

    top_ups = ApiTopUp.objects.aggregate(total=Sum('amount'), first=Min('date'), last=Max('date'))
    consumed = Decimal('0')
    if top_ups['first']:
        consumed = Reading.objects.filter(
            created_at__gte=top_ups['first'], cost__isnull=False,
        ).aggregate(total=Sum('cost'))['total'] or Decimal('0')
    estimated_balance = (top_ups['total'] or Decimal('0')) - consumed
    low_threshold = _decimal_setting('LOW_BALANCE_THRESHOLD')
    monthly_budget = _decimal_setting('MONTHLY_BUDGET')

    mode_totals = {
        row['mode']: row
        for row in ReadingFeedback.objects.values(mode=F('reading__mode')).annotate(
        likes=Count('id', filter=Q(value=ReadingFeedback.Value.LIKE)),
        dislikes=Count('id', filter=Q(value=ReadingFeedback.Value.DISLIKE)),
        total=Count('id'),
        )
    }
    feedback_by_mode = [
        mode_totals.get(mode, {'mode': mode, 'likes': 0, 'dislikes': 0, 'total': 0})
        for mode in Reading.Mode.values
    ]
    spread_totals = {
        row['spread']: row
        for row in ReadingFeedback.objects.values(spread=F('reading__spread')).annotate(
        likes=Count('id', filter=Q(value=ReadingFeedback.Value.LIKE)),
        dislikes=Count('id', filter=Q(value=ReadingFeedback.Value.DISLIKE)),
        total=Count('id'),
        )
    }
    feedback_by_spread = [
        spread_totals.get(spread, {'spread': spread, 'likes': 0, 'dislikes': 0, 'total': 0})
        for spread, _label in Reading.SPREAD_CHOICES
    ]
    feedback_by_week = list(ReadingFeedback.objects.annotate(
        week=TruncWeek('created_at'),
    ).values('week').annotate(
        likes=Count('id', filter=Q(value=ReadingFeedback.Value.LIKE)),
        dislikes=Count('id', filter=Q(value=ReadingFeedback.Value.DISLIKE)),
    ).order_by('week'))
    recent_comments = list(ReadingFeedback.objects.exclude(comment='').select_related(
        'reading',
    ).order_by('-created_at')[:20])
    participation = Reading.objects.aggregate(
        readings=Count('id'), rated=Count('id', filter=Q(feedback__isnull=False), distinct=True),
    )
    participation_rate = (
        participation['rated'] * 100 / participation['readings']
        if participation['readings'] else 0
    )
    for rows in (feedback_by_mode, feedback_by_spread):
        for row in rows:
            row['like_rate'] = row['likes'] * 100 / row['total'] if row['total'] else 0
    feedback_total = sum(row['total'] for row in feedback_by_mode)

    context = {
        **admin.site.each_context(request),
        'title': 'Panel de uso y costo',
        'readings_by_day': readings_by_day,
        'costs_by_day': costs_by_day,
        'failures_by_day': failures_by_day,
        'spreads': spreads,
        'active_users': active_users,
        'month_readings': month['readings'],
        'month_cost': month_cost,
        'average_cost': average_cost,
        'month_users': month['users'],
        'estimated_balance': estimated_balance,
        'last_top_up': top_ups['last'],
        'low_balance': bool(top_ups['first'] and low_threshold > 0 and estimated_balance < low_threshold),
        'over_budget': bool(monthly_budget > 0 and month_cost >= monthly_budget * Decimal('0.8')),
        'monthly_budget': monthly_budget,
        'feedback_by_mode': feedback_by_mode,
        'feedback_total': feedback_total,
        'feedback_by_spread': feedback_by_spread,
        'feedback_by_week': feedback_by_week,
        'recent_comments': recent_comments,
        'rated_readings': participation['rated'],
        'participation_rate': participation_rate,
    }
    return render(request, 'admin/readings/panel.html', context)
