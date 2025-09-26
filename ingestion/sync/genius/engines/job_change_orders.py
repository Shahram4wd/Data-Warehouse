"""
Job Change Order sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.job_change_orders import GeniusJobChangeOrderClient
from ..processors.job_change_orders import GeniusJobChangeOrderProcessor
from ingestion.models import Genius_JobChangeOrder, SyncHistory

logger = logging.getLogger(__name__)


class GeniusJobChangeOrdersSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius job change order data"""
    
    def __init__(self):
        super().__init__('job_change_orders')
        self.client = GeniusJobChangeOrderClient()
        self.processor = GeniusJobChangeOrderProcessor(Genius_JobChangeOrder)
    
    def sync_job_change_orders(self, since_date=None, force_overwrite=False, 
                                   dry_run=False, max_records=0, full_sync=False, **kwargs) -> Dict[str, Any]:
        """Main sync method for job change orders with delta sync support"""
        
        # Create sync history record
        sync_history = SyncHistory.objects.create(
            crm_source='genius',
            sync_type='job_change_orders',
            start_time=timezone.now(),
            status='running'
        )
        
        # Auto-detect delta sync if since_date not provided, not full sync, and not forcing overwrite
        if since_date is None and not full_sync and not force_overwrite:
            since_date = self.get_last_sync_timestamp()
        
        logger.info(f"🚀 Starting job change orders sync")
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
            logger.info(f"Total job change orders to process: {total_count:,}")
            
            # Get job change orders from source using cursor-based pagination
            raw_data = []
            for chunk in self.client.get_chunked_items(chunk_size=10000, since=since_date):
                raw_data.extend(chunk)
                if max_records and len(raw_data) >= max_records:
                    raw_data = raw_data[:max_records]
                    break
            
            logger.info(f"Fetched {len(raw_data)} job change orders from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process job change orders but making no changes")
                stats['total_processed'] = len(raw_data)
                return stats
            
            if not raw_data:
                logger.info("No job change orders to sync")
                return stats
            
            logger.info(f"Processing {len(raw_data)} job change orders in batches")
            
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
                            for column_index, field_name in enumerate(field_mapping):
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
                    
            logger.info(f"✅ Job change orders sync completed. Stats: {stats}")
            
            # Update sync history
            if not dry_run:
                self.complete_sync_record(sync_history, stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Job change order sync failed: {str(e)}")
            # Mark sync as failed
            sync_history.end_time = timezone.now()
            sync_history.status = 'failed'
            sync_history.save()
            raise
        
        finally:
            # Connection cleanup is handled automatically by the client
            pass
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the last successful sync"""
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='genius',
                sync_type='job_change_orders',
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

