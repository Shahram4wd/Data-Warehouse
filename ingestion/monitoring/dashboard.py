"""
Enterprise Monitoring Dashboard for CRM Integrations
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
from django.db import models
from django.utils import timezone
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from asgiref.sync import sync_to_async
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ingestion.models.common import SyncHistory
from ingestion.base.performance import PerformanceMonitor, PerformanceMetrics

logger = logging.getLogger(__name__)

@dataclass
class DashboardMetrics:
    """Dashboard metrics structure"""
    
    # Current status
    active_syncs: int = 0
    queued_syncs: int = 0
    failed_syncs_24h: int = 0
    success_rate_24h: float = 0.0
    
    # Performance metrics
    avg_processing_speed: float = 0.0
    total_records_processed: int = 0
    avg_memory_usage: float = 0.0
    avg_cpu_usage: float = 0.0
    
    # Quality metrics
    data_quality_score: float = 0.0
    validation_error_rate: float = 0.0
    
    # Resource metrics
    database_connections: int = 0
    cache_hit_rate: float = 0.0
    api_rate_limit_usage: float = 0.0
    
    # Error metrics
    top_errors: List[Dict] = None
    error_trends: List[Dict] = None
    
    def __post_init__(self):
        if self.top_errors is None:
            self.top_errors = []
        if self.error_trends is None:
            self.error_trends = []

class MonitoringDashboard:
    """Enterprise monitoring dashboard"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.metrics_cache = {}
        self.alert_thresholds = self.load_alert_thresholds()
    
    # Sync-to-async wrappers for Django ORM queries
    @sync_to_async
    def get_active_syncs_count(self, start_time: datetime) -> int:
        """Get count of active syncs"""
        return SyncHistory.objects.filter(
            status='running',
            start_time__gte=start_time
        ).count()
    
    @sync_to_async
    def get_failed_syncs_count(self, start_time: datetime, end_time: datetime) -> int:
        """Get count of failed syncs"""
        return SyncHistory.objects.filter(
            status='failed',
            start_time__gte=start_time,
            start_time__lt=end_time
        ).count()
    
    @sync_to_async
    def get_total_syncs_count(self, start_time: datetime, end_time: datetime) -> int:
        """Get total syncs count"""
        return SyncHistory.objects.filter(
            start_time__gte=start_time,
            start_time__lt=end_time
        ).count()
    
    @sync_to_async
    def get_performance_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get performance data from sync histories"""
        return list(SyncHistory.objects.filter(
            start_time__gte=start_time,
            start_time__lt=end_time,
            status__in=['success', 'partial']
        ).values('performance_metrics', 'records_processed'))
    
    @sync_to_async
    def get_quality_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get quality data from sync histories"""
        return list(SyncHistory.objects.filter(
            start_time__gte=start_time,
            start_time__lt=end_time
        ).values('performance_metrics', 'records_processed', 'records_failed'))
    
    @sync_to_async
    def get_error_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get error data from sync histories"""
        return list(SyncHistory.objects.filter(
            start_time__gte=start_time,
            start_time__lt=end_time,
            status='failed'
        ).values('error_message', 'start_time'))
    
    async def get_dashboard_metrics(self) -> DashboardMetrics:
        """Get comprehensive dashboard metrics"""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Get sync metrics
        sync_metrics = await self.get_sync_metrics(yesterday, now)
        
        # Get performance metrics
        performance_metrics = await self.get_performance_metrics(yesterday, now)
        
        # Get quality metrics
        quality_metrics = await self.get_quality_metrics(yesterday, now)
        
        # Get error metrics
        error_metrics = await self.get_error_metrics(yesterday, now)
        
        # Combine all metrics
        dashboard_metrics = DashboardMetrics(
            **sync_metrics,
            **performance_metrics,
            **quality_metrics,
            **error_metrics
        )
        
        return dashboard_metrics
    
    async def get_sync_metrics(self, start_time: datetime, end_time: datetime) -> Dict:
        """Get sync-related metrics"""
        # Use sync-to-async wrappers
        active_syncs = await self.get_active_syncs_count(start_time)
        failed_syncs = await self.get_failed_syncs_count(start_time, end_time)
        total_syncs = await self.get_total_syncs_count(start_time, end_time)
        
        # Success rate
        success_rate = (total_syncs - failed_syncs) / max(total_syncs, 1)
        
        return {
            'active_syncs': active_syncs,
            'failed_syncs_24h': failed_syncs,
            'success_rate_24h': success_rate
        }
    
    async def get_performance_metrics(self, start_time: datetime, end_time: datetime) -> Dict:
        """Get performance metrics"""
        # Get performance data using sync-to-async wrapper
        sync_histories = await self.get_performance_data(start_time, end_time)
        
        total_records = 0
        total_duration = 0
        memory_usage_samples = []
        cpu_usage_samples = []
        
        # sync_histories is already a list from the sync_to_async wrapper
        for history in sync_histories:
            metrics = history.get('performance_metrics', {})
            records = history.get('records_processed', 0)
            
            total_records += records
            
            if 'duration_seconds' in metrics:
                total_duration += metrics['duration_seconds']
            
            if 'memory_usage_mb' in metrics:
                memory_usage_samples.append(metrics['memory_usage_mb'])
            
            if 'cpu_percent' in metrics:
                cpu_usage_samples.append(metrics['cpu_percent'])
        
        # Calculate averages
        avg_processing_speed = total_records / max(total_duration, 1)
        avg_memory_usage = sum(memory_usage_samples) / max(len(memory_usage_samples), 1)
        avg_cpu_usage = sum(cpu_usage_samples) / max(len(cpu_usage_samples), 1)
        
        return {
            'avg_processing_speed': avg_processing_speed,
            'total_records_processed': total_records,
            'avg_memory_usage': avg_memory_usage,
            'avg_cpu_usage': avg_cpu_usage
        }
    
    async def get_quality_metrics(self, start_time: datetime, end_time: datetime) -> Dict:
        """Get data quality metrics"""
        # Get quality data using sync-to-async wrapper
        sync_histories = await self.get_quality_data(start_time, end_time)
        
        total_records = 0
        total_validation_errors = 0
        quality_scores = []
        
        # sync_histories is already a list from the sync_to_async wrapper
        for history in sync_histories:
            metrics = history.get('performance_metrics', {})
            records = history.get('records_processed', 0)
            failed = history.get('records_failed', 0)
            
            total_records += records
            
            # Count validation errors
            if 'validation_errors' in metrics:
                total_validation_errors += metrics['validation_errors']
            
            # Calculate quality score for this sync
            if records > 0:
                quality_score = (records - failed) / records
                quality_scores.append(quality_score)
        
        # Calculate overall metrics
        validation_error_rate = total_validation_errors / max(total_records, 1)
        data_quality_score = sum(quality_scores) / max(len(quality_scores), 1)
        
        return {
            'data_quality_score': data_quality_score,
            'validation_error_rate': validation_error_rate
        }
    
    async def get_error_metrics(self, start_time: datetime, end_time: datetime) -> Dict:
        """Get error metrics and trends"""
        # Get error data using sync-to-async wrapper
        sync_histories = await self.get_error_data(start_time, end_time)
        
        error_counts = defaultdict(int)
        error_trends = defaultdict(list)
        
        # sync_histories is already a list from the sync_to_async wrapper
        for history in sync_histories:
            error_msg = history.get('error_message', 'Unknown error')
            error_time = history.get('start_time')
            
            # Categorize error
            error_category = self.categorize_error(error_msg)
            error_counts[error_category] += 1
            
            # Track error trends by hour
            hour = error_time.replace(minute=0, second=0, microsecond=0)
            error_trends[hour].append(error_category)
        
        # Convert to lists for JSON serialization
        top_errors = [
            {'category': category, 'count': count}
            for category, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        trend_data = [
            {'hour': hour.isoformat(), 'errors': len(errors)}
            for hour, errors in sorted(error_trends.items())
        ]
        
        return {
            'top_errors': top_errors,
            'error_trends': trend_data
        }
    
    def categorize_error(self, error_message: str) -> str:
        """Categorize error message"""
        error_msg = error_message.lower()
        
        if 'rate limit' in error_msg or 'too many requests' in error_msg:
            return 'Rate Limit'
        elif 'timeout' in error_msg or 'connection' in error_msg:
            return 'Connection'
        elif 'validation' in error_msg or 'invalid' in error_msg:
            return 'Validation'
        elif 'authentication' in error_msg or 'unauthorized' in error_msg:
            return 'Authentication'
        elif 'not found' in error_msg or '404' in error_msg:
            return 'Not Found'
        elif 'memory' in error_msg or 'out of memory' in error_msg:
            return 'Memory'
        else:
            return 'Other'
    
    def load_alert_thresholds(self) -> Dict:
        """Load alert thresholds from configuration"""
        return {
            'success_rate_min': 0.95,
            'memory_usage_max': 500,  # MB
            'cpu_usage_max': 80,      # %
            'processing_speed_min': 100,  # records/minute
            'error_rate_max': 0.05,
            'response_time_max': 300  # seconds
        }
    
    async def check_alerts(self, metrics: DashboardMetrics) -> List[Dict]:
        """Check metrics against alert thresholds"""
        alerts = []
        
        if metrics.success_rate_24h < self.alert_thresholds['success_rate_min']:
            alerts.append({
                'type': 'error',
                'message': f'Success rate below threshold: {metrics.success_rate_24h:.1%}',
                'threshold': f"{self.alert_thresholds['success_rate_min']:.1%}"
            })
        
        if metrics.avg_memory_usage > self.alert_thresholds['memory_usage_max']:
            alerts.append({
                'type': 'warning',
                'message': f'High memory usage: {metrics.avg_memory_usage:.1f}MB',
                'threshold': f"{self.alert_thresholds['memory_usage_max']}MB"
            })
        
        if metrics.avg_cpu_usage > self.alert_thresholds['cpu_usage_max']:
            alerts.append({
                'type': 'warning',
                'message': f'High CPU usage: {metrics.avg_cpu_usage:.1f}%',
                'threshold': f"{self.alert_thresholds['cpu_usage_max']}%"
            })
        
        if metrics.validation_error_rate > self.alert_thresholds['error_rate_max']:
            alerts.append({
                'type': 'error',
                'message': f'High validation error rate: {metrics.validation_error_rate:.1%}',
                'threshold': f"{self.alert_thresholds['error_rate_max']:.1%}"
            })
        
        return alerts

# Fixed: Make DashboardView synchronous for WSGI compatibility
class DashboardView(LoginRequiredMixin, TemplateView):
    """Django view for monitoring dashboard"""
    
    template_name = 'monitoring/dashboard.html'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dashboard = MonitoringDashboard()
    
    def get_context_data(self, **kwargs):
        """Get dashboard context data (synchronous version)"""
        context = super().get_context_data(**kwargs)
        
        # Use sync version for WSGI compatibility
        metrics = self.get_dashboard_metrics_sync()
        alerts = self.check_alerts_sync(metrics)
        
        context.update({
            'metrics': asdict(metrics),
            'alerts': alerts,
            'last_updated': timezone.now().isoformat()
        })
        
        return context
    
    def get_dashboard_metrics_sync(self) -> DashboardMetrics:
        """Synchronous version of get_dashboard_metrics"""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Get sync metrics synchronously
        active_syncs = SyncHistory.objects.filter(
            status='running',
            start_time__gte=yesterday
        ).count()
        
        failed_syncs = SyncHistory.objects.filter(
            status='failed',
            start_time__gte=yesterday,
            start_time__lt=now
        ).count()
        
        total_syncs = SyncHistory.objects.filter(
            start_time__gte=yesterday,
            start_time__lt=now
        ).count()
        
        success_rate = (total_syncs - failed_syncs) / max(total_syncs, 1)
        
        return DashboardMetrics(
            active_syncs=active_syncs,
            failed_syncs_24h=failed_syncs,
            success_rate_24h=success_rate
        )
    
    def check_alerts_sync(self, metrics: DashboardMetrics) -> List[Dict]:
        """Synchronous version of check_alerts"""
        alerts = []
        
        if metrics.success_rate_24h < 0.95:
            alerts.append({
                'type': 'error',
                'message': f'Success rate below threshold: {metrics.success_rate_24h:.1%}',
                'threshold': '95.0%'
            })
        
        return alerts

# Fixed: Properly inherit from DRF APIView
class DashboardAPIView(APIView):
    """API view for dashboard metrics"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dashboard = MonitoringDashboard()
    
    def get(self, request):
        """Get dashboard metrics as JSON (synchronous version)"""
        try:
            # Use synchronous version for WSGI compatibility
            metrics = self.get_dashboard_metrics_sync()
            alerts = self.check_alerts_sync(metrics)
            
            return Response({
                'success': True,
                'data': {
                    'metrics': asdict(metrics),
                    'alerts': alerts,
                    'timestamp': timezone.now().isoformat()
                }
            })
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_dashboard_metrics_sync(self) -> DashboardMetrics:
        """Synchronous version of get_dashboard_metrics"""
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Get sync metrics synchronously
        active_syncs = SyncHistory.objects.filter(
            status='running',
            start_time__gte=yesterday
        ).count()
        
        failed_syncs = SyncHistory.objects.filter(
            status='failed',
            start_time__gte=yesterday,
            start_time__lt=now
        ).count()
        
        total_syncs = SyncHistory.objects.filter(
            start_time__gte=yesterday,
            start_time__lt=now
        ).count()
        
        success_rate = (total_syncs - failed_syncs) / max(total_syncs, 1)
        
        return DashboardMetrics(
            active_syncs=active_syncs,
            failed_syncs_24h=failed_syncs,
            success_rate_24h=success_rate
        )
    
    def check_alerts_sync(self, metrics: DashboardMetrics) -> List[Dict]:
        """Synchronous version of check_alerts"""
        alerts = []
        
        if metrics.success_rate_24h < 0.95:
            alerts.append({
                'type': 'error',
                'message': f'Success rate below threshold: {metrics.success_rate_24h:.1%}',
                'threshold': '95.0%'
            })
        
        return alerts

