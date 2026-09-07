from django.urls import path

from .views import (
    ReadingDetailView,
    ReadingFavoriteToggleView,
    ReadingListCreateView,
    SharedReadingView,
)

urlpatterns = [
    path('', ReadingListCreateView.as_view(), name='reading-list-create'),
    path('shared/<uuid:share_token>/', SharedReadingView.as_view(), name='reading-shared'),
    path('<int:pk>/', ReadingDetailView.as_view(), name='reading-detail'),
    path('<int:pk>/favorite/', ReadingFavoriteToggleView.as_view(), name='reading-favorite'),
]
