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
from ingestion.tasks.base import DataSyncTask

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


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_five9_contacts')
def sync_five9_contacts(self, **kwargs):
    """Sync Five9 contacts with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting Five9 contacts sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run Five9 sync command with optimized settings
        result = call_command(
            'sync_five9_contacts',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("Five9 contacts sync completed successfully")
        return {
            'status': 'success', 
            'message': 'Five9 contacts synced successfully', 
            'result': result,
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing Five9 contacts: {e}")
        # DataSyncTask automatically handles error status updates
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


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_hubspot_all')
def sync_hubspot_all(self, **kwargs):
    """Sync all HubSpot data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting HubSpot all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run HubSpot sync command with optimized settings
        call_command(
            'sync_hubspot_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("HubSpot all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'HubSpot data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing HubSpot data: {e}")
        # DataSyncTask automatically handles error status updates
        raise


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_genius_all')
def sync_genius_all(self, **kwargs):
    """Sync all Genius data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting Genius all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run Genius sync command with optimized settings
        call_command(
            'db_genius_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("Genius all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'Genius data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing Genius data: {e}")
        # DataSyncTask automatically handles error status updates
        raise


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_arrivy_all')
def sync_arrivy_all(self, **kwargs):
    """Sync all Arrivy data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting Arrivy all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run Arrivy sync command with optimized settings
        call_command(
            'sync_arrivy_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("Arrivy all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'Arrivy data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing Arrivy data: {e}")
        # DataSyncTask automatically handles error status updates
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
    """
    Execute a scheduled ingestion task for a specific schedule.
    This runs the legacy periodic tasks using management commands directly.
    
    Args:
        schedule_id: The ID of the SyncSchedule to run
    
    Returns:
        dict: Task execution result
    """
    from django.core.cache import cache
    from ingestion.models import SyncSchedule
    from django.core.management import call_command
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Lock key to prevent overlapping runs for the same source and mode
    def _lock_key(source_key: str, mode: str) -> str:
        return f"ingestion-lock:{source_key}:{mode}"
    
    LOCK_TTL = 60 * 60  # 1 hour safety timeout
    
    try:
        schedule = SyncSchedule.objects.get(pk=schedule_id)
        key = _lock_key(schedule.source_key, schedule.mode)
        
        # Try to acquire lock
        if cache.get(key):
            logger.warning(f"Skipping {schedule.source_key}:{schedule.mode} - already running (lock exists)")
            return {"status": "skipped", "reason": "already_running"}
        
        # Set lock
        cache.set(key, True, timeout=LOCK_TTL)
        
        try:
            logger.info(f"Starting ingestion for schedule {schedule_id}: {schedule.source_key}:{schedule.mode}")
            
            # Use the new ingestion adapter for proper model-specific command mapping
            from ingestion.services.ingestion_adapter import run_source_ingestion
            
            # Extract model name from schedule
            model_name = schedule.model_name if hasattr(schedule, 'model_name') else None
            
            # Prepare options from schedule
            options = {}
            if schedule.options:
                options.update(schedule.options)
            
            # Execute using the ingestion adapter (handles model-specific routing)
            run_source_ingestion(
                source_key=schedule.source_key,
                mode=schedule.mode,
                model_name=model_name,
                **options
            )
            
            logger.info(f"Successfully completed ingestion for {schedule.source_key}:{schedule.mode}")
            return {
                "status": "success", 
                "schedule_id": schedule_id,
                "source_key": schedule.source_key,
                "mode": schedule.mode,
                "model_name": model_name
            }
            
        finally:
            # Always release the lock
            cache.delete(key)
            
    except SyncSchedule.DoesNotExist:
        error_msg = f"Schedule {schedule_id} not found"
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
        
    except Exception as e:
        error_msg = f"Ingestion failed for schedule {schedule_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": str(e)}


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


# Additional CRM Sync Tasks using DataSyncTask

@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_callrail_all')
def sync_callrail_all(self, **kwargs):
    """Sync all CallRail data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting CallRail all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run CallRail sync command with optimized settings
        call_command(
            'sync_callrail_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("CallRail all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'CallRail data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing CallRail data: {e}")
        raise


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_leadconduit_all')
def sync_leadconduit_all(self, **kwargs):
    """Sync all LeadConduit data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting LeadConduit all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run LeadConduit sync command with optimized settings
        call_command(
            'sync_leadconduit_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("LeadConduit all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'LeadConduit data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing LeadConduit data: {e}")
        raise


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_salesrabbit_all')
def sync_salesrabbit_all(self, **kwargs):
    """Sync all SalesRabbit data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting SalesRabbit all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run SalesRabbit sync command with optimized settings
        call_command(
            'sync_salesrabbit_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("SalesRabbit all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'SalesRabbit data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing SalesRabbit data: {e}")
        raise


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_gsheet_all')
def sync_gsheet_all(self, **kwargs):
    """Sync all Google Sheets data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting Google Sheets all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run Google Sheets sync command with optimized settings
        call_command(
            'sync_gsheet_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("Google Sheets all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'Google Sheets data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing Google Sheets data: {e}")
        raise


@shared_task(bind=True, base=DataSyncTask, name='ingestion.tasks.sync_salespro_all')
def sync_salespro_all(self, **kwargs):
    """Sync all SalesPro data with enhanced monitoring and concurrency control"""
    try:
        from django.conf import settings
        import os
        
        # Check if required Athena credentials are configured
        required_env_vars = [
            'SALESPRO_ACCESS_KEY_ID',
            'SALESPRO_SECRETE_ACCESS_KEY',
            'SALESPRO_S3_LOCATION'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.info(f"SalesPro sync skipped - missing AWS Athena credentials: {', '.join(missing_vars)}")
            return {
                'status': 'skipped', 
                'message': f'SalesPro sync skipped - missing credentials: {", ".join(missing_vars)}'
            }
        
        # Use optimized settings for performance
        page_size = getattr(settings, 'INGEST_PAGE_SIZE', 200)
        batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        logger.info(f"Starting SalesPro all sync with page_size={page_size}, batch_size={batch_size}")
        
        # Run SalesPro sync command with optimized settings
        call_command(
            'db_salespro_all',
            page_size=page_size,
            batch_size=batch_size,
            **kwargs
        )
        
        logger.info("SalesPro all sync completed successfully")
        return {
            'status': 'success', 
            'message': 'SalesPro data synced successfully',
            'page_size': page_size,
            'batch_size': batch_size
        }
        
    except Exception as e:
        logger.error(f"Error syncing SalesPro data: {e}")
        raise