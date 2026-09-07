from django.conf import settings
from django.db import models
import uuid


class Reading(models.Model):
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
    tokens_used = models.PositiveIntegerField(blank=True, null=True)
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created_at',)
        indexes = [models.Index(fields=('user', '-created_at'), name='reading_user_created_idx')]

    def __str__(self):
        return f'{self.user} - {self.spread} - {self.created_at:%Y-%m-%d}'
