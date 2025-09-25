"""
Celery tasks for automation reporting and CRM sync operations
Enhanced with worker pool integration for proper queuing and worker limit enforcement.
"""
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from datetime import timedelta
import logging


logger = logging.getLogger(__name__)


def _update_worker_pool_status(celery_task_id, status_str, error_message=None):
    """Helper function to update worker pool task status"""
    try:
        from ingestion.services.worker_pool import get_worker_pool, TaskStatus
        
        # Convert string to TaskStatus enum
        status_map = {
            'running': TaskStatus.RUNNING,
            'completed': TaskStatus.COMPLETED,
            'failed': TaskStatus.FAILED,
            'cancelled': TaskStatus.CANCELLED
        }
        status = status_map.get(status_str, TaskStatus.FAILED)
        
        worker_pool = get_worker_pool()
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == celery_task_id:
                worker_pool.update_task_status(task_id, status, error_message)
                break
    except Exception as e:
        logger.debug(f"Could not update worker pool status: {e}")


def _task_wrapper(task_func, celery_task_id):
    """Wrapper function for tasks to integrate with worker pool"""
    def wrapper(*args, **kwargs):
        try:
            # Mark as running
            _update_worker_pool_status(celery_task_id, 'running')
            
            # Execute the task
            result = task_func(*args, **kwargs)
            
            # Mark as completed
            _update_worker_pool_status(celery_task_id, 'completed')
            
            return result
            
        except Exception as e:
            # Mark as failed
            _update_worker_pool_status(celery_task_id, 'failed', str(e))
            raise
    
    return wrapper


@shared_task(bind=True, name='ingestion.tasks.cleanup_stale_syncs')
def cleanup_stale_syncs(self, minutes: int | None = None, dry_run: bool = False):
    """Run the cleanup_stale_syncs management command.

    Defaults to settings.WORKER_POOL_STALE_MINUTES when minutes is None.
    """
    try:
        args = []
        if minutes is not None:
            args += ["--minutes", str(minutes)]
        if dry_run:
            args += ["--dry-run"]

        call_command("cleanup_stale_syncs", *args)
        return {"status": "success", "dry_run": dry_run, "minutes": minutes}
    except Exception as e:
        logger.error(f"cleanup_stale_syncs task failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

@shared_task(bind=True, name='ingestion.tasks.generate_automation_reports')
def generate_automation_reports(self):
    """
    Celery task to generate comprehensive automation reports for all CRMs.
    Scheduled to run daily at 9:00 PM and 4:00 AM UTC.
    Enhanced with worker pool integration.
    """
    try:
        # Update worker pool status
        _update_worker_pool_status(self.request.id, 'running')
        
        start_time = timezone.now()
        logger.info(f"Starting scheduled automation reports generation at {start_time}")
        
        # Call the management command
        call_command(
            'generate_automation_reports',
            '--time-window', 24,
            '--detailed',
            '--crm', 'all',
            '--export-json',
            '--output-dir', 'logs/automation_reports'
        )
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Automation reports generation completed successfully in {duration:.2f} seconds")
        
        result = {
            'status': 'success',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'message': 'Automation reports generated successfully'
        }
        
        # Update worker pool status
        _update_worker_pool_status(self.request.id, 'completed')
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate automation reports: {e}", exc_info=True)
        
        # Update worker pool status
        _update_worker_pool_status(self.request.id, 'failed', str(e))
        
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Failed to generate automation reports'
        }

@shared_task
def cleanup_old_data():
    """
    Task to clean up old or temporary data.
    """
    # Add cleanup logic here
    logger.info("Cleanup task completed")
    return True

