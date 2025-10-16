"""
Base Task Classes with Heartbeat and Status Management

This module provides base task classes that handle heartbeat updates,
status tracking, and proper cleanup for long-running sync tasks.
"""
import time
import threading
import logging
from typing import Optional, Dict, Any
from celery import Task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

logger = logging.getLogger(__name__)


def _get_global_concurrency_guard():
    """Lazy import to avoid circular dependencies"""
    try:
        from ingestion.services.concurrency_guard import global_concurrency_guard
        return global_concurrency_guard
    except ImportError as e:
        logger.warning(f"Could not import concurrency guard: {e}")
        # Return a dummy context manager if import fails
        from contextlib import nullcontext
        return nullcontext


class BaseTask(Task):
    """
    Base task class with heartbeat, status tracking, and concurrency control
    """
    
    def __init__(self):
        super().__init__()
        self._heartbeat_thread = None
        self._stop_heartbeat = False
        self._sync_run_id = None
        self._task_name = None
    
    def apply_async(self, args=None, kwargs=None, **options):
        """Override to set task name from the actual task"""
        result = super().apply_async(args, kwargs, **options)
        self._task_name = self.name
        return result
    
    def __call__(self, *args, **kwargs):
        """
        Main task execution with heartbeat and concurrency control
        """
        task_name = getattr(self, 'name', 'unknown_task')
        self._task_name = task_name
        
        logger.info(f"Starting task {task_name} with ID {self.request.id}")
        
        # Use global concurrency guard
        try:
            global_concurrency_guard = _get_global_concurrency_guard()
            with global_concurrency_guard(task_name):
                return self._execute_with_heartbeat(*args, **kwargs)
        except Exception as e:
            logger.error(f"Task {task_name} failed to acquire concurrency permit: {e}")
            raise
    
    def _execute_with_heartbeat(self, *args, **kwargs):
        """Execute task with heartbeat monitoring"""
        sync_run_id = None
        
        try:
            # Create or find sync_run record
            sync_run_id = self._create_sync_run()
            self._sync_run_id = sync_run_id
            
            # Start heartbeat thread
            self._start_heartbeat(sync_run_id)
            
            # Update status to RUNNING
            self._update_sync_run_status(sync_run_id, 'RUNNING')
            
            # Execute the actual task
            result = self.run(*args, **kwargs)
            
            # Update status to SUCCESS
            self._update_sync_run_status(sync_run_id, 'SUCCESS')
            
            logger.info(f"Task {self._task_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Task {self._task_name} failed: {e}")
            if sync_run_id:
                self._update_sync_run_status(sync_run_id, 'FAILED', str(e))
            raise
            
        finally:
            # Stop heartbeat thread
            self._stop_heartbeat_thread()
            
            # Final cleanup
            if sync_run_id:
                self._finalize_sync_run(sync_run_id)
    
    def _create_sync_run(self) -> Optional[int]:
        """Create a sync_run record for tracking"""
        try:
            from django.apps import apps
            
            # Try to get the SyncRun model if it exists
            try:
                SyncRun = apps.get_model('ingestion', 'SyncRun')
            except LookupError:
                # Model doesn't exist, skip sync_run tracking
                logger.debug("SyncRun model not found, skipping sync_run tracking")
                return None
            
            sync_run = SyncRun.objects.create(
                task_name=self._task_name,
                celery_task_id=self.request.id,
                status='PENDING',
                started_at=timezone.now(),
                heartbeat_at=timezone.now()
            )
            return sync_run.id
            
        except Exception as e:
            logger.warning(f"Could not create sync_run record: {e}")
            return None
    
    def _update_sync_run_status(self, sync_run_id: int, status: str, error_message: str = None):
        """Update sync_run status"""
        if not sync_run_id:
            return
            
        try:
            from django.apps import apps
            SyncRun = apps.get_model('ingestion', 'SyncRun')
            
            with transaction.atomic():
                sync_run = SyncRun.objects.select_for_update().get(id=sync_run_id)
                sync_run.status = status
                sync_run.heartbeat_at = timezone.now()
                
                if status == 'SUCCESS':
                    sync_run.completed_at = timezone.now()
                elif status == 'FAILED':
                    sync_run.completed_at = timezone.now()
                    if error_message:
                        sync_run.error_message = error_message[:1000]  # Truncate long errors
                
                sync_run.save()
                
        except Exception as e:
            logger.warning(f"Could not update sync_run status: {e}")
    
    def _start_heartbeat(self, sync_run_id: int):
        """Start heartbeat thread"""
        if not sync_run_id:
            return
            
        self._stop_heartbeat = False
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            args=(sync_run_id,),
            daemon=True
        )
        self._heartbeat_thread.start()
        logger.debug(f"Started heartbeat thread for sync_run {sync_run_id}")
    
    def _heartbeat_worker(self, sync_run_id: int):
        """Heartbeat worker thread that updates heartbeat every 30 seconds"""
        while not self._stop_heartbeat:
            try:
                # Sleep for 30 seconds (or until stopped)
                for _ in range(30):
                    if self._stop_heartbeat:
                        return
                    time.sleep(1)
                
                # Update heartbeat
                from django.apps import apps
                SyncRun = apps.get_model('ingestion', 'SyncRun')
                
                with transaction.atomic():
                    sync_run = SyncRun.objects.select_for_update().get(id=sync_run_id)
                    sync_run.heartbeat_at = timezone.now()
                    sync_run.save(update_fields=['heartbeat_at'])
                
                logger.debug(f"Updated heartbeat for sync_run {sync_run_id}")
                
            except Exception as e:
                logger.warning(f"Error updating heartbeat for sync_run {sync_run_id}: {e}")
                # Continue trying - don't break on temporary errors
    
    def _stop_heartbeat_thread(self):
        """Stop heartbeat thread"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._stop_heartbeat = True
            self._heartbeat_thread.join(timeout=5)  # Wait max 5 seconds
            logger.debug("Stopped heartbeat thread")
    
    def _finalize_sync_run(self, sync_run_id: int):
        """Final cleanup of sync_run record"""
        try:
            from django.apps import apps
            SyncRun = apps.get_model('ingestion', 'SyncRun')
            
            with transaction.atomic():
                sync_run = SyncRun.objects.select_for_update().get(id=sync_run_id)
                
                # If still running, mark as failed (shouldn't happen)
                if sync_run.status in ['PENDING', 'RUNNING']:
                    sync_run.status = 'FAILED'
                    sync_run.error_message = 'Task finished without proper status update'
                    sync_run.completed_at = timezone.now()
                
                # Final heartbeat update
                sync_run.heartbeat_at = timezone.now()
                sync_run.save()
                
        except Exception as e:
            logger.warning(f"Error finalizing sync_run {sync_run_id}: {e}")


class DataSyncTask(BaseTask):
    """
    Specialized task for data synchronization with additional features
    """
    
    def _execute_with_heartbeat(self, *args, **kwargs):
        """Override to add data sync specific logging"""
        logger.info(f"Starting data sync task: {self._task_name}")
        
        # Log memory usage at start
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Task {self._task_name} starting with {memory_mb:.1f}MB memory usage")
        except ImportError:
            pass
        
        result = super()._execute_with_heartbeat(*args, **kwargs)
        
        # Log memory usage at end
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Task {self._task_name} finished with {memory_mb:.1f}MB memory usage")
        except ImportError:
            pass
        
        return result


def create_base_task_class():
    """Factory function to create task class with proper binding"""
    return BaseTask


def create_data_sync_task_class():
    """Factory function to create data sync task class with proper binding"""
    return DataSyncTask