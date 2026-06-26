from django.urls import path

from .views import TarotCardDetailView, TarotCardListView

urlpatterns = [
    path('', TarotCardListView.as_view(), name='card-list'),
    path('<slug:slug>/', TarotCardDetailView.as_view(), name='card-detail'),
]