@shared_task(bind=True, name="ingestion.run_ingestion")
def run_ingestion(self, schedule_id: int):
    """
    Execute a scheduled ingestion task for a specific schedule.
    This task now integrates with the worker pool system to ensure proper queuing and worker limits.
    
    Args:
        schedule_id: The ID of the IngestionSchedule to run
    
    Returns:
        dict: Task execution result
    """
    from django.core.cache import cache
    from ingestion.models import SyncSchedule
    from ingestion.models.common import SyncHistory
    from ingestion.services.worker_pool import get_worker_pool
    
    # Lock key to prevent overlapping runs for the same source and mode
    def _lock_key(source_key: str, mode: str) -> str:
        return f"ingestion-lock:{source_key}:{mode}"
    
    LOCK_TTL = 60 * 60  # 1 hour safety timeout
    
    try:
        schedule = SyncSchedule.objects.select_related('periodic_task').get(pk=schedule_id)
        key = _lock_key(schedule.source_key, schedule.mode)
        
        # Try to acquire lock
        if not cache.add(key, "1", LOCK_TTL):
            # Another task is already running for this source/mode combination
            logger.warning(f"Skipped ingestion for {schedule.source_key}:{schedule.mode} due to overlap")
            # Record a skipped run in SyncHistory
            SyncHistory.objects.create(
                crm_source=schedule.source_key,
                sync_type=schedule.model_name,
                start_time=timezone.now(),
                end_time=timezone.now(),
                status='failed',  # represent skip as failed/partial if needed
                error_message='Skipped due to overlapping execution',
                configuration={"schedule_id": schedule.id}
            )
            return {
                'status': 'skipped_overlap',
                'schedule_id': schedule_id,
                'source_key': schedule.source_key,
                'mode': schedule.mode,
                'message': 'Skipped due to overlapping execution'
            }
        
        # Instead of running directly, submit to worker pool
        worker_pool = get_worker_pool()
        
        # Submit task to worker pool with schedule information
        task_id = worker_pool.submit_task(
            crm_source=schedule.source_key,
            sync_type=schedule.model_name or 'all',  # Use 'all' if no specific model
            parameters=schedule.options or {},
            priority=0
        )
        
        logger.info(f"Submitted scheduled ingestion to worker pool: {task_id} for {schedule.source_key}:{schedule.mode}")
        
        # Create SyncHistory run record
        started = timezone.now()
        history = SyncHistory.objects.create(
            crm_source=schedule.source_key,
            sync_type=schedule.model_name,
            start_time=started,
            status='running',
            configuration={"schedule_id": schedule.id, "worker_pool_task_id": task_id, **(schedule.options or {})},
        )
        
        # Return success - the actual execution will be handled by the worker pool
        return {
            'status': 'queued',
            'schedule_id': schedule_id,
            'source_key': schedule.source_key,
            'mode': schedule.mode,
            'worker_pool_task_id': task_id,
            'message': 'Task submitted to worker pool for execution'
        }
            
    except Exception as e:
        # Mark as failed and release lock
        error_msg = str(e)
        logger.error(f"Failed to submit scheduled ingestion {schedule_id}: {error_msg}", exc_info=True)
        
        # Clean up lock
        cache.delete(key)
        
        return {
            'status': 'error',
            'schedule_id': schedule_id,
            'error': error_msg,
            'message': f'Failed to submit task to worker pool: {error_msg}'
        }
            
    except SyncSchedule.DoesNotExist:
        logger.error(f"SyncSchedule with ID {schedule_id} does not exist")
        return {
            'status': 'error',
            'schedule_id': schedule_id,
            'message': 'Schedule does not exist'
        }
    except Exception as e:
        logger.error(f"Unexpected error in run_ingestion task: {e}", exc_info=True)
        return {
            'status': 'error',
            'schedule_id': schedule_id,
            'error': str(e),
            'message': 'Unexpected error occurred'
        }


# Worker pool management tasks
@shared_task(bind=True, name='ingestion.tasks.worker_pool_monitor')
def worker_pool_monitor(self):
    """Monitor worker pool and update task statuses"""
    try:
        from ingestion.services.worker_pool import get_worker_pool
        
        worker_pool = get_worker_pool()
        
        # Check Celery task statuses
        worker_pool.check_celery_task_statuses()
        
        # Cleanup old completed tasks
        worker_pool.cleanup_completed_tasks()
        # Cleanup stale active tasks (no heartbeat)
        stale = worker_pool.cleanup_stale_active_tasks()
        
        # Process any pending tasks
        worker_pool.process_queue()
        
        stats = worker_pool.get_stats()
        logger.debug(f"Worker pool monitor: {stats['active_count']} active, {stats['queued_count']} queued, stale_cleaned={stale}")
        
        return {'status': 'success', 'stats': stats}
        
    except Exception as e:
        logger.error(f"Worker pool monitor error: {e}")
        raise