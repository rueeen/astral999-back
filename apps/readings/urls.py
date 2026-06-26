from django.urls import path

from .views import ReadingDetailView, ReadingFavoriteToggleView, ReadingListCreateView

urlpatterns = [
    path('', ReadingListCreateView.as_view(), name='reading-list-create'),
    path('<int:pk>/', ReadingDetailView.as_view(), name='reading-detail'),
    path('<int:pk>/favorite/', ReadingFavoriteToggleView.as_view(), name='reading-favorite'),
]
