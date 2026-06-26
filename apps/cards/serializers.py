from rest_framework import serializers

from .models import TarotCard


class TarotCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarotCard
        fields = ('id', 'name', 'slug', 'arcana', 'number', 'meaning_up', 'meaning_rev', 'keywords', 'image', 'created_at')
        read_only_fields = ('id', 'created_at')
