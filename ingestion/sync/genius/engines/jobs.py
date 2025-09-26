"""
Jobs sync engine for Genius CRM data synchronization
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone

from ..clients.jobs import GeniusJobClient
from ..processors.jobs import GeniusJobProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class GeniusJobSyncEngine:
    """Sync engine for Genius jobs data with chunked processing"""
    
    def __init__(self):
        # Import model here to avoid circular imports
        from ingestion.models import Genius_Job
        
        self.client = GeniusJobClient()
        self.processor = GeniusJobProcessor(Genius_Job)
        self.chunk_size = 100000  # 100K records per chunk
        self.batch_size = 500     # 500 records per batch
        
        # SyncHistory configuration
        self.crm_source = 'genius'
        self.entity_type = 'jobs'
    
    def get_last_sync_timestamp(self, force_overwrite: bool = False) -> Optional[datetime]:
        """Get the timestamp of the last successful sync"""
        if force_overwrite:
            return None
        
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='genius',
                sync_type='jobs',
                status='success'
            ).order_by('-end_time').first()
            
            if last_sync and last_sync.end_time:
                logger.info(f"📅 Last successful sync: {last_sync.end_time}")
                return last_sync.end_time
            else:
                logger.info("📅 No previous successful sync found, performing full sync")
                return None
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    def create_sync_record(self, configuration: Dict[str, Any]) -> SyncHistory:
        """Create a new SyncHistory record"""
        return SyncHistory.objects.create(
            crm_source=self.crm_source,
            sync_type=self.entity_type,
            configuration=configuration,
            start_time=timezone.now(),
            status='running'
        )
    
    def complete_sync_record(self, sync_record: SyncHistory, stats: Dict[str, Any], 
                           error_message: Optional[str] = None):
        """Complete the SyncHistory record"""
        sync_record.end_time = timezone.now()
        sync_record.total_processed = stats.get('total_processed', 0)
        sync_record.successful_count = stats.get('created', 0) + stats.get('updated', 0)
        sync_record.error_count = stats.get('errors', 0)
        sync_record.statistics = stats
        
        if error_message:
            sync_record.status = 'failed'
            sync_record.error_message = error_message
        else:
            sync_record.status = 'success'
        
        sync_record.save()
    
    def sync_jobs(self, since_date: Optional[datetime] = None, 
                 force_overwrite: bool = False, 
                 dry_run: bool = False,
                 max_records: Optional[int] = None,
                 full_sync: bool = False) -> Dict[str, Any]:
        """
        Sync jobs data with cursor-based pagination and delta sync support
        
        Args:
            since_date: Optional datetime to sync from (for delta updates)
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            max_records: Maximum number of records to process (for testing)
            full_sync: Whether to perform a full sync ignoring delta detection
            
        Returns:
            Dictionary containing sync statistics
        """
        # Create sync history record
        sync_history = SyncHistory.objects.create(
            crm_source='genius',
            sync_type='jobs',
            start_time=timezone.now(),
            status='running'
        )
        
        # Auto-detect delta sync if since_date not provided, not full sync, and not forcing overwrite
        if since_date is None and not full_sync and not force_overwrite:
            since_date = self.get_last_sync_timestamp()
        
        logger.info(f"🚀 Starting jobs sync")
        logger.info(f"   📅 Since date: {since_date}")
        logger.info(f"   🔄 Force overwrite: {force_overwrite}")
        logger.info(f"   🧪 Dry run: {dry_run}")
        logger.info(f"   📊 Max records: {max_records or 'unlimited'}")
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get total count for progress tracking  
            total_count = self.client.get_total_count(since_date)
            logger.info(f"Total jobs to process: {total_count:,}")
            
            # Get jobs from source using cursor-based pagination
            raw_data = []
            for chunk in self.client.get_chunked_items(chunk_size=10000, since=since_date):
                raw_data.extend(chunk)
                if max_records and len(raw_data) >= max_records:
                    raw_data = raw_data[:max_records]
                    break
            
            logger.info(f"Fetched {len(raw_data)} jobs from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process jobs but making no changes")
                stats['total_processed'] = len(raw_data)
                return stats
            
            if not raw_data:
                logger.info("No jobs to sync")
                return stats
            
            logger.info(f"Processing {len(raw_data)} jobs in batches")
            
            # Get field mapping for data transformation
            field_mapping = self.client.get_field_mapping()
            
            # Process in batches for better performance
            batch_size = 10000
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(raw_data) + batch_size - 1) // batch_size
                
                logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
                
                try:
                    # Transform raw tuples to dictionaries using field mapping
                    transformed_batch = []
                    for raw_record in batch:
                        try:
                            # Convert tuple to dictionary using field mapping
                            record_dict = {}
                            for field_name, column_index in field_mapping.items():
                                if column_index < len(raw_record):
                                    record_dict[field_name] = raw_record[column_index]
                            
                            transformed_batch.append(record_dict)
                        except Exception as e:
                            logger.error(f"Transform failed for record {raw_record}: {e}")
                            stats['errors'] += 1
                            continue
                    
                    if not dry_run and transformed_batch:
                        batch_stats = self.processor.process_batch(transformed_batch, force_overwrite=force_overwrite)
                        stats['created'] += batch_stats['created']
                        stats['updated'] += batch_stats['updated']
                        stats['errors'] += batch_stats['errors']
                    
                    stats['total_processed'] += len(transformed_batch)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
                    stats['errors'] += len(batch)
                    
            logger.info(f"✅ Jobs sync completed. Stats: {stats}")
            
            # Update sync history
            if not dry_run:
                self.complete_sync_record(sync_history, stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Job sync failed: {str(e)}")
            # Mark sync as failed
            sync_history.end_time = timezone.now()
            sync_history.status = 'failed'
            sync_history.save()
            raise
        
        finally:
            # Connection cleanup is handled automatically by the client
            pass
    
    def complete_sync_record(self, sync_history, stats):
        """Complete the sync history record"""
        try:
            sync_history.end_time = timezone.now()
            sync_history.status = 'success'
            sync_history.records_processed = stats['total_processed']
            sync_history.records_created = stats['created']
            sync_history.records_updated = stats['updated']
            sync_history.save()
            logger.info(f"✅ Sync history updated: {sync_history.id}")
        except Exception as e:
            logger.error(f"Error updating sync history: {e}")
    

