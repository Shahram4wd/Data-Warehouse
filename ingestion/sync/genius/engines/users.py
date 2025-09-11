"""
Genius Users Sync Engine
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone

from ..clients.users import GeniusUsersClient
from ..processors.users import GeniusUsersProcessor

logger = logging.getLogger(__name__)


class GeniusUsersSyncEngine:
    """Sync engine for Genius users data with chunked processing"""
    
    def __init__(self):
        # Import models here to avoid circular imports
        from ingestion.models import Genius_UserData
        from ingestion.models.common import SyncHistory
        
        self.client = GeniusUsersClient()
        self.processor = GeniusUsersProcessor(Genius_UserData)
        self.chunk_size = 100000  # 100K records per chunk
        self.batch_size = 500     # 500 records per batch
        self.crm_source = 'genius'
        self.entity_type = 'users'
        self.SyncHistory = SyncHistory

    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get last successful sync timestamp from SyncHistory table"""
        try:
            last_sync = self.SyncHistory.objects.filter(
                crm_source=self.crm_source,
                sync_type=self.entity_type,
                status__in=['success', 'completed'],
                end_time__isnull=False
            ).order_by('-end_time').first()
            
            return last_sync.end_time if last_sync else None
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None

    def create_sync_record(self, configuration: Dict[str, Any]):
        """Create SyncHistory record at sync start"""
        return self.SyncHistory.objects.create(
            crm_source=self.crm_source,
            sync_type=self.entity_type,
            status='running',
            start_time=timezone.now(),
            configuration=configuration
        )

    def complete_sync_record(self, sync_record, stats: Dict[str, int], error_message: str = None) -> None:
        """Complete SyncHistory record with results"""
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('total_processed', 0)
        sync_record.records_created = stats.get('created', 0)
        sync_record.records_updated = stats.get('updated', 0)
        sync_record.records_failed = stats.get('errors', 0)
        
        if error_message:
            sync_record.status = 'failed'
            sync_record.error_message = error_message
        else:
            sync_record.status = 'success' if stats.get('errors', 0) == 0 else 'partial'
        
        # Calculate performance metrics
        duration = (sync_record.end_time - sync_record.start_time).total_seconds()
        total_processed = stats.get('total_processed', 0)
        success_rate = ((total_processed - stats.get('errors', 0)) / total_processed) if total_processed > 0 else 0
        
        sync_record.performance_metrics = {
            'duration_seconds': duration,
            'records_per_second': total_processed / duration if duration > 0 else 0,
            'success_rate': success_rate
        }
        
        sync_record.save()
    
    def sync_users(self, since_date: Optional[datetime] = None, force_overwrite: bool = False, dry_run: bool = False, max_records: Optional[int] = None) -> Dict[str, Any]:
        """Sync users data with chunked processing"""
        
        # Automatically determine delta sync timestamp if not provided
        if since_date is None and not force_overwrite:
            last_sync = self.get_last_sync_timestamp()
            if last_sync:
                since_date = last_sync
                logger.info(f"Delta sync: Using last successful sync timestamp: {since_date}")
            else:
                logger.info("No previous successful sync found, performing full sync")
        elif since_date is None and force_overwrite:
            logger.info("Force overwrite mode: Ignoring previous sync timestamps")
        elif since_date:
            logger.info(f"Manual delta sync: Using provided since_date: {since_date}")
        
        logger.info(f"Starting users sync - since_date: {since_date}, force_overwrite: {force_overwrite}, dry_run: {dry_run}, max_records: {max_records}")
        
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
                users_data = self.client.get_users(since_date=since_date, limit=max_records)
                stats = self._process_users_batch(users_data, force_overwrite, dry_run, stats)
            else:
                # For larger datasets, use chunked processing
                stats = self._sync_chunked_users(since_date, force_overwrite, dry_run, max_records, stats)
            
            logger.info(f"Users sync completed - Stats: {stats}")
            
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
    
    def _sync_chunked_users(self, since_date: Optional[datetime], force_overwrite: bool, 
                           dry_run: bool, max_records: Optional[int], 
                           stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process users data in chunks for large datasets"""
        
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
            chunk_data = self.client.get_chunked_users(offset, current_chunk_size, since_date)
            
            if not chunk_data:
                logger.info("No more data to process")
                break
                
            logger.info(f"Processing chunk {(offset // self.chunk_size) + 1}: "
                       f"{len(chunk_data)} records (total processed so far: {total_processed + len(chunk_data)})")
            
            # Process this chunk
            chunk_stats = self._process_users_batch(chunk_data, force_overwrite, dry_run, stats)
            
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
    
    def _process_users_batch(self, users_data: list, force_overwrite: bool, 
                            dry_run: bool, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process a batch of users data using bulk operations"""
        
        if not users_data:
            return stats
            
        field_mapping = self.client.get_field_mapping()
        
        # Process in smaller batches for efficiency
        batch_count = (len(users_data) + self.batch_size - 1) // self.batch_size
        logger.info(f"Processing {len(users_data)} users in {batch_count} batches of {self.batch_size}")
        
        for i in range(0, len(users_data), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch_data = users_data[i:i + self.batch_size]
            
            logger.info(f"Processing batch {batch_num}/{batch_count}: records {i+1}-{min(i+self.batch_size, len(users_data))}")
            
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
    
    def build_where_clause(self, 
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          sync_strategy: str = None) -> str:
        """Build WHERE clause based on sync parameters"""
        conditions = []
        
        # Strategy-based filtering - use updated_at for delta updates when available
        if sync_strategy == "incremental" and since:
            conditions.append(f"updated_at > '{since.strftime('%Y-%m-%d %H:%M:%S')}'")
        elif sync_strategy == "manual_since" and since:
            conditions.append(f"updated_at >= '{since.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        # Date range filtering - also use updated_at for better delta support
        if start_date:
            conditions.append(f"updated_at >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'")
        if end_date:
            conditions.append(f"updated_at <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        return " AND ".join(conditions) if conditions else ""
