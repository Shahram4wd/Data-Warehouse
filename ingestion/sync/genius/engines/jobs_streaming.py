"""
Memory-safe streaming jobs sync engine using keyset pagination.

Replaces the OFFSET-based pagination with id > last_id for better performance
and implements streaming processing to prevent OOM issues.
"""
import gc
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone

from ..clients.jobs import GeniusJobsClient
from ..processors.jobs import GeniusJobsProcessor
from ingestion.models.common import SyncHistory
from ingestion.base.streaming_client import StreamingClient, StreamingProcessor

logger = logging.getLogger(__name__)


class StreamingGeniusJobsClient(StreamingClient):
    """Streaming client for Genius jobs with keyset pagination"""
    
    def __init__(self):
        super().__init__('job j')
        self.base_client = GeniusJobsClient()  # For compatibility
    
    def get_field_mapping(self) -> List[str]:
        """Return the field mapping for jobs table"""
        return [
            'id', 'prospect_id', 'appointment_id', 'service_id', 'address',
            'city', 'state', 'zip', 'description', 'status_id', 'start_date',
            'completion_date', 'total_amount', 'deposit_amount', 'sales_rep_id',
            'crew_leader_id', 'add_user_id', 'add_date', 'updated_at'
        ]
    
    def build_where_clause(self, since_date: Optional[datetime] = None) -> str:
        """Build WHERE clause for incremental sync"""
        where_parts = []
        
        if since_date:
            where_parts.append(f"j.updated_at >= '{since_date.isoformat()}'")
        
        return " AND ".join(where_parts) if where_parts else ""
    
    def stream_jobs(
        self, 
        since_date: Optional[datetime] = None,
        max_records: Optional[int] = None
    ):
        """Stream jobs using keyset pagination"""
        
        select_fields = [f'j.{field}' for field in self.get_field_mapping()]
        
        where_condition = self.build_where_clause(since_date)
        
        logger.info(
            f"Starting jobs stream: since_date={since_date}, "
            f"max_records={max_records}, page_size={self.page_size}"
        )
        
        return self.stream_records(
            select_fields=select_fields,
            where_condition=where_condition,
            since_date=since_date,
            max_records=max_records
        )


class StreamingGeniusJobsProcessor(StreamingProcessor):
    """Memory-safe processor for jobs with bulk operations"""
    
    def __init__(self):
        from ingestion.models.genius import Genius_Job
        super().__init__(Genius_Job)
        self.base_processor = GeniusJobsProcessor(Genius_Job)  # For compatibility
    
    def transform_job_record(self, record: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw database record to model format"""
        
        raw_data = dict(zip(field_mapping, record))
        
        # Apply any necessary transformations
        transformed = {}
        for field, value in raw_data.items():
            # Handle None values and data type conversions
            if field in ['total_amount', 'deposit_amount'] and value is not None:
                try:
                    transformed[field] = float(value)
                except (ValueError, TypeError):
                    transformed[field] = 0.0
            elif field in ['prospect_id', 'appointment_id', 'service_id', 'status_id', 'sales_rep_id', 'crew_leader_id', 'add_user_id'] and value is not None:
                try:
                    transformed[field] = int(value)
                except (ValueError, TypeError):
                    transformed[field] = None
            elif field in ['start_date', 'completion_date', 'add_date', 'updated_at'] and value is not None:
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


class StreamingGeniusJobsSyncEngine:
    """Memory-safe sync engine for Genius jobs using streaming"""
    
    def __init__(self):
        self.client = StreamingGeniusJobsClient()
        self.processor = StreamingGeniusJobsProcessor()
        
        # SyncHistory configuration
        self.crm_source = 'genius'
        self.entity_type = 'jobs'
        
        logger.info(
            f"Streaming jobs sync engine initialized: "
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
    
    def sync_jobs(
        self, 
        since_date: Optional[datetime] = None, 
        force_overwrite: bool = False, 
        dry_run: bool = False,
        max_records: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync jobs data using streaming for memory safety
        
        Args:
            since_date: Optional datetime to sync from (for delta updates)
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            max_records: Maximum number of records to process (for testing)
            
        Returns:
            Dictionary containing sync statistics
        """
        logger.info(
            f"Starting streaming jobs sync - since_date: {since_date}, "
            f"force_overwrite: {force_overwrite}, dry_run: {dry_run}, "
            f"max_records: {max_records}"
        )
        
        # Create SyncHistory record
        configuration = {
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
            self.client.memory_guard.log_memory_usage("Starting jobs sync")
            
            # Get jobs stream
            jobs_stream = self.client.stream_jobs(
                since_date=since_date,
                max_records=max_records
            )
            
            # Process stream with memory safety
            stats = self.processor.process_stream(
                records_stream=jobs_stream,
                field_mapping=self.client.get_field_mapping(),
                transform_func=self.processor.transform_job_record,
                force_overwrite=force_overwrite,
                dry_run=dry_run
            )
            
            logger.info(f"Streaming jobs sync completed - Stats: {stats}")
            
            # Complete sync record with success
            self.complete_sync_record(sync_record, stats)
            
            # Final memory cleanup
            gc.collect()
            self.client.memory_guard.log_memory_usage("Jobs sync complete")
            
            # Return stats with sync_id for compatibility
            result = stats.copy()
            result['sync_id'] = sync_record.id
            result['streaming_mode'] = True
            return result
            
        except Exception as e:
            logger.error(f"Streaming jobs sync failed: {e}")
            # Complete sync record with error
            error_stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 1}
            self.complete_sync_record(sync_record, error_stats, error_message=str(e))
            raise
        finally:
            # Ensure final cleanup
            gc.collect()


# For backward compatibility, create an alias
GeniusJobsSyncEngine = StreamingGeniusJobsSyncEngine