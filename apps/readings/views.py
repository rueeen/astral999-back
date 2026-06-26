from random import choice, sample

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import TarotCard
from .models import Reading
from .serializers import ReadingSerializer, SPREAD_CARD_COUNTS


class ReadingListCreateView(generics.ListCreateAPIView):
    serializer_class = ReadingSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Reading.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        spread = serializer.validated_data['spread']
        question = serializer.validated_data['question']
        card_count = SPREAD_CARD_COUNTS[spread]

        cards = sample(list(TarotCard.objects.all()), card_count)
        cards_drawn = [
            {'card_id': card.id, 'position': i + 1,
                'reversed': choice((True, False))}
            for i, card in enumerate(cards)
        ]

        # Stub — reemplazar con llamada real a Anthropic en Fase 2
        ai_response = f'Lectura generada para: {question} [IA pendiente de integrar]'

        serializer.save(
            user=self.request.user,
            cards_drawn=cards_drawn,
            ai_response=ai_response,
        )


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
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        reading.is_favorite = not reading.is_favorite
        reading.save(update_fields=['is_favorite'])
        return Response(ReadingSerializer(reading, context={'request': request}).data)
