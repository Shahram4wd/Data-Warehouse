"""
Worker Pool API Views for CRM Dashboard

These views provide API endpoints for interacting with the worker pool
management system from the CRM dashboard frontend.
"""
import logging
import json
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from ingestion.services.worker_pool import get_worker_pool, TaskStatus

logger = logging.getLogger(__name__)


class WorkerPoolAPIView(View):
    """Base API view for worker pool operations"""
    
    def dispatch(self, request, *args, **kwargs):
        """Add CORS headers and handle preflight requests"""
        response = super().dispatch(request, *args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
        return response
    
    def options(self, request, *args, **kwargs):
        """Handle CORS preflight requests"""
        return JsonResponse({}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class WorkerPoolStatusView(WorkerPoolAPIView):
    """Get worker pool status and statistics"""
    
    def get(self, request):
        """Get current worker pool status"""
        try:
            worker_pool = get_worker_pool()
            stats = worker_pool.get_stats()
            
            return JsonResponse({
                'success': True,
                'data': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting worker pool status: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SubmitSyncTaskView(WorkerPoolAPIView):
    """Submit a sync task to the worker pool"""
    
    def post(self, request):
        """Submit a new sync task"""
        try:
            data = json.loads(request.body) if request.body else {}
            
            # Extract parameters
            crm_source = data.get('crm_source')
            sync_type = data.get('sync_type', 'all')
            parameters = data.get('parameters', {})
            priority = data.get('priority', 0)
            
            # Validate required parameters
            if not crm_source:
                return JsonResponse({
                    'success': False,
                    'error': 'crm_source is required'
                }, status=400)
            
            # Submit task to worker pool
            worker_pool = get_worker_pool()
            task_id = worker_pool.submit_task(
                crm_source=crm_source,
                sync_type=sync_type,
                parameters=parameters,
                priority=priority
            )
            
            # Get task status
            task = worker_pool.get_task_status(task_id)
            
            response_data = {
                'success': True,
                'task_id': task_id,
                'status': task.status.value if task else 'unknown',
                'message': f'Task submitted successfully'
            }
            
            # Add queue position if queued
            if task and task.status == TaskStatus.QUEUED:
                queued_tasks = worker_pool.get_queued_tasks()
                position = next((i + 1 for i, t in enumerate(queued_tasks) if t.id == task_id), None)
                if position:
                    response_data['queue_position'] = position
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error submitting sync task: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TaskStatusView(WorkerPoolAPIView):
    """Get status of a specific task"""
    
    def get(self, request, task_id):
        """Get status of a specific task"""
        try:
            worker_pool = get_worker_pool()
            task = worker_pool.get_task_status(task_id)
            
            if not task:
                return JsonResponse({
                    'success': False,
                    'error': 'Task not found'
                }, status=404)
            
            response_data = {
                'success': True,
                'task': {
                    'id': task.id,
                    'task_name': task.task_name,
                    'crm_source': task.crm_source,
                    'sync_type': task.sync_type,
                    'status': task.status.value,
                    'priority': task.priority,
                    'queued_at': task.queued_at.isoformat() if task.queued_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'error_message': task.error_message
                }
            }
            
            # Add queue position if queued
            if task.status == TaskStatus.QUEUED:
                queued_tasks = worker_pool.get_queued_tasks()
                position = next((i + 1 for i, t in enumerate(queued_tasks) if t.id == task_id), None)
                if position:
                    response_data['task']['queue_position'] = position
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CancelTaskView(WorkerPoolAPIView):
    """Cancel a specific task"""
    
    def delete(self, request, task_id):
        """Cancel a task"""
        try:
            worker_pool = get_worker_pool()
            success = worker_pool.cancel_task(task_id)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': 'Task cancelled successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Task not found or cannot be cancelled'
                }, status=404)
                
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class WorkerPoolConfigView(WorkerPoolAPIView):
    """Manage worker pool configuration"""
    
    def get(self, request):
        """Get worker pool configuration"""
        try:
            worker_pool = get_worker_pool()
            
            return JsonResponse({
                'success': True,
                'config': {
                    'max_workers': worker_pool.get_max_workers(),
                    'current_active': len(worker_pool.active_workers),
                    'current_queued': len(worker_pool.task_queue)
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting worker pool config: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def post(self, request):
        """Update worker pool configuration"""
        try:
            data = json.loads(request.body) if request.body else {}
            max_workers = data.get('max_workers')
            
            if max_workers is not None:
                if not isinstance(max_workers, int) or max_workers < 1:
                    return JsonResponse({
                        'success': False,
                        'error': 'max_workers must be a positive integer'
                    }, status=400)
                
                worker_pool = get_worker_pool()
                worker_pool.set_max_workers(max_workers)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Max workers updated to {max_workers}',
                    'config': {
                        'max_workers': worker_pool.get_max_workers(),
                        'current_active': len(worker_pool.active_workers),
                        'current_queued': len(worker_pool.task_queue)
                    }
                })
            
            return JsonResponse({
                'success': False,
                'error': 'No valid configuration parameters provided'
            }, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating worker pool config: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')  
class ProcessQueueView(WorkerPoolAPIView):
    """Manually trigger queue processing"""
    
    def post(self, request):
        """Process the task queue"""
        try:
            worker_pool = get_worker_pool()
            worker_pool.process_queue()
            
            stats = worker_pool.get_stats()
            
            return JsonResponse({
                'success': True,
                'message': 'Queue processing triggered',
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


# Compatibility functions for existing CRM dashboard JavaScript
@csrf_exempt 
@require_http_methods(["GET"])
def get_worker_pool_stats(request):
    """Get worker pool statistics - compatibility function"""
    view = WorkerPoolStatusView()
    return view.get(request)


@csrf_exempt
@require_http_methods(["POST"])
def submit_sync_task(request):
    """Submit sync task - compatibility function"""
    view = SubmitSyncTaskView()
    return view.post(request)