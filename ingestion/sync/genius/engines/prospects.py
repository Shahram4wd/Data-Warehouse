"""
Prospects sync engine for Genius CRM data synchronization
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone

from ..clients.prospects import GeniusProspectsClient
from ..processors.prospects import GeniusProspectsProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class GeniusProspectsSyncEngine:
    """Sync engine for Genius prospects data with chunked processing"""
    
    def __init__(self):
        # Import model here to avoid circular imports
        from ingestion.models.genius import Genius_Prospect
        
        self.client = GeniusProspectsClient()
        self.processor = GeniusProspectsProcessor(Genius_Prospect)
        self.chunk_size = 100000  # 100K records per chunk
        self.batch_size = 500     # 500 records per batch
        
        # SyncHistory configuration
        self.crm_source = 'genius'
        self.entity_type = 'prospects'
    
    def get_last_sync_timestamp(self, force_overwrite: bool = False) -> Optional[datetime]:
        """Get the timestamp of the last successful sync"""
        if force_overwrite:
            return None
        
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source=self.crm_source,
                sync_type=self.entity_type,
                status='completed'
            ).order_by('-end_time').first()
            
            return last_sync.end_time if last_sync else None
        except Exception as e:
            logger.warning(f"Could not retrieve last sync timestamp: {e}")
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
    
    def sync_prospects(self, since_date: Optional[datetime] = None, 
                      force_overwrite: bool = False, 
                      dry_run: bool = False,
                      max_records: Optional[int] = None) -> Dict[str, Any]:
        """
        Sync prospects data with chunked processing
        
        Args:
            since_date: Optional datetime to sync from (for delta updates)
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            max_records: Maximum number of records to process (for testing)
            
        Returns:
            Dictionary containing sync statistics
        """
        logger.info(f"Starting prospects sync - since_date: {since_date}, force_overwrite: {force_overwrite}, "
                   f"dry_run: {dry_run}, max_records: {max_records}")
        
        # Create SyncHistory record
        configuration = {
            'since_date': since_date.isoformat() if since_date else None,
            'force_overwrite': force_overwrite,
            'dry_run': dry_run,
            'max_records': max_records
        }
        sync_record = self.create_sync_record(configuration)
        
        try:
            stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
            
            if max_records and max_records <= 10000:
                # For smaller datasets, use direct processing
                logger.info(f"Processing limited dataset: {max_records} records")
                prospects_data = self.client.get_prospects(since_date=since_date, limit=max_records)
                stats = self._process_prospects_batch(prospects_data, force_overwrite, dry_run, stats)
            else:
                # For larger datasets, use chunked processing
                stats = self._sync_chunked_prospects(since_date, force_overwrite, dry_run, max_records, stats)
            
            logger.info(f"Prospects sync completed - Stats: {stats}")
            
            # Complete sync record with success
            self.complete_sync_record(sync_record, stats)
            
            # Return stats with sync_id for compatibility
            result = stats.copy()
            result['sync_id'] = sync_record.id
            return result
            
        except Exception as e:
            # Complete sync record with error
            error_stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 1}
            self.complete_sync_record(sync_record, error_stats, error_message=str(e))
            raise
    
    def _sync_chunked_prospects(self, since_date: Optional[datetime], force_overwrite: bool, 
                               dry_run: bool, max_records: Optional[int], 
                               stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process prospects data in chunks for large datasets"""
        
        offset = 0
        total_processed = 0
        
        while True:
            # Apply max_records limit to chunk size if specified
            current_chunk_size = self.chunk_size
            if max_records:
                remaining = max_records - total_processed
                if remaining <= 0:
                    break
                current_chunk_size = min(self.chunk_size, remaining)
            
            logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {current_chunk_size})")
            
            # Get chunked query for logging
            query = self.client.get_chunked_query(offset, current_chunk_size, since_date)
            logger.info(query)
            
            # Fetch chunk data
            chunk_data = self.client.get_chunked_prospects(offset, current_chunk_size, since_date)
            
            if not chunk_data:
                logger.info("No more data to process")
                break
                
            logger.info(f"Processing chunk {(offset // self.chunk_size) + 1}: "
                       f"{len(chunk_data)} records (total processed so far: {total_processed + len(chunk_data)})")
            
            # Process this chunk
            chunk_stats = self._process_prospects_batch(chunk_data, force_overwrite, dry_run, stats)
            
            # Update running totals
            for key in ['total_processed', 'created', 'updated', 'errors']:
                stats[key] = chunk_stats[key]
            
            total_processed = stats['total_processed']
            
            logger.info(f"Chunk {(offset // self.chunk_size) + 1} completed - "
                       f"Created: {chunk_stats['created'] - (stats['created'] - len([r for r in chunk_data if r]))}, "
                       f"Updated: {chunk_stats['updated'] - (stats['updated'] - len([r for r in chunk_data if r]))}, "
                       f"Running totals: {stats['created']} created, {stats['updated']} updated")
            
            # Move to next chunk
            offset += current_chunk_size
            
            # Break if we got less data than requested (end of data)
            if len(chunk_data) < current_chunk_size:
                break
        
        return stats
    
    def _process_prospects_batch(self, prospects_data: list, force_overwrite: bool, 
                                dry_run: bool, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process a batch of prospects data using bulk operations"""
        
        if not prospects_data:
            return stats
            
        field_mapping = self.client.get_field_mapping()
        
        # Process in smaller batches for efficiency
        batch_count = (len(prospects_data) + self.batch_size - 1) // self.batch_size
        logger.info(f"Processing {len(prospects_data)} prospects in {batch_count} batches of {self.batch_size}")
        
        for i in range(0, len(prospects_data), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch_data = prospects_data[i:i + self.batch_size]
            
            logger.info(f"Processing batch {batch_num}/{batch_count}: records {i+1}-{min(i+self.batch_size, len(prospects_data))}")
            
            try:
                # Process batch through processor
                batch_stats = self.processor.process_batch(
                    batch_data, 
                    field_mapping, 
                    force_overwrite=force_overwrite,
                    dry_run=dry_run
                )
                
                # Update cumulative stats
                for key, value in batch_stats.items():
                    stats[key] += value
                
                logger.info(f"Batch {batch_num} completed - Created: {batch_stats['created']}, "
                           f"Updated: {batch_stats['updated']}, Total so far: {stats['created']} created, "
                           f"{stats['updated']} updated")
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                stats['errors'] += len(batch_data)
        
        return stats
