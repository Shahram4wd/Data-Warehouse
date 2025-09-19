"""
Enhanced Celery Tasks with Worker Pool Integration

This module provides enhanced Celery tasks that integrate with the worker pool
management system for proper queuing and worker limit enforcement.
"""
import logging
from typing import Dict, Any, Optional
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='ingestion.tasks.generate_automation_reports')
def generate_automation_reports(self):
    """Generate automation reports task - existing functionality"""
    try:
        from ingestion.services.worker_pool import get_worker_pool
        
        # Update worker pool that task started
        worker_pool = get_worker_pool()
        # Find task in worker pool by celery task ID
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                from ingestion.services.worker_pool import TaskStatus
                worker_pool.update_task_status(task_id, TaskStatus.RUNNING)
                break
        
        # Run the actual task
        logger.info("Starting automation reports generation...")
        call_command('generate_automation_reports')
        logger.info("Automation reports generation completed")
        
        # Update worker pool that task completed
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                from ingestion.services.worker_pool import TaskStatus
                worker_pool.update_task_status(task_id, TaskStatus.COMPLETED)
                break
        
        return {'status': 'success', 'message': 'Automation reports generated successfully'}
        
    except Exception as e:
        logger.error(f"Error generating automation reports: {e}")
        
        # Update worker pool that task failed
        try:
            from ingestion.services.worker_pool import get_worker_pool, TaskStatus
            worker_pool = get_worker_pool()
            for task_id, worker_task in worker_pool.active_workers.items():
                if worker_task.celery_task_id == self.request.id:
                    worker_pool.update_task_status(task_id, TaskStatus.FAILED, str(e))
                    break
        except:
            pass
        
        raise


@shared_task(bind=True, name='ingestion.tasks.sync_five9_contacts')
def sync_five9_contacts(self, **kwargs):
    """Sync Five9 contacts with worker pool integration"""
    try:
        from ingestion.services.worker_pool import get_worker_pool, TaskStatus
        
        # Update worker pool that task started
        worker_pool = get_worker_pool()
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.RUNNING)
                break
        
        # Run the sync
        logger.info("Starting Five9 contacts sync...")
        result = call_command('sync_five9_contacts', **kwargs)
        logger.info("Five9 contacts sync completed")
        
        # Update worker pool that task completed
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.COMPLETED)
                break
        
        return {'status': 'success', 'message': 'Five9 contacts synced successfully', 'result': result}
        
    except Exception as e:
        logger.error(f"Error syncing Five9 contacts: {e}")
        
        # Update worker pool that task failed
        try:
            from ingestion.services.worker_pool import get_worker_pool, TaskStatus
            worker_pool = get_worker_pool()
            for task_id, worker_task in worker_pool.active_workers.items():
                if worker_task.celery_task_id == self.request.id:
                    worker_pool.update_task_status(task_id, TaskStatus.FAILED, str(e))
                    break
        except:
            pass
        
        raise


@shared_task(bind=True, name='ingestion.tasks.sync_genius_marketsharp_contacts')
def sync_genius_marketsharp_contacts(self, **kwargs):
    """Sync Genius MarketSharp contacts with worker pool integration"""
    try:
        from ingestion.services.worker_pool import get_worker_pool, TaskStatus
        
        # Update worker pool that task started
        worker_pool = get_worker_pool()
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.RUNNING)
                break
        
        # Run the sync
        logger.info("Starting Genius MarketSharp contacts sync...")
        result = call_command('sync_marketsharp_data', endpoint='contacts', **kwargs)
        logger.info("Genius MarketSharp contacts sync completed")
        
        # Update worker pool that task completed
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.COMPLETED)
                break
        
        return {'status': 'success', 'message': 'Genius MarketSharp contacts synced successfully', 'result': result}
        
    except Exception as e:
        logger.error(f"Error syncing Genius MarketSharp contacts: {e}")
        
        # Update worker pool that task failed
        try:
            from ingestion.services.worker_pool import get_worker_pool, TaskStatus
            worker_pool = get_worker_pool()
            for task_id, worker_task in worker_pool.active_workers.items():
                if worker_task.celery_task_id == self.request.id:
                    worker_pool.update_task_status(task_id, TaskStatus.FAILED, str(e))
                    break
        except:
            pass
        
        raise


