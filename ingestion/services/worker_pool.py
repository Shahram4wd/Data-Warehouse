"""
Worker Pool Management Service for Celery Tasks

This service manages a pool of workers for sync tasks, ensuring only the configured
maximum number of workers can run simultaneously. Tasks that exceed the limit are
queued until workers become available.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from django.core.cache import cache
from django.conf import settings
from celery import current_app
from celery.result import AsyncResult
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkerTask:
    """Represents a task in the worker pool"""
    id: str
    task_name: str
    crm_source: str
    sync_type: str
    parameters: Dict[str, Any]
    status: TaskStatus
    priority: int = 0
    queued_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    celery_task_id: str = None
    error_message: str = None
    last_heartbeat: datetime = None
    
    def __post_init__(self):
        if self.queued_at is None:
            self.queued_at = datetime.utcnow()


class WorkerPoolService:
    """
    Service to manage worker pool for sync tasks
    """
    
    # Cache keys
    ACTIVE_WORKERS_KEY = "worker_pool:active_workers"
    TASK_QUEUE_KEY = "worker_pool:task_queue" 
    WORKER_STATS_KEY = "worker_pool:stats"
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or getattr(settings, 'MAX_SYNC_WORKERS', 1)
        self.task_queue: List[WorkerTask] = []
        self.active_workers: Dict[str, WorkerTask] = {}
        
        # Task name mappings for different CRM sync operations
        self.task_mappings = {
            ('five9', 'contacts'): 'ingestion.tasks.sync_five9_contacts',
            ('genius', 'marketsharp_contacts'): 'ingestion.tasks.sync_genius_marketsharp_contacts', 
            ('hubspot', 'all'): 'ingestion.tasks.sync_hubspot_all',
            ('genius', 'all'): 'ingestion.tasks.sync_genius_all',
            ('arrivy', 'all'): 'ingestion.tasks.sync_arrivy_all',
        }
        
        # Load state from cache
        self._load_state()
    
    def _load_state(self):
        """Load worker pool state from cache"""
        try:
            def _deserialize(task_dict: Dict[str, Any]) -> WorkerTask:
                # Ensure backward compatibility with older cached structure (strings)
                td = dict(task_dict)
                # Convert enum string back to TaskStatus
                status_val = td.get('status')
                if isinstance(status_val, str):
                    try:
                        td['status'] = TaskStatus(status_val)
                    except Exception:
                        td['status'] = TaskStatus.FAILED
                # Parse datetimes if they are strings
                for key in ['queued_at', 'started_at', 'completed_at', 'last_heartbeat']:
                    if isinstance(td.get(key), str):
                        try:
                            td[key] = datetime.fromisoformat(td[key])
                        except Exception:
                            td[key] = None
                return WorkerTask(**td)

            # Load active workers
            active_data = cache.get(self.ACTIVE_WORKERS_KEY, {}) or {}
            self.active_workers = {}
            for task_id, task_data in active_data.items():
                try:
                    self.active_workers[task_id] = _deserialize(task_data)
                except Exception as inner_e:
                    logger.warning(f"Skipping corrupt active task {task_id}: {inner_e}")

            # Load task queue
            queue_data = cache.get(self.TASK_QUEUE_KEY, []) or []
            self.task_queue = []
            for task_data in queue_data:
                try:
                    self.task_queue.append(_deserialize(task_data))
                except Exception as inner_e:
                    logger.warning(f"Skipping corrupt queued task: {inner_e}")

            logger.info(f"Loaded worker pool state: {len(self.active_workers)} active, {len(self.task_queue)} queued")

        except Exception as e:
            logger.error(f"Error loading worker pool state: {e}")
            self.active_workers = {}
            self.task_queue = []
    
    def _save_state(self):
        """Save worker pool state to cache"""
        try:
            # Save active workers
            active_data = {}
            for task_id, task in self.active_workers.items():
                active_data[task_id] = {
                    'id': task.id,
                    'task_name': task.task_name,
                    'crm_source': task.crm_source,
                    'sync_type': task.sync_type,
                    'parameters': task.parameters,
                    'status': task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
                    'priority': task.priority,
                    'queued_at': task.queued_at.isoformat() if task.queued_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'last_heartbeat': task.last_heartbeat.isoformat() if getattr(task, 'last_heartbeat', None) else None,
                    'celery_task_id': task.celery_task_id,
                    'error_message': task.error_message
                }
            cache.set(self.ACTIVE_WORKERS_KEY, active_data, timeout=3600)
            
            # Save task queue
            queue_data = []
            for task in self.task_queue:
                queue_data.append({
                    'id': task.id,
                    'task_name': task.task_name,
                    'crm_source': task.crm_source,
                    'sync_type': task.sync_type,
                    'parameters': task.parameters,
                    'status': task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
                    'priority': task.priority,
                    'queued_at': task.queued_at.isoformat() if task.queued_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'last_heartbeat': task.last_heartbeat.isoformat() if getattr(task, 'last_heartbeat', None) else None,
                    'celery_task_id': task.celery_task_id,
                    'error_message': task.error_message
                })
            cache.set(self.TASK_QUEUE_KEY, queue_data, timeout=3600)
            
        except Exception as e:
            logger.error(f"Error saving worker pool state: {e}")
    
    def get_max_workers(self) -> int:
        """Get current max workers setting"""
        return self.max_workers
    
    def set_max_workers(self, max_workers: int):
        """Update max workers setting"""
        if max_workers < 1:
            raise ValueError("Max workers must be at least 1")
        
        old_max = self.max_workers
        self.max_workers = max_workers
        
        logger.info(f"Updated max workers from {old_max} to {max_workers}")
        
        # Process queue if we have more capacity now
        if max_workers > old_max:
            self.process_queue()
    
    def submit_task(self, crm_source: str, sync_type: str, 
                   parameters: Dict[str, Any] = None, priority: int = 0) -> str:
        """
        Submit a task to the worker pool
        
        Args:
            crm_source: CRM source (five9, genius, hubspot, etc.)
            sync_type: Type of sync (contacts, all, etc.)
            parameters: Task parameters
            priority: Task priority (higher = higher priority)
            
        Returns:
            Task ID
        """
        # Always refresh state before mutating to avoid cross-process drift
        self._load_state()

        if parameters is None:
            parameters = {}
        # Normalize inputs
        crm_source = (crm_source or '').strip()
        sync_type = (sync_type or '').strip().lower()
        if not sync_type or sync_type == 'undefined':
            sync_type = 'all'
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Get task name from mapping
        task_key = (crm_source.lower(), sync_type.lower())
        task_name = self.task_mappings.get(task_key)
        
        if not task_name:
            # Fallback to generic task name
            task_name = f"ingestion.tasks.sync_{crm_source}_{sync_type}"
            logger.warning(f"No task mapping found for {task_key}, using fallback: {task_name}")
        
        # Create worker task
        worker_task = WorkerTask(
            id=task_id,
            task_name=task_name,
            crm_source=crm_source,
            sync_type=sync_type,
            parameters=parameters,
            status=TaskStatus.QUEUED,
            priority=priority
        )
        
        # Check if we can run immediately
        if len(self.active_workers) < self.max_workers:
            self._start_task(worker_task)
        else:
            # Add to queue (sorted by priority)
            self.task_queue.append(worker_task)
            self.task_queue.sort(key=lambda x: x.priority, reverse=True)
            
            logger.info(f"Task {task_id} queued (position: {len(self.task_queue)})")
        
        self._save_state()
        return task_id
    
    def _start_task(self, worker_task: WorkerTask):
        """Start a worker task"""
        try:
            worker_task.status = TaskStatus.RUNNING
            worker_task.started_at = datetime.utcnow()
            worker_task.last_heartbeat = worker_task.started_at
            
            # Submit to Celery
            task_name = worker_task.task_name
            # If task name contains undefined, attempt to fallback to '*_all'
            if task_name.endswith('_undefined'):
                fallback_key = (worker_task.crm_source.lower(), 'all')
                fallback_name = self.task_mappings.get(fallback_key)
                if fallback_name:
                    logger.info(f"Replacing undefined task '{task_name}' with fallback '{fallback_name}'")
                    task_name = fallback_name
            celery_task = current_app.send_task(task_name, kwargs=worker_task.parameters)
            
            worker_task.celery_task_id = celery_task.id
            self.active_workers[worker_task.id] = worker_task
            
            logger.info(f"Started task {worker_task.id} ({worker_task.crm_source}.{worker_task.sync_type})")
            
        except Exception as e:
            worker_task.status = TaskStatus.FAILED
            worker_task.error_message = str(e)
            worker_task.completed_at = datetime.utcnow()
            logger.error(f"Failed to start task {worker_task.id}: {e}")
    
    def process_queue(self):
        """Process pending tasks in the queue"""
        # Refresh state to operate on latest
        self._load_state()
        while len(self.active_workers) < self.max_workers and self.task_queue:
            next_task = self.task_queue.pop(0)  # Get highest priority task
            self._start_task(next_task)
        
        self._save_state()
    
    def update_task_status(self, task_id: str, status: TaskStatus, error_message: str = None):
        """Update task status"""
        if task_id in self.active_workers:
            task = self.active_workers[task_id]
            task.status = status
            task.error_message = error_message
            task.last_heartbeat = datetime.utcnow()
            
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.utcnow()
                
                # Update associated SyncHistory record if it exists
                self._update_sync_history(task_id, status, error_message)
                
                # Remove from active workers
                del self.active_workers[task_id]
                
                logger.info(f"Task {task_id} completed with status: {status.value}")
                
                # Process next task in queue
                self.process_queue()
        
        self._save_state()
    
    def _update_sync_history(self, worker_task_id: str, status: TaskStatus, error_message: str = None):
        """Update SyncHistory record associated with this worker task"""
        try:
            from ingestion.models.common import SyncHistory
            from django.utils import timezone
            import json
            
            # Find SyncHistory records that reference this worker task ID
            sync_records = SyncHistory.objects.filter(
                status='running',
                configuration__icontains=worker_task_id
            )
            
            for sync_record in sync_records:
                # Verify this is the correct record by checking the configuration
                config = sync_record.configuration
                if isinstance(config, str):
                    try:
                        config = json.loads(config)
                    except:
                        continue
                
                if isinstance(config, dict) and config.get('worker_pool_task_id') == worker_task_id:
                    # Update the sync record
                    sync_record.end_time = timezone.now()
                    
                    if status == TaskStatus.COMPLETED:
                        sync_record.status = 'success'
                    elif status == TaskStatus.FAILED:
                        sync_record.status = 'failed'
                        sync_record.error_message = error_message or 'Task failed in worker pool'
                    elif status == TaskStatus.CANCELLED:
                        sync_record.status = 'failed'
                        sync_record.error_message = 'Task was cancelled'
                    
                    sync_record.save(update_fields=['status', 'end_time', 'error_message'])
                    
                    logger.info(f"Updated SyncHistory {sync_record.id} to status: {sync_record.status}")
                    break
            
        except Exception as e:
            logger.error(f"Failed to update SyncHistory for worker task {worker_task_id}: {e}")
            # Don't raise - this shouldn't stop the worker pool operation
    
    # Note: SyncHistory cleanup is handled by the existing cleanup_stale_syncs command
    # which uses WORKER_POOL_STALE_MINUTES setting and runs nightly
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        # Refresh state to operate on latest
        self._load_state()
        # Check if task is queued
        for i, task in enumerate(self.task_queue):
            if task.id == task_id:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()
                self.task_queue.pop(i)
                self._save_state()
                logger.info(f"Cancelled queued task {task_id}")
                return True
        
        # Check if task is active
        if task_id in self.active_workers:
            task = self.active_workers[task_id]
            
            # Try to revoke Celery task
            if task.celery_task_id:
                try:
                    current_app.control.revoke(task.celery_task_id, terminate=True)
                    logger.info(f"Revoked Celery task {task.celery_task_id}")
                except Exception as e:
                    logger.error(f"Failed to revoke Celery task: {e}")
            
            # Update status
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            del self.active_workers[task_id]
            
            # Process next task
            self.process_queue()
            self._save_state()
            
            logger.info(f"Cancelled active task {task_id}")
            return True
        
        # If not found in either active or queue
        self._save_state()
        return False
    
    def get_task_status(self, task_id: str) -> Optional[WorkerTask]:
        """Get task status"""
        # Check active workers
        if task_id in self.active_workers:
            return self.active_workers[task_id]
        
        # Check queue
        for task in self.task_queue:
            if task.id == task_id:
                return task
        
        return None
    
    def get_active_tasks(self) -> List[WorkerTask]:
        """Get all active tasks"""
        return list(self.active_workers.values())
    
    def get_queued_tasks(self) -> List[WorkerTask]:
        """Get all queued tasks"""
        return self.task_queue.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics"""
        # Refresh state to reflect any changes from other processes
        self._load_state()
        return {
            'max_workers': self.max_workers,
            'active_count': len(self.active_workers),
            'queued_count': len(self.task_queue),
            'available_workers': self.max_workers - len(self.active_workers),
            'active_tasks': [
                {
                    'id': task.id,
                    'crm_source': task.crm_source,
                    'sync_type': task.sync_type,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'status': task.status.value
                }
                for task in self.active_workers.values()
            ],
            'queued_tasks': [
                {
                    'id': task.id,
                    'crm_source': task.crm_source,
                    'sync_type': task.sync_type,
                    'queued_at': task.queued_at.isoformat() if task.queued_at else None,
                    'priority': task.priority,
                    'position': i + 1
                }
                for i, task in enumerate(self.task_queue)
            ]
        }

    def cancel_all(self) -> Dict[str, int]:
        """Cancel all active and queued tasks; returns counts of cancelled items"""
        # Refresh state to operate on latest
        self._load_state()
        cancelled_active = 0
        cancelled_queued = 0

        # Cancel queued tasks
        while self.task_queue:
            task = self.task_queue.pop(0)
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            cancelled_queued += 1

        # Cancel active tasks (revoke Celery tasks where possible)
        for task_id in list(self.active_workers.keys()):
            task = self.active_workers[task_id]
            if task.celery_task_id:
                try:
                    current_app.control.revoke(task.celery_task_id, terminate=True)
                    logger.info(f"Revoked Celery task {task.celery_task_id}")
                except Exception as e:
                    logger.error(f"Failed to revoke Celery task {task.celery_task_id}: {e}")
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            del self.active_workers[task_id]
            cancelled_active += 1

        # Persist and return stats
        self._save_state()
        return {"cancelled_active": cancelled_active, "cancelled_queued": cancelled_queued}

    def reset_state(self) -> Dict[str, int]:
        """Forcefully clear all worker-pool state (active + queued) and cancel tasks.

        Returns counts of active and queued tasks cleared. This is more aggressive than
        cancel_all because it does not attempt graceful revocation beyond a best effort.
        """
        self._load_state()
        stats = self.cancel_all()
        # After cancel_all, clear any remnants
        self.active_workers.clear()
        self.task_queue.clear()
        self._save_state()
        logger.warning("Worker pool state was forcefully reset")
        return stats
    
    def cleanup_completed_tasks(self, max_age_minutes: int = 60):
        """Clean up old completed tasks from memory"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        # This is handled by moving tasks out of active_workers when completed
        # Additional cleanup can be added here if needed
        
        logger.debug(f"Cleanup completed for tasks older than {max_age_minutes} minutes")

    def cleanup_stale_active_tasks(self, max_stale_minutes: int = None):
        """Mark tasks with no heartbeat for a long time as FAILED and remove them.

        Prevents dashboard from showing phantom active tasks if worker died.
        """
        if max_stale_minutes is None:
            try:
                from django.conf import settings as dj_settings
                max_stale_minutes = getattr(dj_settings, 'WORKER_POOL_STALE_MINUTES', 30)
            except Exception:
                max_stale_minutes = 30
        stale_cutoff = datetime.utcnow() - timedelta(minutes=max_stale_minutes)
        stale_count = 0
        for task_id, task in list(self.active_workers.items()):
            if task.last_heartbeat and task.last_heartbeat < stale_cutoff:
                logger.warning(f"Marking stale task {task_id} (no heartbeat since {task.last_heartbeat}) as FAILED")
                task.status = TaskStatus.FAILED
                task.error_message = task.error_message or 'Stale task heartbeat timeout'
                task.completed_at = datetime.utcnow()
                del self.active_workers[task_id]
                stale_count += 1
        if stale_count:
            self._save_state()
        return stale_count
    
    def check_celery_task_statuses(self):
        """Check Celery task statuses and update accordingly"""
        for task_id, worker_task in list(self.active_workers.items()):
            if worker_task.celery_task_id:
                try:
                    result = AsyncResult(worker_task.celery_task_id)
                    
                    if result.state == 'SUCCESS':
                        self.update_task_status(task_id, TaskStatus.COMPLETED)
                    elif result.state == 'FAILURE':
                        error_msg = str(result.result) if result.result else "Unknown error"
                        self.update_task_status(task_id, TaskStatus.FAILED, error_msg)
                    elif result.state == 'REVOKED':
                        self.update_task_status(task_id, TaskStatus.CANCELLED)
                    else:
                        # heartbeat for active states (PENDING / STARTED)
                        worker_task.last_heartbeat = datetime.utcnow()
                        self._save_state()
                        
                except Exception as e:
                    logger.error(f"Error checking Celery task {worker_task.celery_task_id}: {e}")


# Global instance
_worker_pool_instance = None

def get_worker_pool() -> WorkerPoolService:
    """Get the global worker pool instance"""
    global _worker_pool_instance
    if _worker_pool_instance is None:
        _worker_pool_instance = WorkerPoolService()
    return _worker_pool_instance