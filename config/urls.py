from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('api/auth/login/', TokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/register/', __import__('apps.users.views',
         fromlist=['RegisterView']).RegisterView.as_view(), name='register'),

    # Users
    path('api/users/', include('apps.users.urls')),

    # Cards
    path('api/cards/', include('apps.cards.urls')),

    # Readings
    path('api/readings/', include('apps.readings.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
