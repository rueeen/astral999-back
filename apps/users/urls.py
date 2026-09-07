from django.urls import path
from .views import MeView, QuotaView

urlpatterns = [
    path('me/', MeView.as_view(), name='user-me'),
    path('me/quota/', QuotaView.as_view(), name='user-quota'),
]