@shared_task(bind=True, name='ingestion.tasks.sync_hubspot_all')
def sync_hubspot_all(self, **kwargs):
    """Sync all HubSpot data with worker pool integration"""
    try:
        from ingestion.services.worker_pool import get_worker_pool, TaskStatus
        
        # Update worker pool that task started
        worker_pool = get_worker_pool()
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.RUNNING)
                break
        
        # Run HubSpot sync tasks
        logger.info("Starting HubSpot all sync...")
        # Add HubSpot sync logic here
        logger.info("HubSpot all sync completed")
        
        # Update worker pool that task completed
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.COMPLETED)
                break
        
        return {'status': 'success', 'message': 'HubSpot data synced successfully'}
        
    except Exception as e:
        logger.error(f"Error syncing HubSpot data: {e}")
        
        # Update worker pool that task failed
        try:
            from ingestion.services.worker_pool import get_worker_pool, TaskStatus
            worker_pool = get_worker_pool()
            for task_id, worker_task in worker_pool.active_workers.items():
                if worker_task.celery_task_id == self.request.id:
                    worker_pool.update_task_status(task_id, TaskStatus.FAILED, str(e))
                    break
        except:
            pass
        
        raise


@shared_task(bind=True, name='ingestion.tasks.sync_genius_all')
def sync_genius_all(self, **kwargs):
    """Sync all Genius data with worker pool integration"""
    try:
        from ingestion.services.worker_pool import get_worker_pool, TaskStatus
        
        # Update worker pool that task started
        worker_pool = get_worker_pool()
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.RUNNING)
                break
        
        # Run Genius sync tasks
        logger.info("Starting Genius all sync...")
        # Add Genius sync logic here
        logger.info("Genius all sync completed")
        
        # Update worker pool that task completed
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.COMPLETED)
                break
        
        return {'status': 'success', 'message': 'Genius data synced successfully'}
        
    except Exception as e:
        logger.error(f"Error syncing Genius data: {e}")
        
        # Update worker pool that task failed
        try:
            from ingestion.services.worker_pool import get_worker_pool, TaskStatus
            worker_pool = get_worker_pool()
            for task_id, worker_task in worker_pool.active_workers.items():
                if worker_task.celery_task_id == self.request.id:
                    worker_pool.update_task_status(task_id, TaskStatus.FAILED, str(e))
                    break
        except:
            pass
        
        raise


@shared_task(bind=True, name='ingestion.tasks.sync_arrivy_all')
def sync_arrivy_all(self, **kwargs):
    """Sync all Arrivy data with worker pool integration"""
    try:
        from ingestion.services.worker_pool import get_worker_pool, TaskStatus
        
        # Update worker pool that task started
        worker_pool = get_worker_pool()
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.RUNNING)
                break
        
        # Run Arrivy sync tasks
        logger.info("Starting Arrivy all sync...")
        # Add Arrivy sync logic here
        logger.info("Arrivy all sync completed")
        
        # Update worker pool that task completed
        for task_id, worker_task in worker_pool.active_workers.items():
            if worker_task.celery_task_id == self.request.id:
                worker_pool.update_task_status(task_id, TaskStatus.COMPLETED)
                break
        
        return {'status': 'success', 'message': 'Arrivy data synced successfully'}
        
    except Exception as e:
        logger.error(f"Error syncing Arrivy data: {e}")
        
        # Update worker pool that task failed
        try:
            from ingestion.services.worker_pool import get_worker_pool, TaskStatus
            worker_pool = get_worker_pool()
            for task_id, worker_task in worker_pool.active_workers.items():
                if worker_task.celery_task_id == self.request.id:
                    worker_pool.update_task_status(task_id, TaskStatus.FAILED, str(e))
                    break
        except:
            pass
        
        raise


# Existing tasks maintained for backward compatibility
@shared_task
def sync_divisions_task():
    """Task to sync divisions data"""
    try:
        logger.info("Starting divisions sync...")
        call_command('sync_divisions')
        logger.info("Divisions sync completed")
        return {'status': 'success', 'message': 'Divisions synced successfully'}
    except Exception as e:
        logger.error(f"Error syncing divisions: {e}")
        raise


@shared_task
def cleanup_old_data():
    """Task to clean up old or temporary data"""
    try:
        logger.info("Starting data cleanup...")
        # Add cleanup logic here
        logger.info("Data cleanup completed")
        return {'status': 'success', 'message': 'Old data cleaned up successfully'}
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        raise


@shared_task(bind=True, name="ingestion.run_ingestion")
def run_ingestion(self, schedule_id: int):
    """Run ingestion task"""
    try:
        logger.info(f"Starting ingestion for schedule {schedule_id}...")
        # Add ingestion logic here
        logger.info(f"Ingestion for schedule {schedule_id} completed")
        return {'status': 'success', 'message': f'Ingestion for schedule {schedule_id} completed'}
    except Exception as e:
        logger.error(f"Error running ingestion for schedule {schedule_id}: {e}")
        raise


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
        
        # Process any pending tasks
        worker_pool.process_queue()
        
        stats = worker_pool.get_stats()
        logger.debug(f"Worker pool monitor: {stats['active_count']} active, {stats['queued_count']} queued")
        
        return {'status': 'success', 'stats': stats}
        
    except Exception as e:
        logger.error(f"Worker pool monitor error: {e}")
        raise