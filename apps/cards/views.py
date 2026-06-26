from rest_framework import generics, permissions

from .models import TarotCard
from .serializers import TarotCardSerializer


class TarotCardListView(generics.ListAPIView):
    queryset = TarotCard.objects.all()
    serializer_class = TarotCardSerializer
    permission_classes = (permissions.AllowAny,)


class TarotCardDetailView(generics.RetrieveAPIView):
    queryset = TarotCard.objects.all()
    serializer_class = TarotCardSerializer
    lookup_field = 'slug'
    permission_classes = (permissions.AllowAny,)
