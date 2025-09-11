"""
Appointments sync engine for Genius CRM data synchronization
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone

from ..clients.appointments import GeniusAppointmentsClient
from ..processors.appointments import GeniusAppointmentsProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class GeniusAppointmentsSyncEngine:
    """Sync engine for Genius appointments data with chunked processing"""
    
    def __init__(self):
        # Import model here to avoid circular imports
        from ingestion.models import Genius_Appointment
        
        self.client = GeniusAppointmentsClient()
        self.processor = GeniusAppointmentsProcessor()
        self.chunk_size = 100000  # 100K records per chunk
        self.batch_size = 500     # 500 records per batch
        
        # SyncHistory configuration
        self.crm_source = 'genius'
        self.entity_type = 'appointments'
    
    def get_last_sync_timestamp(self, force_overwrite: bool = False) -> Optional[datetime]:
        """Get the timestamp of the last successful sync"""
        if force_overwrite:
            return None
        
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source=self.crm_source,
                sync_type=self.entity_type,
                status='success'
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
        sync_record.records_processed = stats.get('total_processed', 0)
        sync_record.records_created = stats.get('created', 0)
        sync_record.records_updated = stats.get('updated', 0)
        sync_record.records_failed = stats.get('errors', 0)
        sync_record.performance_metrics = stats
        
        if error_message:
            sync_record.status = 'failed'
            sync_record.error_message = error_message
        else:
            sync_record.status = 'success'
        
        sync_record.save()
    
    def sync_appointments(self, since_date: Optional[datetime] = None, 
                         force_overwrite: bool = False, 
                         dry_run: bool = False,
                         max_records: Optional[int] = None) -> Dict[str, Any]:
        """
        Sync appointments data with chunked processing
        
        Args:
            since_date: Optional datetime to sync from (for delta updates)
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            max_records: Maximum number of records to process (for testing)
            
        Returns:
            Dictionary containing sync statistics
        """
        logger.info(f"Starting appointments sync - since_date: {since_date}, force_overwrite: {force_overwrite}, "
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
                appointments_data = self.client.get_appointments(since=since_date, limit=max_records)
                stats = self._process_appointments_batch(appointments_data, force_overwrite, dry_run, stats)
            else:
                # For larger datasets, use chunked processing
                stats = self._sync_chunked_appointments(since_date, force_overwrite, dry_run, max_records, stats)
            
            logger.info(f"Appointments sync completed - Stats: {stats}")
            
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
    
    def _sync_chunked_appointments(self, since_date: Optional[datetime], force_overwrite: bool, 
                                  dry_run: bool, max_records: Optional[int], 
                                  stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process appointments data in chunks for large datasets"""
        
        # Get total count first
        total_count = self.client.get_appointments_count(since=since_date)
        logger.info(f"Total appointments to process: {total_count}")
        
        if max_records:
            total_count = min(total_count, max_records)
            
        # Process in chunks using limit and offset simulation
        processed = 0
        chunk_num = 1
        
        while processed < total_count:
            # Calculate chunk size
            current_chunk_size = min(self.chunk_size, total_count - processed)
            
            if current_chunk_size <= 0:
                break
                
            logger.info(f"Processing chunk {chunk_num}: records {processed + 1} to {processed + current_chunk_size}")
            
            # Fetch chunk data (the client will handle pagination internally)
            chunk_data = self.client.get_appointments(since=since_date, limit=current_chunk_size)
            
            if not chunk_data:
                logger.info("No more data to process")
                break
                
            # Skip already processed records if this isn't the first chunk
            if processed > 0:
                chunk_data = chunk_data[processed:]
                
            # Limit to current chunk size
            chunk_data = chunk_data[:current_chunk_size]
                
            logger.info(f"Processing chunk {chunk_num}: {len(chunk_data)} records")
            
            # Process this chunk
            chunk_stats = self._process_appointments_batch(chunk_data, force_overwrite, dry_run, stats)
            
            # Update stats
            stats = chunk_stats
            processed += len(chunk_data)
            chunk_num += 1
            
            logger.info(f"Chunk {chunk_num - 1} completed - "
                       f"Created: {chunk_stats.get('created', 0)}, "
                       f"Updated: {chunk_stats.get('updated', 0)}, "
                       f"Total processed: {processed}")
        
        return stats
    
    def _process_appointments_batch(self, appointments_data: list, force_overwrite: bool, 
                                   dry_run: bool, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process a batch of appointments data using bulk operations"""
        
        if not appointments_data:
            return stats
            
        field_mapping = self.client.get_field_mapping()
        
        # Process in smaller batches for efficiency
        batch_count = (len(appointments_data) + self.batch_size - 1) // self.batch_size
        logger.info(f"Processing {len(appointments_data)} appointments in {batch_count} batches of {self.batch_size}")
        
        for i in range(0, len(appointments_data), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch_data = appointments_data[i:i + self.batch_size]
            
            logger.info(f"Processing batch {batch_num}/{batch_count}: records {i+1}-{min(i+self.batch_size, len(appointments_data))}")
            
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
