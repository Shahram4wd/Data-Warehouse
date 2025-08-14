from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import GeniusUserSyncView

# Import monitoring views directly to avoid module conflicts
try:
    from ingestion.views.monitoring import (
        DashboardView,
        DashboardStatsView,
        AlertView,
        PerformanceView,
        ConnectionView,
        ConnectionHealthView,
        AutomationStatusView,
        ApproveActionView,
        RejectActionView,
        SecurityStatusView
    )
    monitoring_available = True
except ImportError:
    monitoring_available = False

# Define monitoring URLs directly here
monitoring_urlpatterns = [
    # Dashboard views
    path('', DashboardView.as_view(), name='monitoring_dashboard'),
    path('dashboard/', DashboardView.as_view(), name='monitoring_dashboard_home'),
    
    # API endpoints
    path('api/stats/', DashboardStatsView.as_view(), name='monitoring_api_stats'),
    path('api/alerts/', AlertView.as_view(), name='monitoring_api_alerts'),
    path('api/performance/', PerformanceView.as_view(), name='monitoring_api_performance'),
    path('api/connections/', ConnectionView.as_view(), name='monitoring_api_connections'),
    path('api/connection-health/', ConnectionHealthView.as_view(), name='monitoring_api_connection_health'),
    path('api/automation-status/', AutomationStatusView.as_view(), name='monitoring_api_automation_status'),
    path('api/security-status/', SecurityStatusView.as_view(), name='monitoring_api_security_status'),
    path('api/approve-action/<str:approval_id>/', ApproveActionView.as_view(), name='monitoring_api_approve_action'),
    path('api/reject-action/<str:approval_id>/', RejectActionView.as_view(), name='monitoring_api_reject_action'),
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