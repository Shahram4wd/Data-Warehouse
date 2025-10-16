"""
Memory-safe streaming quotes sync engine using keyset pagination and MySQL.

Replaces the OFFSET-based pagination with id > last_id for better performance
and implements streaming processing to prevent OOM issues.
"""
import gc
import logging
import psutil
from typing import Dict, Any, Optional, Iterator
from datetime import datetime
from django.utils import timezone
from django.conf import settings

from ..clients.base import GeniusBaseClient
from ..processors.quotes import GeniusQuoteProcessor
from ingestion.models import Genius_Quote
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)


class StreamingGeniusQuoteClient(GeniusBaseClient):
    """Streaming client for Genius quotes with keyset pagination and MySQL connection"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'quote'
        
        # Get memory-safe settings
        self.page_size = getattr(settings, 'INGEST_PAGE_SIZE', 5000)
        self.bulk_batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
        # Hard memory guards
        if self.page_size > 5000:
            logger.warning(f"Page size {self.page_size} > 5000, limiting to 5000 for memory safety")
            self.page_size = 5000
            
        logger.info(f"Streaming client initialized: page_size={self.page_size}, bulk_batch_size={self.bulk_batch_size}")
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def stream_quotes(self, since_date: Optional[datetime] = None, max_records: int = 0) -> Iterator[list]:
        """
        Stream quotes using keyset pagination with memory safety
        
        Args:
            since_date: Filter quotes updated after this date
            max_records: Maximum records to fetch (0 = unlimited)
            
        Yields:
            List of quote records (max page_size per yield)
        """
        logger.info(f"Starting quotes stream: since_date={since_date}, max_records={max_records}, page_size={self.page_size}")
        
        last_id = 0
        total_fetched = 0
        page_num = 1
        
        while True:
            logger.info(f"Starting quotes sync: {self.get_memory_usage():.1f}MB RSS")
            
            # Build keyset pagination query
            query = self._build_keyset_query(since_date, last_id, self.page_size)
            
            logger.info(f"Page {page_num}: Fetching records WHERE id > {last_id}")
            
            # Execute query with external MySQL connection
            try:
                records = self._execute_mysql_query(query, since_date, last_id)
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise
            
            if not records:
                logger.info("No more records found, ending stream")
                break
            
            # Check for OOM protection on first page
            if page_num == 1 and len(records) > 10000:
                error_msg = f"Aborting to prevent OOM—first page returned {len(records)} records (> 10000 limit)"
                logger.error(error_msg)
                raise MemoryError(error_msg)
            
            logger.info(f"Page {page_num}: Retrieved {len(records)} records ({self.get_memory_usage():.1f}MB RSS)")
            
            # Update tracking variables
            last_id = records[-1][0]  # Assuming first column is id
            total_fetched += len(records)
            page_num += 1
            
            # Yield the page of records
            yield records
            
            # Check max_records limit
            if max_records > 0 and total_fetched >= max_records:
                logger.info(f"Reached max_records limit: {max_records}")
                break
            
            # Memory cleanup
            del records
            gc.collect()
        
        logger.info(f"Stream complete: {total_fetched} total records fetched in {page_num-1} pages")
    
    def _build_keyset_query(self, since_date: Optional[datetime], last_id: int, page_size: int) -> str:
        """Build keyset pagination query"""
        
        query = """
            SELECT
                q.id,
                q.prospect_id,
                q.appointment_id,
                q.job_id,
                q.client_cid,
                q.service_id,
                q.label,
                q.description,
                q.amount,
                q.expire_date,
                q.status_id,
                q.contract_file_id,
                q.estimate_file_id,
                q.add_user_id,
                q.add_date,
                q.updated_at
            FROM quote q
            WHERE q.id > %s
        """
        
        # Add date filter if provided
        if since_date:
            query += " AND q.updated_at > %s"
        
        # Add ordering and limit for keyset pagination
        query += f" ORDER BY q.id ASC LIMIT {page_size}"
        
        return query
    
    def _execute_mysql_query(self, query: str, since_date: Optional[datetime], last_id: int) -> list:
        """Execute query against external MySQL database"""
        
        connection = None
        cursor = None
        
        try:
            # Get connection to external Genius database
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Execute query with parameters for keyset pagination
            if since_date:
                cursor.execute(query, (last_id, since_date))
            else:
                cursor.execute(query, (last_id,))
            
            # Fetch all results for this page
            records = cursor.fetchall()
            
            return records
            
        except Exception as e:
            logger.error(f"MySQL query failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


class StreamingGeniusQuotesProcessor:
    """Process streamed quotes with memory-safe batching"""
    
    def __init__(self):
        self.bulk_batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def process_stream(self, records_stream: Iterator[list], dry_run: bool = False) -> Dict[str, Any]:
        """
        Process streamed quotes with memory-safe batching
        
        Args:
            records_stream: Iterator yielding pages of quote records
            dry_run: If True, don't write to database
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Starting stream processing: {self.get_memory_usage():.1f}MB RSS")
        
        stats = {
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'pages_processed': 0
        }
        
        buffer = []
        
        try:
            for page_records in records_stream:
                stats['pages_processed'] += 1
                
                # Process records in chunks to control memory
                for i in range(0, len(page_records), self.bulk_batch_size):
                    chunk = page_records[i:i + self.bulk_batch_size]
                    
                    # Convert to quote objects
                    for record in chunk:
                        try:
                            quote_obj = self._convert_to_quote_object(record)
                            buffer.append(quote_obj)
                            stats['total_processed'] += 1
                            
                        except Exception as e:
                            logger.error(f"Error converting record: {e}")
                            stats['total_errors'] += 1
                    
                    # Batch write when buffer is full
                    if len(buffer) >= self.bulk_batch_size:
                        batch_stats = self._write_batch(buffer, dry_run)
                        stats['total_created'] += batch_stats['created']
                        stats['total_updated'] += batch_stats['updated']
                        stats['total_errors'] += batch_stats['errors']
                        
                        # Clear buffer and force garbage collection
                        buffer.clear()
                        gc.collect()
                        
                        logger.info(f"Processed {stats['total_processed']} records, {self.get_memory_usage():.1f}MB RSS")
                
                # Memory cleanup after each page
                del page_records
                gc.collect()
        
        except Exception as e:
            logger.error(f"Stream processing failed: {e}")
            raise
        
        # Process remaining buffer
        if buffer:
            batch_stats = self._write_batch(buffer, dry_run)
            stats['total_created'] += batch_stats['created']
            stats['total_updated'] += batch_stats['updated']
            stats['total_errors'] += batch_stats['errors']
            buffer.clear()
        
        logger.info(f"Stream processing complete: {self.get_memory_usage():.1f}MB RSS")
        return stats
    
    def _convert_to_quote_object(self, record: tuple) -> Genius_Quote:
        """Convert database record to Genius_Quote object using proper data transformation"""
        
        # Use the same transformation logic as the existing quotes processor
        from ingestion.sync.genius.processors.quotes import GeniusQuoteProcessor
        processor = GeniusQuoteProcessor()
        
        # Transform raw tuple to validated dictionary
        quote_data = processor._transform_quote(record)
        
        if not quote_data:
            raise ValueError("Failed to transform quote record")
        
        # Create quote object with transformed data
        quote = Genius_Quote(**quote_data)
        return quote
    
    def _write_batch(self, quotes: list, dry_run: bool = False) -> Dict[str, int]:
        """Write a batch of quotes to database"""
        
        if dry_run:
            logger.info(f"DRY RUN: Would write {len(quotes)} quotes to database")
            return {'created': len(quotes), 'updated': 0, 'errors': 0}
        
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # Use bulk_create with ignore_conflicts for memory efficiency
            created_quotes = Genius_Quote.objects.bulk_create(
                quotes, 
                batch_size=self.bulk_batch_size,
                ignore_conflicts=True
            )
            
            stats['created'] = len(created_quotes)
            
        except Exception as e:
            logger.error(f"Bulk create failed: {e}")
            stats['errors'] = len(quotes)
        
        return stats


