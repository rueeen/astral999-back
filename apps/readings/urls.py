from django.urls import path

from .views import (
    ReadingDetailView,
    ReadingFavoriteToggleView,
    ReadingFeedbackSummaryView,
    ReadingFeedbackView,
    ReadingListCreateView,
    SharedReadingView,
    SharedReadingImageView,
)

urlpatterns = [
    path('', ReadingListCreateView.as_view(), name='reading-list-create'),
    path('shared/<uuid:share_token>/', SharedReadingView.as_view(), name='reading-shared'),
    path('shared/<uuid:share_token>/image/', SharedReadingImageView.as_view(), name='reading-shared-image'),
    path('<int:pk>/', ReadingDetailView.as_view(), name='reading-detail'),
    path('<int:pk>/favorite/', ReadingFavoriteToggleView.as_view(), name='reading-favorite'),
    path('<int:pk>/feedback/', ReadingFeedbackView.as_view(), name='reading-feedback'),
    path(
        '<int:pk>/feedback/summary/', ReadingFeedbackSummaryView.as_view(),
        name='reading-feedback-summary',
    ),
]
