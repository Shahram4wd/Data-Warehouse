from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import GeniusUserSyncView

urlpatterns = [
    # API endpoints
    path('api/sync/genius-users/', GeniusUserSyncView.as_view(), name='sync-genius-users'),

    # Authentication endpoints
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    # Schema endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Redirect root URL to API docs
    path('', RedirectView.as_view(url='/api/docs/', permanent=False), name='index'),
]