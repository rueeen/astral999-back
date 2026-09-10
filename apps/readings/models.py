from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid


class ModelPricing(models.Model):
    model = models.CharField(max_length=120)
    input_price_per_million = models.DecimalField(max_digits=12, decimal_places=6)
    output_price_per_million = models.DecimalField(max_digits=12, decimal_places=6)
    cache_read_price_per_million = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True)
    cache_creation_price_per_million = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    effective_from = models.DateTimeField()

    class Meta:
        ordering = ('-effective_from',)
        constraints = [models.UniqueConstraint(fields=('model', 'effective_from'), name='unique_model_pricing_date')]

    def __str__(self):
        return f'{self.model} desde {self.effective_from:%Y-%m-%d} ({self.currency})'


class ApiTopUp(models.Model):
    date = models.DateTimeField('fecha')
    amount = models.DecimalField('monto en USD', max_digits=14, decimal_places=2)
    note = models.TextField('nota', blank=True, default='')

    class Meta:
        ordering = ('-date',)
        verbose_name = 'recarga de API'
        verbose_name_plural = 'recargas de API'

    def __str__(self):
        return f'{self.date:%Y-%m-%d}: USD {self.amount}'


class AnthropicCostReconciliation(models.Model):
    start_date = models.DateField('inicio')
    end_date = models.DateField('fin')
    reported_cost = models.DecimalField('costo informado', max_digits=14, decimal_places=8)
    local_cost = models.DecimalField('costo local', max_digits=14, decimal_places=8)
    difference = models.DecimalField('diferencia', max_digits=14, decimal_places=8)
    synced_at = models.DateTimeField('conciliado', auto_now_add=True)

    class Meta:
        ordering = ('-synced_at',)
        verbose_name = 'conciliación de costos de Anthropic'
        verbose_name_plural = 'conciliaciones de costos de Anthropic'


class Reading(models.Model):
    class AddressAs(models.TextChoices):
        MASCULINE = 'masculine', 'Masculino'
        FEMININE = 'feminine', 'Femenino'
        NEUTRAL = 'neutral', 'Neutro'

    class Mode(models.TextChoices):
        CLASSIC = 'classic', 'Clásico'
        NEGATIVE = 'negative', 'Negativo'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        READY = 'ready', 'Lista'
        FAILED = 'failed', 'Fallida'

    SPREAD_CHOICES = [
        ('one_card', 'One Card'),
        ('three_cards', 'Three Cards'),
        ('celtic_cross', 'Celtic Cross'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='readings')
    question = models.TextField()
    spread = models.CharField(max_length=20, choices=SPREAD_CHOICES)
    cards_drawn = models.JSONField(default=list)
    ai_response = models.TextField(blank=True, default='')
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CLASSIC)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    model_used = models.CharField(max_length=120, blank=True, null=True)
    # Total histórico anterior a la separación entre entrada y salida.
    legacy_tokens = models.PositiveIntegerField(blank=True, null=True)
    input_tokens = models.PositiveIntegerField(blank=True, null=True)
    output_tokens = models.PositiveIntegerField(blank=True, null=True)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    cache_creation_tokens = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=14, decimal_places=8, blank=True, null=True)
    cost_currency = models.CharField(max_length=3, blank=True, default='')
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    address_as = models.CharField(
        'preferencia de tratamiento al generar', max_length=10,
        choices=AddressAs.choices, default=AddressAs.NEUTRAL, editable=False,
    )

    class Meta:
        ordering = ('-created_at',)
        indexes = [models.Index(fields=('user', '-created_at'), name='reading_user_created_idx')]

    def __str__(self):
        return f'{self.user} - {self.spread} - {self.created_at:%Y-%m-%d}'

    def calculate_cost(self, at=None):
        if not self.model_used or self.input_tokens is None or self.output_tokens is None:
            return None
        pricing = ModelPricing.objects.filter(
            model=self.model_used,
            effective_from__lte=at or self.created_at or timezone.now(),
        ).order_by('-effective_from').first()
        if pricing is None:
            return None
        total = (
            Decimal(self.input_tokens) * pricing.input_price_per_million
            + Decimal(self.output_tokens) * pricing.output_price_per_million
            + Decimal(self.cache_read_tokens) * (
                pricing.cache_read_price_per_million or pricing.input_price_per_million)
            + Decimal(self.cache_creation_tokens) * (
                pricing.cache_creation_price_per_million or pricing.input_price_per_million)
        ) / Decimal(1_000_000)
        return total.quantize(Decimal('0.00000001')), pricing.currency

    def save(self, *args, **kwargs):
        # Solo se fija una vez: los cambios posteriores en la tabla de precios no
        # pueden modificar el costo histórico de una lectura ya contabilizada.
        if self.cost is None:
            calculated = self.calculate_cost()
            if calculated:
                self.cost, self.cost_currency = calculated
                update_fields = kwargs.get('update_fields')
                if update_fields is not None:
                    kwargs['update_fields'] = tuple(set(update_fields) | {'cost', 'cost_currency'})
        return super().save(*args, **kwargs)


class ReadingFeedback(models.Model):
    class Value(models.IntegerChoices):
        LIKE = 1, 'Like'
        DISLIKE = -1, 'Dislike'

    reading = models.ForeignKey(Reading, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='reading_feedback', blank=True, null=True,
    )
    value = models.SmallIntegerField(choices=Value.choices)
    comment = models.TextField(blank=True, default='')
    # Snapshot mínimo para auditar qué produjo la respuesta si los prompts cambian.
    generation_context = models.JSONField(default=dict, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('reading', 'user'), name='unique_reading_feedback_user',
            ),
        ]

    def __str__(self):
        return f'{self.reading_id}: {self.get_value_display()}'
