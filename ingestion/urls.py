from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import GeniusUserSyncView

# Import CRM dashboard views
try:
    from ingestion.views.crm_dashboard.views import (
        CRMDashboardView,
        CRMModelsView,
        ModelDetailView,
        SyncHistoryView
    )
    from ingestion.views.crm_dashboard.api_views import (
        CRMListAPIView,
        CRMModelsAPIView,
        ModelDetailAPIView,
        ModelDataAPIView,
        SyncExecuteAPIView,
        SyncStatusAPIView,
        SyncStopAPIView,
        RunningSyncsAPIView,
        SyncHistoryAPIView,
        AvailableCommandsAPIView,
        ValidateParametersAPIView
    )
    crm_dashboard_available = True
except ImportError:
    crm_dashboard_available = False

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

# Define CRM dashboard URLs
crm_dashboard_urlpatterns = [
    # API endpoints (must come first to avoid conflicts with dynamic patterns)
    path('api/crms/', CRMListAPIView.as_view(), name='api_crm_list'),
    path('api/crms/<str:crm_source>/models/', CRMModelsAPIView.as_view(), name='api_crm_models'),
    path('api/crms/<str:crm_source>/models/<str:model_name>/', ModelDetailAPIView.as_view(), name='api_model_detail'),
    path('api/crms/<str:crm_source>/models/<str:model_name>/data/', ModelDataAPIView.as_view(), name='api_model_data'),
    path('api/crms/<str:crm_source>/commands/', AvailableCommandsAPIView.as_view(), name='api_available_commands'),
    path('api/sync/execute/', SyncExecuteAPIView.as_view(), name='api_sync_execute'),
    path('api/sync/<int:sync_id>/status/', SyncStatusAPIView.as_view(), name='api_sync_status'),
    path('api/sync/<int:sync_id>/stop/', SyncStopAPIView.as_view(), name='api_sync_stop'),
    path('api/sync/running/', RunningSyncsAPIView.as_view(), name='api_running_syncs'),
    path('api/sync/history/', SyncHistoryAPIView.as_view(), name='api_sync_history'),
    path('api/sync/validate/', ValidateParametersAPIView.as_view(), name='api_validate_parameters'),
    
    # Dashboard pages (dynamic patterns at the end)
    path('', CRMDashboardView.as_view(), name='crm_dashboard'),
    path('history/', SyncHistoryView.as_view(), name='sync_history'),
    path('<str:crm_source>/', CRMModelsView.as_view(), name='crm_models'),
    path('<str:crm_source>/<str:model_name>/', ModelDetailView.as_view(), name='model_detail'),
]

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

    # CRM Dashboard endpoints
    path('crm-dashboard/', include((crm_dashboard_urlpatterns, 'crm_dashboard'), namespace='crm_dashboard')),

    # Redirect root URL to monitoring dashboard
    path('', RedirectView.as_view(url='/monitoring/', permanent=False), name='index'),

    # Added URL patterns for the reports module
    path('reports/', include('reports.urls')),
]