# Fixed: Improved WebSocket management with proper error handling
class DashboardWebSocket:
    """WebSocket handler for real-time dashboard updates"""
    
    def __init__(self):
        self.dashboard = MonitoringDashboard()
        self.connected_clients = set()
        self.update_interval = 30  # seconds
        self.is_running = False
    
    async def connect(self, websocket, path):
        """Handle WebSocket connection"""
        self.connected_clients.add(websocket)
        logger.info(f"Dashboard client connected: {websocket.remote_address}")
        
        try:
            await websocket.wait_closed()
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            self.connected_clients.discard(websocket)
            logger.info(f"Dashboard client disconnected: {websocket.remote_address}")
    
    async def broadcast_updates(self):
        """Broadcast real-time updates to connected clients"""
        if not self.connected_clients:
            return
        
        try:
            metrics = await self.dashboard.get_dashboard_metrics()
            alerts = await self.dashboard.check_alerts(metrics)
            
            message = json.dumps({
                'type': 'metrics_update',
                'data': {
                    'metrics': asdict(metrics),
                    'alerts': alerts,
                    'timestamp': timezone.now().isoformat()
                }
            })
            
            # Send to all connected clients
            disconnected = set()
            for client in self.connected_clients:
                try:
                    await client.send(message)
                except Exception as e:
                    logger.debug(f"Failed to send to client: {e}")
                    disconnected.add(client)
            
            # Remove disconnected clients
            self.connected_clients -= disconnected
            
        except Exception as e:
            logger.error(f"Error broadcasting dashboard updates: {e}")
    
    async def start_broadcasting(self):
        """Start periodic broadcasting with proper error handling"""
        self.is_running = True
        
        while self.is_running:
            try:
                await self.broadcast_updates()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                logger.info("Broadcasting cancelled")
                break
            except Exception as e:
                logger.error(f"Error in broadcasting loop: {e}")
                # Add exponential backoff on error
                await asyncio.sleep(min(self.update_interval * 2, 120))
    
    def stop_broadcasting(self):
        """Stop the broadcasting loop"""
        self.is_running = False

# Global WebSocket instance for management
dashboard_websocket = DashboardWebSocket()

# Function to start WebSocket broadcasting as a background task
def start_dashboard_websocket():
    """Start dashboard WebSocket broadcasting"""
    if not dashboard_websocket.is_running:
        asyncio.create_task(dashboard_websocket.start_broadcasting())

def stop_dashboard_websocket():
    """Stop dashboard WebSocket broadcasting"""
    dashboard_websocket.stop_broadcasting()
