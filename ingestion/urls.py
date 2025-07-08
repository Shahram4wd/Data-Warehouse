from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import GeniusUserSyncView

# Import monitoring views directly to avoid module conflicts
try:
    from ingestion.views.monitoring import (
        MonitoringDashboardView,
        MonitoringAPIView,
        SyncConfigurationView,
        SyncControlView,
        HealthCheckView
    )
    monitoring_available = True
except ImportError:
    monitoring_available = False

# Define monitoring URLs directly here
monitoring_urlpatterns = [
    # Dashboard views
    path('', MonitoringDashboardView.as_view(), name='monitoring_dashboard'),
    path('dashboard/', MonitoringDashboardView.as_view(), name='monitoring_dashboard_home'),
    
    # API endpoints
    path('api/data/', MonitoringAPIView.as_view(), name='monitoring_api_data'),
    path('api/config/', SyncConfigurationView.as_view(), name='monitoring_api_config'),
    path('api/control/', SyncControlView.as_view(), name='monitoring_api_control'),
    path('api/health/', HealthCheckView.as_view(), name='monitoring_api_health'),
] if monitoring_available else []

urlpatterns = [
    # API endpoints
    path('api/sync/genius-users/', GeniusUserSyncView.as_view(), name='sync-genius-users'),

    # Authentication endpoints
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    # Schema endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Monitoring endpoints (included directly)
    path('monitoring/', include((monitoring_urlpatterns, 'monitoring'), namespace='monitoring')),

    # Redirect root URL to monitoring dashboard
    path('', RedirectView.as_view(url='/monitoring/', permanent=False), name='index'),

    # Added URL patterns for the reports module
    path('reports/', include('reports.urls')),
]