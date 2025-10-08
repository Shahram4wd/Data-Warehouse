from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import GeniusUserSyncView
from django.http import HttpResponse

# Debug view for testing dashboard
def debug_dashboard(request):
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Test</title>
    <style>
        .debug { background: #f0f0f0; padding: 10px; margin: 10px; }
    </style>
</head>
<body>
    <h1>Dashboard Debug Test</h1>
    <div id="debug-output" class="debug">Loading...</div>
    <div id="crm-cards-container" class="debug">CRM cards will appear here...</div>

    <script src="/static/crm_dashboard/js/dashboard.js"></script>
    
    <script>
        const debugOutput = document.getElementById('debug-output');
        
        function log(message) {
            debugOutput.innerHTML += '<br>' + message;
            console.log(message);
        }
        
        log('🚀 Starting debug test...');
        
        // Test if the class exists
        if (typeof EnhancedDashboardManager !== 'undefined') {
            log('✅ EnhancedDashboardManager class is available');
            
            try {
                const manager = new EnhancedDashboardManager();
                log('✅ Dashboard manager created successfully');
                log('Manager methods: ' + Object.getOwnPropertyNames(Object.getPrototypeOf(manager)).join(', '));
                
                // Test if we can call fetchCRMsData
                log('🔍 Testing fetchCRMsData...');
                manager.fetchCRMsData().then(data => {
                    log('✅ CRM data fetched: ' + JSON.stringify(data).substring(0, 200) + '...');
                }).catch(err => {
                    log('❌ Error fetching CRM data: ' + err.message);
                });
                
            } catch (error) {
                log('❌ Error creating dashboard manager: ' + error.message);
                log('Stack: ' + error.stack);
            }
        } else {
            log('❌ EnhancedDashboardManager class is not available');
        }
    </script>
</body>
</html>"""
    return HttpResponse(html)

# Register app namespace for namespaced URL reversing
app_name = 'ingestion'

# Import CRM dashboard views
try:
    from ingestion.views.crm_dashboard.views import (
        CRMDashboardView,
        CRMModelsView,
        ModelDetailView,
        SyncHistoryView,
        AllSchedulesView
    )
    from ingestion.views.crm_dashboard.api_views import (
        CRMListAPIView,
        CRMModelsAPIView,
        CRMRecordCountAPIView,
        ModelDetailAPIView,
        ModelDataAPIView,
        SyncExecuteAPIView,
        SyncStatusAPIView,
        SyncStopAPIView,
    SyncStopAllAPIView,
        RunningSyncsAPIView,
        SyncHistoryAPIView,
        SyncHistoryDetailAPIView,
        AvailableCommandsAPIView,
        ValidateParametersAPIView,
        SyncSchemasAPIView,
        ModelScheduleAPIView,
        ScheduleDetailAPIView,
        AllSchedulesAPIView
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

# Import worker pool API views
try:
    from ingestion.views.worker_pool_api import (
        WorkerPoolStatusView,
        SubmitSyncTaskView,
        TaskStatusView,
        CancelTaskView,
        CancelAllTasksView,
        ResetWorkerPoolView,
        WorkerPoolConfigView,
        ProcessQueueView,
        get_worker_pool_stats,
        submit_sync_task
    )
    worker_pool_api_available = True
except ImportError:
    worker_pool_api_available = False

"""CRM Dashboard URLs (defined here to avoid separate module).
If the CRM views fail to import, expose an empty list to keep URLConf stable.
"""
crm_dashboard_urlpatterns = [
    # API endpoints (must come first to avoid conflicts with dynamic patterns)
    path('api/crms/', CRMListAPIView.as_view(), name='api_crm_list'),
    path('api/crms/<str:crm_source>/models/', CRMModelsAPIView.as_view(), name='api_crm_models'),
    path('api/crms/<str:crm_source>/record-count/', CRMRecordCountAPIView.as_view(), name='api_crm_record_count'),
    path('api/crms/<str:crm_source>/models/<str:model_name>/', ModelDetailAPIView.as_view(), name='api_model_detail'),
    path('api/crms/<str:crm_source>/models/<str:model_name>/data/', ModelDataAPIView.as_view(), name='api_model_data'),
    path('api/crms/<str:crm_source>/commands/', AvailableCommandsAPIView.as_view(), name='api_available_commands'),
    path('api/sync/execute/', SyncExecuteAPIView.as_view(), name='api_sync_execute'),
    path('api/sync/<int:sync_id>/status/', SyncStatusAPIView.as_view(), name='api_sync_status'),
    path('api/sync/<int:sync_id>/stop/', SyncStopAPIView.as_view(), name='api_sync_stop'),
    path('api/sync/stop-all/', SyncStopAllAPIView.as_view(), name='api_sync_stop_all'),
    path('api/sync/running/', RunningSyncsAPIView.as_view(), name='api_running_syncs'),
    path('api/sync/history/', SyncHistoryAPIView.as_view(), name='api_sync_history'),
    path('api/sync/history/<int:sync_id>/', SyncHistoryDetailAPIView.as_view(), name='api_sync_history_detail'),
    path('api/sync/validate/', ValidateParametersAPIView.as_view(), name='api_validate_parameters'),
    path('api/sync/schemas/', SyncSchemasAPIView.as_view(), name='api_sync_schemas'),
    
    # Worker Pool API endpoints
    path('api/worker-pool/status/', WorkerPoolStatusView.as_view(), name='api_worker_pool_status'),
    path('api/worker-pool/submit/', SubmitSyncTaskView.as_view(), name='api_worker_pool_submit'),
    path('api/worker-pool/tasks/<str:task_id>/', TaskStatusView.as_view(), name='api_worker_pool_task_status'),
    path('api/worker-pool/tasks/<str:task_id>/cancel/', CancelTaskView.as_view(), name='api_worker_pool_cancel_task'),
    path('api/worker-pool/cancel-all/', CancelAllTasksView.as_view(), name='api_worker_pool_cancel_all'),
    path('api/worker-pool/reset/', ResetWorkerPoolView.as_view(), name='api_worker_pool_reset'),
    path('api/worker-pool/config/', WorkerPoolConfigView.as_view(), name='api_worker_pool_config'),
    path('api/worker-pool/process-queue/', ProcessQueueView.as_view(), name='api_worker_pool_process_queue'),
    
    # Worker Pool compatibility endpoints
    path('api/worker-pool/stats/', get_worker_pool_stats, name='api_worker_pool_stats_compat'),
    path('api/worker-pool/sync/submit/', submit_sync_task, name='api_worker_pool_sync_submit_compat'),

    # Schedule management API endpoints
    path('api/schedules/', AllSchedulesAPIView.as_view(), name='api_all_schedules'),
    path('api/schedules/<int:schedule_id>/', ScheduleDetailAPIView.as_view(), name='api_schedule_detail'),
    path('api/crms/<str:crm_source>/models/<str:model_name>/schedules/', ModelScheduleAPIView.as_view(), name='api_model_schedules'),

    # Dashboard pages (dynamic patterns at the end)
    path('', CRMDashboardView.as_view(), name='crm_dashboard'),
    path('history/', SyncHistoryView.as_view(), name='sync_history'),
    path('schedules/', AllSchedulesView.as_view(), name='all_schedules'),
    path('<str:crm_source>/', CRMModelsView.as_view(), name='crm_models'),
    path('<str:crm_source>/<str:model_name>/', ModelDetailView.as_view(), name='model_detail'),
] if crm_dashboard_available else []

"""Monitoring URLs (defined here to avoid separate module).
If the monitoring views fail to import, expose an empty list to keep URLConf stable.
"""
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

    # CRM Dashboard endpoints (local patterns; no external urls module)
    path('crm-dashboard/', include((crm_dashboard_urlpatterns, 'crm_dashboard'), namespace='crm_dashboard')),

    # Scheduling endpoints (server-rendered)
    # These power the schedule list/create/edit/toggle/delete/run-now UI
    path('schedules/<str:source_key>/',
        __import__('ingestion.views.schedules', fromlist=['list_schedules']).list_schedules,
        name='schedules'),
    path('schedules/<str:source_key>/new/',
        __import__('ingestion.views.schedules', fromlist=['create_schedule']).create_schedule,
        name='schedule_new'),
    path('schedules/<str:source_key>/<int:pk>/edit/',
        __import__('ingestion.views.schedules', fromlist=['edit_schedule']).edit_schedule,
        name='schedule_edit'),
    path('schedules/<str:source_key>/<int:pk>/delete/',
        __import__('ingestion.views.schedules', fromlist=['delete_schedule']).delete_schedule,
        name='schedule_delete'),
    path('schedules/<str:source_key>/<int:pk>/toggle/',
        __import__('ingestion.views.schedules', fromlist=['toggle_schedule']).toggle_schedule,
        name='schedule_toggle'),
    path('schedules/<str:source_key>/<int:pk>/run/',
        __import__('ingestion.views.schedules', fromlist=['run_now']).run_now,
        name='schedule_run'),

    # Redirect root URL to monitoring dashboard
    path('', RedirectView.as_view(url='/monitoring/', permanent=False), name='index'),

    # Added URL patterns for the reports module
    path('reports/', include('reports.urls')),
    
    # Debug dashboard test
    path('debug-dashboard/', debug_dashboard, name='debug_dashboard'),
]