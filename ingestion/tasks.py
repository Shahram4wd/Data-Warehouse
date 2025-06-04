from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
from ingestion.genius.division_sync import sync_divisions

logger = logging.getLogger(__name__)

@shared_task
def sync_divisions_task():
    """
    Task to synchronize data from Genius CRM.
    This task will be scheduled to run periodically.
    """
    from django.core.management import call_command
    
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