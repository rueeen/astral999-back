from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, UserSerializer
from apps.readings.quotas import get_quota


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)


class MeView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(
            request.user, data=request.data, partial=True, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class QuotaView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(get_quota(request.user))
