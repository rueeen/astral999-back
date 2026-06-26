from rest_framework import serializers
from apps.cards.models import TarotCard
from apps.cards.serializers import TarotCardSerializer
from .models import Reading

SPREAD_CARD_COUNTS = {
    'one_card': 1,
    'three_cards': 3,
    'celtic_cross': 10,
}


class DrawnCardSerializer(serializers.Serializer):
    card = TarotCardSerializer()
    position = serializers.IntegerField()
    reversed = serializers.BooleanField()


class ReadingSerializer(serializers.ModelSerializer):
    cards_detail = serializers.SerializerMethodField()

    class Meta:
        model = Reading
        fields = (
            'id', 'user', 'question', 'spread',
            'cards_drawn', 'cards_detail',
            'ai_response', 'created_at', 'is_favorite',
        )
        read_only_fields = (
            'id', 'user', 'cards_drawn', 'cards_detail',
            'ai_response', 'created_at', 'is_favorite',
        )

    def validate_spread(self, value):
        if value not in SPREAD_CARD_COUNTS:
            raise serializers.ValidationError('Invalid spread.')
        return value

    def validate(self, attrs):
        spread = attrs.get('spread')
        required = SPREAD_CARD_COUNTS.get(spread, 0)
        available = TarotCard.objects.count()
        if available < required:
            raise serializers.ValidationError(
                {'spread': f'Not enough cards. Required: {required}, available: {available}.'}
            )
        return attrs

    def get_cards_detail(self, obj):
        card_ids = [item['card_id'] for item in obj.cards_drawn]
        cards_map = {
            c.id: c for c in TarotCard.objects.filter(id__in=card_ids)}
        result = []
        for item in obj.cards_drawn:
            card = cards_map.get(item['card_id'])
            if card:
                result.append({
                    'card': TarotCardSerializer(card, context=self.context).data,
                    'position': item['position'],
                    'reversed': item['reversed'],
                })
        return result
