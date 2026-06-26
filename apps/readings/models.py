from django.conf import settings
from django.db import models


class Reading(models.Model):
    SPREAD_CHOICES = [
        ('one_card', 'One Card'),
        ('three_cards', 'Three Cards'),
        ('celtic_cross', 'Celtic Cross'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='readings')
    question = models.TextField()
    spread = models.CharField(max_length=20, choices=SPREAD_CHOICES)
    cards_drawn = models.JSONField(default=list)
    ai_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.user} - {self.spread} - {self.created_at:%Y-%m-%d}'