class StreamingGeniusQuotesSyncEngine:
    """Streaming sync engine for Genius quotes with memory safety"""
    
    def __init__(self):
        self.client = StreamingGeniusQuoteClient()
        self.processor = StreamingGeniusQuotesProcessor()
        
        # SyncHistory configuration
        self.crm_source = 'genius'
        self.entity_type = 'quotes'
        
        logger.info(f"Streaming quotes sync engine initialized: page_size={self.client.page_size}, bulk_batch_size={self.client.bulk_batch_size}")
    
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
    
    def sync_quotes(self, since_date: Optional[datetime] = None, force_overwrite: bool = False, 
                   dry_run: bool = False, max_records: int = 0) -> Dict[str, Any]:
        """
        Sync quotes with streaming and memory safety
        
        Args:
            since_date: Sync quotes updated after this date
            force_overwrite: Ignore last sync timestamp
            dry_run: Test run without database writes
            max_records: Limit total records (0 = unlimited)
            
        Returns:
            Dictionary with sync results
        """
        
        logger.info(f"Starting streaming quotes sync - since_date: {since_date}, force_overwrite: {force_overwrite}, dry_run: {dry_run}, max_records: {max_records}")
        
        start_time = timezone.now()
        
        try:
            # Create sync record
            sync_record = self.create_sync_record({
                'since_date': since_date,
                'force_overwrite': force_overwrite,
                'dry_run': dry_run,
                'max_records': max_records
            })
            
            # Get records stream
            records_stream = self.client.stream_quotes(
                since_date=since_date,
                max_records=max_records
            )
            
            # Process stream
            stats = self.processor.process_stream(records_stream, dry_run=dry_run)
            
            # Update sync record
            self.complete_sync_record(sync_record, stats, start_time)
            
            logger.info(f"Streaming quotes sync completed successfully")
            
            return {
                'success': True,
                'total_processed': stats['total_processed'],
                'total_created': stats['total_created'],
                'total_updated': stats['total_updated'],
                'total_errors': stats['total_errors'],
                'pages_processed': stats['pages_processed'],
                'duration': (timezone.now() - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Streaming quotes sync failed: {e}")
            if 'sync_record' in locals():
                self.fail_sync_record(sync_record, str(e), start_time)
            
            return {
                'success': False,
                'error': str(e),
                'duration': (timezone.now() - start_time).total_seconds()
            }
    
    def create_sync_record(self, configuration: Dict[str, Any]) -> SyncHistory:
        """Create a new SyncHistory record"""
        return SyncHistory.objects.create(
            crm_source=self.crm_source,
            sync_type=self.entity_type,
            status='in_progress',
            start_time=timezone.now(),
            configuration=configuration
        )
    
    def complete_sync_record(self, sync_record: SyncHistory, stats: Dict[str, Any], start_time: datetime):
        """Complete sync record with success status"""
        sync_record.status = 'success'
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats['total_processed']
        sync_record.records_created = stats['total_created']
        sync_record.records_updated = stats['total_updated']
        sync_record.records_failed = stats['total_errors']
        sync_record.duration = (timezone.now() - start_time).total_seconds()
        sync_record.save()
    
    def fail_sync_record(self, sync_record: SyncHistory, error: str, start_time: datetime):
        """Complete sync record with failure status"""
        sync_record.status = 'failed'
        sync_record.end_time = timezone.now()
        sync_record.error_message = error[:1000]  # Truncate long errors
        sync_record.duration = (timezone.now() - start_time).total_seconds()
        sync_record.save()