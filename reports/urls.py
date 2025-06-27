from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_list, name='report_list'),
    path('<int:report_id>/', views.report_detail, name='report_detail'),

    # Genius Prospects Duplicate Detection
    path('api/run-duplicate-detection/', views.run_duplicate_detection, name='run_duplicate_detection'),
    path('api/check-detection-progress/', views.check_detection_progress, name='check_detection_progress'),
    path('api/cancel-detection/', views.cancel_detection, name='cancel_detection'),
    path('api/export-duplicates-csv/', views.export_duplicates_csv, name='export_duplicates_csv'),
    path('api/load-report-file/<str:filename>/', views.load_report_file, name='load_report_file'),

    # HubSpot Appointments Duplicate Detection
    path('api/run-hubspot-duplicate-detection/', views.run_hubspot_duplicate_detection, name='run_hubspot_duplicate_detection'),
    path('api/check-hubspot-detection-progress/', views.check_hubspot_detection_progress, name='check_hubspot_detection_progress'),
    path('api/cancel-hubspot-detection/', views.cancel_hubspot_detection, name='cancel_hubspot_detection'),
    path('api/export-hubspot-duplicates-csv/', views.export_hubspot_duplicates_csv, name='export_hubspot_duplicates_csv'),
    path('api/load-hubspot-report-file/<str:filename>/', views.load_hubspot_report_file, name='load_hubspot_report_file'),
]
