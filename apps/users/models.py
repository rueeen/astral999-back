from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class AddressAs(models.TextChoices):
        MASCULINE = 'masculine', 'Masculino'
        FEMININE = 'feminine', 'Femenino'
        NEUTRAL = 'neutral', 'Neutro'

    class Plan(models.TextChoices):
        FREE = 'free', 'Gratis'
        PREMIUM = 'premium', 'Premium'

    email = models.EmailField('email', unique=True)
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    plan_expires_at = models.DateTimeField(blank=True, null=True)
    is_trial_grant = models.BooleanField(default=False)
    address_as = models.CharField(
        'preferencia de tratamiento', max_length=10,
        choices=AddressAs.choices, default=AddressAs.NEUTRAL,
    )
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # Datos astrológicos para personalizar lecturas
    birth_date = models.DateField(blank=True, null=True)
    birth_time = models.TimeField(blank=True, null=True)
    birth_place = models.CharField(max_length=120, blank=True)

    @property
    def is_premium(self):
        return self.plan == self.Plan.PREMIUM and (
            self.plan_expires_at is None or self.plan_expires_at > timezone.now()
        )

    def get_zodiac_sign(self):
        """Retorna el signo solar basado en birth_date."""
        if not self.birth_date:
            return None
        month = self.birth_date.month
        day = self.birth_date.day
        signs = [
            ((1, 20), (2, 18), 'Acuario'),
            ((2, 19), (3, 20), 'Piscis'),
            ((3, 21), (4, 19), 'Aries'),
            ((4, 20), (5, 20), 'Tauro'),
            ((5, 21), (6, 20), 'Géminis'),
            ((6, 21), (7, 22), 'Cáncer'),
            ((7, 23), (8, 22), 'Leo'),
            ((8, 23), (9, 22), 'Virgo'),
            ((9, 23), (10, 22), 'Libra'),
            ((10, 23), (11, 21), 'Escorpio'),
            ((11, 22), (12, 21), 'Sagitario'),
            ((12, 22), (1, 19), 'Capricornio'),
        ]
        for start, end, sign in signs:
            if (month == start[0] and day >= start[1]) or \
               (month == end[0] and day <= end[1]):
                return sign
        return 'Capricornio'
