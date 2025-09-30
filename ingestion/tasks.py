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

# generate_automation_reports task moved to tasks_enhanced.py to avoid conflicts

@shared_task
def cleanup_old_data():
    """
    Task to clean up old or temporary data.
    """
    # Add cleanup logic here
    logger.info("Cleanup task completed")
    return True

# run_ingestion task moved to tasks_enhanced.py to avoid conflicts

# Worker pool management tasks
