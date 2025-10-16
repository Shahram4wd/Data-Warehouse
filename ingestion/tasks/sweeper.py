"""
Periodic Task Sweeper

This module provides periodic tasks for cleaning up stuck/stale tasks
and maintaining system health.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='ingestion.tasks.sweeper_cleanup_stuck_tasks')
def sweeper_cleanup_stuck_tasks(self):
    """
    Periodic task that marks tasks with no heartbeat >5 min as STUCK
    Runs every 2 minutes to catch stuck tasks quickly
    """
    try:
        from django.apps import apps
        
        # Try to get the SyncRun model if it exists
        try:
            SyncRun = apps.get_model('ingestion', 'SyncRun')
        except LookupError:
            # Model doesn't exist, skip cleanup
            logger.debug("SyncRun model not found, skipping stuck task cleanup")
            return {'status': 'skipped', 'reason': 'SyncRun model not found'}
        
        # Find tasks that are stuck (RUNNING but no heartbeat >5 min)
        stuck_cutoff = timezone.now() - timedelta(minutes=5)
        
        with transaction.atomic():
            stuck_tasks = SyncRun.objects.select_for_update().filter(
                status__in=['PENDING', 'RUNNING'],
                heartbeat_at__lt=stuck_cutoff
            )
            
            stuck_count = stuck_tasks.count()
            
            if stuck_count > 0:
                logger.warning(f"Found {stuck_count} stuck tasks, marking as STUCK")
                
                # Update stuck tasks
                for task in stuck_tasks:
                    old_status = task.status
                    task.status = 'STUCK'
                    task.completed_at = timezone.now()
                    task.error_message = f'Task stuck - no heartbeat since {task.heartbeat_at}'
                    task.save()
                    
                    logger.warning(
                        f"Marked task {task.task_name} (ID: {task.celery_task_id}) "
                        f"as STUCK (was {old_status}, last heartbeat: {task.heartbeat_at})"
                    )
                
                return {
                    'status': 'success',
                    'stuck_tasks_found': stuck_count,
                    'stuck_tasks_marked': stuck_count
                }
            else:
                logger.debug("No stuck tasks found")
                return {
                    'status': 'success',
                    'stuck_tasks_found': 0,
                    'stuck_tasks_marked': 0
                }
        
    except Exception as e:
        logger.error(f"Error in stuck task cleanup: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='ingestion.tasks.sweeper_cleanup_old_sync_runs')
def sweeper_cleanup_old_sync_runs(self):
    """
    Clean up old sync_run records to prevent database bloat
    Runs daily to remove records older than 30 days
    """
    try:
        from django.apps import apps
        
        try:
            SyncRun = apps.get_model('ingestion', 'SyncRun')
        except LookupError:
            logger.debug("SyncRun model not found, skipping old sync_run cleanup")
            return {'status': 'skipped', 'reason': 'SyncRun model not found'}
        
        # Remove sync_runs older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        with transaction.atomic():
            old_runs = SyncRun.objects.filter(started_at__lt=cutoff_date)
            old_count = old_runs.count()
            
            if old_count > 0:
                logger.info(f"Deleting {old_count} old sync_run records (older than 30 days)")
                old_runs.delete()
                
                return {
                    'status': 'success',
                    'deleted_count': old_count
                }
            else:
                return {
                    'status': 'success',
                    'deleted_count': 0
                }
        
    except Exception as e:
        logger.error(f"Error in old sync_run cleanup: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task(bind=True, name='ingestion.tasks.sweeper_memory_monitor')
def sweeper_memory_monitor(self):
    """
    Monitor system memory usage and log warnings if high
    Helps with debugging memory leaks
    """
    try:
        import psutil
        
        # Get system memory info
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get process memory info
        process = psutil.Process()
        process_memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Log memory stats
        logger.info(
            f"Memory usage - System: {memory_percent:.1f}%, "
            f"Process: {process_memory_mb:.1f}MB"
        )
        
        # Warn if system memory is high
        if memory_percent > 85:
            logger.warning(f"High system memory usage: {memory_percent:.1f}%")
        
        # Warn if process memory is high (>500MB)
        if process_memory_mb > 500:
            logger.warning(f"High process memory usage: {process_memory_mb:.1f}MB")
        
        return {
            'status': 'success',
            'system_memory_percent': memory_percent,
            'process_memory_mb': process_memory_mb
        }
        
    except ImportError:
        # psutil not available
        return {
            'status': 'skipped',
            'reason': 'psutil not available'
        }
    except Exception as e:
        logger.error(f"Error in memory monitor: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }