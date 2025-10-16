"""
Memory-safe streaming prospects sync engine using keyset pagination.

Replaces the OFFSET-based pagination with id > last_id for better performance
and implements streaming processing to prevent OOM issues.
"""
import gc
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone

from ..clients.prospects import GeniusProspectsClient  
from ..processors.prospects import GeniusProspectsProcessor
from ingestion.models.common import SyncHistory
from ingestion.base.streaming_client import StreamingClient, StreamingProcessor

logger = logging.getLogger(__name__)


class StreamingGeniusProspectsClient(StreamingClient):
    """Streaming client for Genius prospects with keyset pagination"""
    
    def __init__(self):
        super().__init__('prospect p')
        self.base_client = GeniusProspectsClient()  # For compatibility
    
    def get_field_mapping(self) -> List[str]:
        """Return the field mapping for prospects table"""
        return [
            'id', 'cid', 'client_cid', 'first_name', 'last_name', 'email',
            'phone', 'address', 'city', 'state', 'zip', 'latitude', 'longitude',
            'lead_source_id', 'status_id', 'sales_rep_id', 'add_user_id',
            'add_date', 'updated_at', 'notes', 'contact_preference', 'budget_range'
        ]
    
    def build_where_clause(self, since_date: Optional[datetime] = None) -> str:
        """Build WHERE clause for incremental sync"""
        where_parts = []
        
        if since_date:
            where_parts.append(f"p.updated_at >= '{since_date.isoformat()}'")
        
        return " AND ".join(where_parts) if where_parts else ""
    
    def stream_prospects(
        self, 
        since_date: Optional[datetime] = None,
        max_records: Optional[int] = None
    ):
        """Stream prospects using keyset pagination"""
        
        select_fields = [f'p.{field}' for field in self.get_field_mapping()]
        
        where_condition = self.build_where_clause(since_date)
        
        logger.info(
            f"Starting prospects stream: since_date={since_date}, "
            f"max_records={max_records}, page_size={self.page_size}"
        )
        
        return self.stream_records(
            select_fields=select_fields,
            where_condition=where_condition,
            since_date=since_date,
            max_records=max_records
        )


class StreamingGeniusProspectsProcessor(StreamingProcessor):
    """Memory-safe processor for prospects with bulk operations"""
    
    def __init__(self):
        from ingestion.models.genius import Genius_Prospect
        super().__init__(Genius_Prospect)
        self.base_processor = GeniusProspectsProcessor(Genius_Prospect)  # For compatibility
    
    def transform_prospect_record(self, record: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw database record to model format"""
        
        raw_data = dict(zip(field_mapping, record))
        
        # Apply any necessary transformations
        transformed = {}
        for field, value in raw_data.items():
            # Handle None values and data type conversions
            if field in ['latitude', 'longitude'] and value is not None:
                try:
                    transformed[field] = float(value)
                except (ValueError, TypeError):
                    transformed[field] = None
            elif field in ['lead_source_id', 'status_id', 'sales_rep_id', 'add_user_id'] and value is not None:
                try:
                    transformed[field] = int(value)
                except (ValueError, TypeError):
                    transformed[field] = None
            elif field in ['add_date', 'updated_at'] and value is not None:
                # Ensure datetime fields are properly handled
                if isinstance(value, str):
                    try:
                        from django.utils.dateparse import parse_datetime
                        transformed[field] = parse_datetime(value)
                    except Exception:
                        transformed[field] = value
                else:
                    transformed[field] = value
            else:
                transformed[field] = value
        
        return transformed


class StreamingGeniusProspectsSyncEngine:
    """Memory-safe sync engine for Genius prospects using streaming"""
    
    def __init__(self):
        self.client = StreamingGeniusProspectsClient()
        self.processor = StreamingGeniusProspectsProcessor()
        
        # SyncHistory configuration
        self.crm_source = 'genius'
        self.entity_type = 'prospects'
        
        logger.info(
            f"Streaming prospects sync engine initialized: "
            f"page_size={self.client.page_size}, "
            f"bulk_batch_size={self.processor.bulk_batch_size}"
        )
    
    def get_last_sync_timestamp(self, force_overwrite: bool = False) -> Optional[datetime]:
        """Get the timestamp of the last successful sync"""
        if force_overwrite:
            return None
        
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source=self.crm_source,
                sync_type=self.entity_type,
                status__in=['success', 'completed'],
                end_time__isnull=False
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
    
    def complete_sync_record(
        self, 
        sync_record: SyncHistory, 
        stats: Dict[str, Any], 
        error_message: Optional[str] = None
    ):
        """Complete the SyncHistory record"""
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('total_processed', 0)
        sync_record.records_created = stats.get('created', 0)
        sync_record.records_updated = stats.get('updated', 0)
        sync_record.records_failed = stats.get('errors', 0)
        
        # Store performance metrics
        if sync_record.start_time:
            duration = sync_record.end_time - sync_record.start_time
            sync_record.performance_metrics = {
                'duration_seconds': duration.total_seconds(),
                'stats': stats,
                'streaming_mode': True
            }
        
        if error_message:
            sync_record.status = 'failed'
            sync_record.error_message = error_message
        else:
            sync_record.status = 'success'
        
        sync_record.save()
    
    def sync_prospects(
        self, 
        sync_mode: str = 'incremental',
        batch_size: int = 500,
        max_records: Optional[int] = None,
        dry_run: bool = False,
        debug: bool = False,
        skip_validation: bool = False,
        start_date: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync prospects data using streaming for memory safety
        
        Args:
            sync_mode: 'incremental', 'full', or 'force'
            batch_size: Records per batch for bulk operations
            max_records: Maximum number of records to process (for testing)
            dry_run: Whether to perform a dry run without database changes
            debug: Enable debug logging
            skip_validation: Skip data validation steps
            start_date: Manual sync start date
            
        Returns:
            Dictionary containing sync statistics
        """
        logger.info(
            f"Starting streaming prospects sync - sync_mode: {sync_mode}, "
            f"start_date: {start_date}, dry_run: {dry_run}, "
            f"max_records: {max_records}"
        )
        
        # Determine force_overwrite based on sync_mode
        force_overwrite = sync_mode == 'force'
        
        # Determine since_date based on sync mode and start_date
        since_date = None
        if sync_mode == 'incremental' and not start_date:
            since_date = self.get_last_sync_timestamp(force_overwrite)
        elif start_date:
            since_date = start_date
        
        # Create SyncHistory record
        configuration = {
            'sync_mode': sync_mode,
            'start_date': start_date.isoformat() if start_date else None,
            'since_date': since_date.isoformat() if since_date else None,
            'force_overwrite': force_overwrite,
            'dry_run': dry_run,
            'max_records': max_records,
            'streaming_mode': True,
            'page_size': self.client.page_size,
            'bulk_batch_size': self.processor.bulk_batch_size
        }
        sync_record = self.create_sync_record(configuration)
        
        try:
            # Log memory at start
            self.client.memory_guard.log_memory_usage("Starting prospects sync")
            
            # Get prospects stream
            prospects_stream = self.client.stream_prospects(
                since_date=since_date,
                max_records=max_records
            )
            
            # Process stream with memory safety
            stats = self.processor.process_stream(
                records_stream=prospects_stream,
                field_mapping=self.client.get_field_mapping(),
                transform_func=self.processor.transform_prospect_record,
                force_overwrite=force_overwrite,
                dry_run=dry_run
            )
            
            logger.info(f"Streaming prospects sync completed - Stats: {stats}")
            
            # Complete sync record with success
            self.complete_sync_record(sync_record, stats)
            
            # Final memory cleanup
            gc.collect()
            self.client.memory_guard.log_memory_usage("Prospects sync complete")
            
            # Return stats with sync_id for compatibility
            result = stats.copy()
            result['sync_id'] = sync_record.id
            result['streaming_mode'] = True
            return result
            
        except Exception as e:
            logger.error(f"Streaming prospects sync failed: {e}")
            # Complete sync record with error
            error_stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 1}
            self.complete_sync_record(sync_record, error_stats, error_message=str(e))
            raise
        finally:
            # Ensure final cleanup
            gc.collect()


# For backward compatibility, create an alias
GeniusProspectsSyncEngine = StreamingGeniusProspectsSyncEngine