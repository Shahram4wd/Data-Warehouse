from django.urls import path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import GeniusUserSyncView

urlpatterns = [
    # API endpoints
    path('api/sync/genius-users/', GeniusUserSyncView.as_view(), name='sync-genius-users'),
    
    # Schema endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Redirect root URL to API docs
    path('', RedirectView.as_view(url='/api/docs/', permanent=False), name='index'),
]