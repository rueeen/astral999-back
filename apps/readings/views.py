from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Reading
from .serializers import ReadingSerializer


class ReadingListCreateView(generics.ListCreateAPIView):
    serializer_class = ReadingSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Reading.objects.filter(user=self.request.user)


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
