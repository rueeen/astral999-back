import logging
from random import choice, sample

from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404
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
from .services.share_image import get_or_render

logger = logging.getLogger(__name__)


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
        queryset = Reading.objects.filter(user=self.request.user)
        if self.request.method == 'GET' and self.request.query_params.get('include_failed') != 'true':
            queryset = queryset.exclude(status=Reading.Status.FAILED)
        return queryset

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
            address_as=self.request.user.address_as,
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
            text, model, tokens = result.text, result.model, result.tokens
            if not text.strip():
                raise RuntimeError('Respuesta vacía')
        except ImproperlyConfigured:
            reading.status = Reading.Status.FAILED
            reading.save(update_fields=('status',))
            raise
        except Exception as error:
            logger.exception('Falló la generación de la lectura %s.', reading.pk)
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

    def patch(self, request, *args, **kwargs):
        reading = self.get_object()
        is_public = request.data.get('is_public')
        if not isinstance(is_public, bool):
            return Response(
                {'detail': 'El campo is_public debe ser verdadero o falso.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reading.is_public = is_public
        reading.save(update_fields=('is_public',))
        return Response(self.get_serializer(reading).data)


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
    queryset = Reading.objects.filter(status=Reading.Status.READY, is_public=True)
    serializer_class = SharedReadingSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'share_token'


class SharedReadingImageView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, share_token):
        try:
            reading = Reading.objects.get(
                share_token=share_token, status=Reading.Status.READY, is_public=True,
            )
        except Reading.DoesNotExist as error:
            raise Http404 from error
        fmt = request.query_params.get('format', 'og')
        include_question = request.query_params.get('question', 'true').lower() == 'true'
        try:
            image_path = get_or_render(reading, fmt=fmt, include_question=include_question)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        response = FileResponse(open(image_path, 'rb'), content_type='image/png')
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
