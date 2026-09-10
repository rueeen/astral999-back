from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.views import TokenBlacklistView
from apps.users.views import RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/users/', include('apps.users.urls')),
    path('api/cards/', include('apps.cards.urls')),
    path('api/readings/', include('apps.readings.urls')),
]

if settings.DEBUG:
    # En producción PythonAnywhere sirve MEDIA_ROOT mediante su mapeo estático
    # /media/; Django solo expone estos archivos durante el desarrollo local.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
