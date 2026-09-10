from rest_framework import serializers
from apps.cards.models import TarotCard
from apps.cards.serializers import TarotCardSerializer
from .models import Reading, ReadingFeedback

SPREAD_CARD_COUNTS = {
    'one_card': 1,
    'three_cards': 3,
    'celtic_cross': 10,
}


class ReadingSerializer(serializers.ModelSerializer):
    cards_detail = serializers.SerializerMethodField()

    class Meta:
        model = Reading
        fields = (
            'id', 'user', 'question', 'spread',
            'cards_drawn', 'cards_detail',
            'ai_response', 'mode', 'status', 'model_used',
            'input_tokens', 'output_tokens', 'cache_read_tokens',
            'cache_creation_tokens', 'cost', 'cost_currency',
            'share_token', 'created_at', 'is_favorite',
            'is_public', 'address_as',
        )
        read_only_fields = (
            'id', 'user', 'cards_drawn', 'cards_detail',
            'ai_response', 'status', 'model_used', 'input_tokens', 'output_tokens',
            'cache_read_tokens', 'cache_creation_tokens', 'cost', 'cost_currency',
            'share_token', 'created_at', 'is_favorite',
            'address_as',
        )

    def validate_spread(self, value):
        if value not in SPREAD_CARD_COUNTS:
            raise serializers.ValidationError('La tirada seleccionada no es válida.')
        return value

    def validate(self, attrs):
        spread = attrs.get('spread')
        required = SPREAD_CARD_COUNTS.get(spread, 0)
        available = TarotCard.objects.count()
        if available < required:
            raise serializers.ValidationError(
                {'spread': f'No hay suficientes cartas. Se requieren {required} y hay {available}.'}
            )
        return attrs

    def get_cards_detail(self, obj):
        card_ids = [item['card_id'] for item in obj.cards_drawn]
        cards_map = self.context.get('cards_map')
        if cards_map is None:
            cards_map = {c.id: c for c in TarotCard.objects.filter(id__in=card_ids)}
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


class SharedReadingSerializer(ReadingSerializer):
    class Meta:
        model = Reading
        fields = (
            'question', 'spread', 'cards_drawn', 'cards_detail',
            'ai_response', 'mode', 'created_at',
        )
        read_only_fields = fields


class ReadingFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingFeedback
        fields = ('id', 'reading', 'user', 'value', 'comment', 'generation_context', 'created_at')
        read_only_fields = ('id', 'reading', 'user', 'generation_context', 'created_at')
