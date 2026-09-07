from django.db import models


class TarotCard(models.Model):
    class Arcana(models.TextChoices):
        MAJOR = 'MAJOR', 'Major'
        MINOR = 'MINOR', 'Minor'

    class Suit(models.TextChoices):
        WANDS = 'wands', 'Bastos'
        CUPS = 'cups', 'Copas'
        SWORDS = 'swords', 'Espadas'
        PENTACLES = 'pentacles', 'Oros'

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    arcana = models.CharField(max_length=5, choices=Arcana.choices)
    suit = models.CharField(max_length=10, choices=Suit.choices, blank=True, null=True)
    number = models.IntegerField()
    meaning_up = models.TextField()
    meaning_rev = models.TextField()
    keywords = models.JSONField(default=list)
    image = models.ImageField(upload_to='cards/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('arcana', 'number', 'name')

    def __str__(self):
        return self.name
