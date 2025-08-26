"""
URL Configuration for CRM Test Dashboard

Defines all URLs for the web-based test interface.
"""

from django.urls import path
from . import views

app_name = 'testing'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_home, name='dashboard'),
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    
    # Test management
    path('tests/', views.test_list, name='test_list'),
    path('tests/<str:test_name>/', views.test_detail, name='test_detail'),
    
    # Test execution
    path('run/', views.run_test_form, name='run_test'),
    path('run/ajax/', views.run_test_ajax, name='run_test_ajax'),
    
    # Results
    path('results/', views.test_results, name='results'),
    path('results/export/', views.export_results, name='export_results'),
]
