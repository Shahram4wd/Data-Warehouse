"""
Celery tasks for automation reporting and CRM sync operations
"""
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from datetime import timedelta
import logging
from ingestion.genius.division_sync import sync_divisions

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