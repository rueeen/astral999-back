from random import choice, sample

from rest_framework import serializers

from apps.cards.models import TarotCard
from .models import Reading

SPREAD_CARD_COUNTS = {
    'one_card': 1,
    'three_cards': 3,
    'celtic_cross': 10,
}


class ReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reading
        fields = ('id', 'user', 'question', 'spread', 'cards_drawn', 'ai_response', 'created_at', 'is_favorite')
        read_only_fields = ('id', 'user', 'cards_drawn', 'ai_response', 'created_at', 'is_favorite')

    def validate_spread(self, value):
        if value not in SPREAD_CARD_COUNTS:
            raise serializers.ValidationError('Invalid spread.')
        return value

    def validate(self, attrs):
        spread = attrs.get('spread')
        required_cards = SPREAD_CARD_COUNTS.get(spread, 0)
        available_cards = TarotCard.objects.count()
        if available_cards < required_cards:
            raise serializers.ValidationError({'spread': f'Not enough cards to create this spread. Required: {required_cards}.'})
        return attrs

    def create(self, validated_data):
        question = validated_data['question']
        spread = validated_data['spread']
        card_count = SPREAD_CARD_COUNTS[spread]
        cards = sample(list(TarotCard.objects.all()), card_count)
        cards_drawn = [
            {'card_id': card.id, 'position': index + 1, 'reversed': choice((True, False))}
            for index, card in enumerate(cards)
        ]
        ai_response = f'Lectura generada para: {question} [IA pendiente de integrar]'
        return Reading.objects.create(
            user=self.context['request'].user,
            question=question,
            spread=spread,
            cards_drawn=cards_drawn,
            ai_response=ai_response,
        )
