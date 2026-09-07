from random import choice, sample

from rest_framework import generics, permissions, status
from rest_framework.exceptions import APIException
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import TarotCard
from .models import Reading
from .serializers import ReadingSerializer, SharedReadingSerializer, SPREAD_CARD_COUNTS
from .quotas import validate_quota
from .services.ai import generate_reading


class ReadingServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'No pudimos generar tu lectura. Inténtalo nuevamente más tarde.'
    default_code = 'ai_unavailable'


class ReadingListCreateView(generics.ListCreateAPIView):
    serializer_class = ReadingSerializer
    permission_classes = (permissions.IsAuthenticated,)
    throttle_scope = 'reading_create'

    def get_throttles(self):
        if self.request.method == 'POST':
            return [ScopedRateThrottle()]
        return []

    def get_queryset(self):
        return Reading.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'GET':
            context['cards_map'] = {card.id: card for card in TarotCard.objects.all()}
        return context

    def perform_create(self, serializer):
        spread = serializer.validated_data['spread']
        question = serializer.validated_data['question']
        validate_quota(self.request.user, spread)
        card_count = SPREAD_CARD_COUNTS[spread]

        cards = sample(list(TarotCard.objects.all()), card_count)
        cards_drawn = [
            {'card_id': card.id, 'position': i + 1,
                'reversed': choice((True, False))}
            for i, card in enumerate(cards)
        ]
        reading = serializer.save(
            user=self.request.user,
            cards_drawn=cards_drawn,
            status=Reading.Status.PENDING,
        )
        drawn_with_cards = [
            {**item, 'card': card}
            for item, card in zip(cards_drawn, cards)
        ]
        try:
            result = generate_reading(
                question=question,
                spread=spread,
                cards=drawn_with_cards,
                mode=reading.mode,
                user=self.request.user,
            )
            if isinstance(result, str):
                text, model, tokens = result, None, None
            else:
                text, model, tokens = result.text, result.model, result.tokens
            if not text.strip():
                raise RuntimeError('Respuesta vacía')
        except Exception as error:
            reading.status = Reading.Status.FAILED
            reading.save(update_fields=('status',))
            raise ReadingServiceUnavailable() from error
        reading.ai_response = text
        reading.model_used = model
        reading.tokens_used = tokens
        reading.status = Reading.Status.READY
        reading.save(update_fields=('ai_response', 'model_used', 'tokens_used', 'status'))


class ReadingDetailView(generics.RetrieveAPIView):
    serializer_class = ReadingSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Reading.objects.filter(user=self.request.user)


class ReadingFavoriteToggleView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, pk):
        try:
            reading = Reading.objects.get(pk=pk, user=request.user)
        except Reading.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        is_favorite = request.data.get('is_favorite')
        if not isinstance(is_favorite, bool):
            return Response(
                {'detail': 'El campo is_favorite debe ser verdadero o falso.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reading.is_favorite = is_favorite
        reading.save(update_fields=['is_favorite'])
        return Response(ReadingSerializer(reading, context={'request': request}).data)


class SharedReadingView(generics.RetrieveAPIView):
    queryset = Reading.objects.filter(status=Reading.Status.READY)
    serializer_class = SharedReadingSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'share_token'
