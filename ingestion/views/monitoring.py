"""
Django views for enterprise monitoring dashboard
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
from asgiref.sync import sync_to_async
from ingestion.models.common import SyncHistory, SyncConfiguration
from ingestion.monitoring.dashboard import MonitoringDashboard
from ingestion.monitoring.alerts import AlertManager
from ingestion.base.performance import PerformanceMonitor

# Mock connection_manager for now
class MockConnectionManager:
    def get_all_stats(self):
        return {"active_connections": 5, "total_connections": 10}

connection_manager = MockConnectionManager()

class DashboardView(View):
    """Main dashboard view"""
    
    def get(self, request):
        """Render dashboard page"""
        return render(request, 'monitoring/dashboard.html')

class DashboardStatsView(View):
    """Dashboard statistics API"""
    
    def get(self, request):
        """Get dashboard statistics"""
        try:
            # Use synchronous queries for now
            now = timezone.now()
            yesterday = now - timedelta(days=1)
            
            # Basic sync stats
            active_syncs = SyncHistory.objects.filter(
                status='running',
                start_time__gte=yesterday
            ).count()
            
            failed_syncs = SyncHistory.objects.filter(
                status='failed',
                start_time__gte=yesterday
            ).count()
            
            total_syncs = SyncHistory.objects.filter(
                start_time__gte=yesterday
            ).count()
            
            success_rate = (total_syncs - failed_syncs) / max(total_syncs, 1)
            
            return JsonResponse({
                'active_syncs': active_syncs,
                'failed_syncs': failed_syncs,
                'total_syncs': total_syncs,
                'success_rate': success_rate,
                'timestamp': now.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class AlertView(View):
    """Alert management view"""
    
    def get(self, request):
        """Get current alerts"""
        try:
            # Simple alert logic for now
            alerts = []
            
            # Check for recent failures
            recent_failures = SyncHistory.objects.filter(
                status='failed',
                start_time__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_failures > 5:
                alerts.append({
                    'type': 'error',
                    'message': f'High failure rate: {recent_failures} failures in last hour'
                })
            
            return JsonResponse({'alerts': alerts})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class PerformanceView(View):
    """Performance monitoring view"""
    
    def get(self, request):
        """Get performance metrics"""
        try:
            # Simple performance metrics
            now = timezone.now()
            yesterday = now - timedelta(days=1)
            
            # Get sync performance data
            sync_data = SyncHistory.objects.filter(
                start_time__gte=yesterday,
                status='success'
            ).aggregate(
                total_records=Sum('records_processed'),
                avg_duration=Avg('duration_seconds')
            )
            
            return JsonResponse({
                'total_records_processed': sync_data['total_records'] or 0,
                'avg_duration_seconds': sync_data['avg_duration'] or 0,
                'timestamp': now.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class ConnectionView(View):
    """Connection monitoring view"""
    
    def get(self, request):
        """Get connection pool data"""
        try:
            connection_stats = connection_manager.get_all_stats()
            # Get health status synchronously for now
            health_status = {'overall_health': 'healthy'}
            return JsonResponse({
                'connection_stats': connection_stats,
                'health_status': health_status
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# API Views for monitoring endpoints
dashboard_view = DashboardView.as_view()
dashboard_stats_view = DashboardStatsView.as_view()
alert_view = AlertView.as_view()
performance_view = PerformanceView.as_view()
connection_view = ConnectionView.as_view()

# Export all views
__all__ = [
    'dashboard_view', 
    'dashboard_stats_view', 
    'alert_view', 
    'performance_view', 
    'connection_view'
]
