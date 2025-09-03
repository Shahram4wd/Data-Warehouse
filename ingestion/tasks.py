"""
Celery tasks for automation reporting and CRM sync operations
"""
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from datetime import timedelta
import logging


logger = logging.getLogger(__name__)

@shared_task(bind=True, name='ingestion.tasks.generate_automation_reports')
def generate_automation_reports(self):
    """
    Celery task to generate comprehensive automation reports for all CRMs.
    Scheduled to run daily at 9:00 PM and 4:00 AM UTC.
    """
    try:
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
        return {
            'status': 'success',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'message': 'Automation reports generated successfully'
        }
        
    except Exception as e:
        logger.error(f"Failed to generate automation reports: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Failed to generate automation reports'
        }

@shared_task(bind=True, name='ingestion.tasks.sync_hubspot_all')
def sync_hubspot_all(self):
    """
    Celery task to run complete HubSpot sync.
    Can be scheduled or triggered manually.
    """
    try:
        start_time = timezone.now()
        logger.info(f"Starting HubSpot sync at {start_time}")
        
        call_command('sync_hubspot_all_new')
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"HubSpot sync completed successfully in {duration:.2f} seconds")
        return {
            'status': 'success',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'message': 'HubSpot sync completed successfully'
        }
        
    except Exception as e:
        logger.error(f"HubSpot sync failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'message': 'HubSpot sync failed'
        }

@shared_task(bind=True, name='ingestion.tasks.sync_genius_all')
def sync_genius_all(self):
    """
    Celery task to run complete Genius CRM sync.
    Can be scheduled or triggered manually.
    """
    try:
        start_time = timezone.now()
        logger.info(f"Starting Genius sync at {start_time}")
        
        # Call individual Genius sync commands
        call_command('sync_genius_divisions')
        call_command('sync_genius_marketing_sources')
        call_command('sync_genius_users')
        call_command('sync_genius_prospects')
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Genius sync completed successfully in {duration:.2f} seconds")
        return {
            'status': 'success',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'message': 'Genius sync completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Genius sync failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Genius sync failed'
        }

@shared_task(bind=True, name='ingestion.tasks.sync_arrivy_all')
def sync_arrivy_all(self):
    """
    Celery task to run complete Arrivy sync.
    Can be scheduled or triggered manually.
    """
    try:
        start_time = timezone.now()
        logger.info(f"Starting Arrivy sync at {start_time}")
        
        call_command('sync_arrivy_all')
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Arrivy sync completed successfully in {duration:.2f} seconds")
        return {
            'status': 'success',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'message': 'Arrivy sync completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Arrivy sync failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Arrivy sync failed'
        }

@shared_task
def sync_divisions_task():
    """
    Task to synchronize data from Genius CRM.
    This task will be scheduled to run periodically.
    """
    logger.info("Starting Genius data synchronization task")
    
    try:
        # Sync divisions first as they're required for other data
        call_command('sync_genius_divisions')
        
        # Sync marketing sources
        call_command('sync_genius_marketing_sources')
        
        # Add other sync commands as needed
        # call_command('sync_genius_appointments')
        # call_command('sync_genius_prospects')
        
        logger.info("Genius data synchronization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in Genius data synchronization task: {str(e)}")
        return False

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
    
    Args:
        schedule_id: The ID of the IngestionSchedule to run
    
    Returns:
        dict: Task execution result
    """
    from django.core.cache import cache
    from ingestion.models import SyncSchedule
    from ingestion.models.common import SyncHistory
    from ingestion.services.ingestion_adapter import run_source_ingestion
    
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
                sync_type=f"{schedule.mode}_scheduled",
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
        
        # Create SyncHistory run record
        started = timezone.now()
        history = SyncHistory.objects.create(
            crm_source=schedule.source_key,
            sync_type=f"{schedule.mode}_scheduled",
            start_time=started,
            status='running',
            configuration={"schedule_id": schedule.id, **(schedule.options or {})},
        )
        
        try:
            # Execute the actual ingestion
            logger.info(f"Starting ingestion for {schedule.source_key}:{schedule.mode}")
            run_source_ingestion(
                source_key=schedule.source_key,
                mode=schedule.mode,
                **(schedule.options or {}),
            )
            
            # Mark as successful in SyncHistory
            history.status = 'success'
            history.end_time = timezone.now()
            # Optional: duration metrics
            duration_ms = int((history.end_time - started).total_seconds() * 1000)
            history.performance_metrics = {**(history.performance_metrics or {}), "duration_ms": duration_ms}
            history.save(update_fields=['status', 'end_time', 'performance_metrics'])
            logger.info(f"Successfully completed ingestion for {schedule.source_key}:{schedule.mode}")
            
            return {
                'status': 'success',
                'schedule_id': schedule_id,
                'source_key': schedule.source_key,
                'mode': schedule.mode,
                'duration_ms': history.performance_metrics.get('duration_ms') if history.performance_metrics else None,
                'message': 'Ingestion completed successfully'
            }
            
        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            history.status = 'failed'
            history.error_message = error_msg
            history.end_time = timezone.now()
            # Optional: capture traceback size safely omitted here
            duration_ms = int((history.end_time - started).total_seconds() * 1000)
            history.performance_metrics = {**(history.performance_metrics or {}), "duration_ms": duration_ms}
            history.save(update_fields=['status', 'error_message', 'end_time', 'performance_metrics'])
            logger.error(f"Failed ingestion for {schedule.source_key}:{schedule.mode}: {error_msg}", exc_info=True)
            
            # Re-raise to mark task as failed
            raise
            
        finally:
            # Always release the lock
            cache.delete(key)
            
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