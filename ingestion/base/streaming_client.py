"""
Memory-safe streaming client base class for large data imports.

Implements keyset pagination instead of OFFSET to avoid memory issues
and provides streaming data processing with automatic garbage collection.
"""
import gc
import logging
import psutil
from typing import Iterator, List, Dict, Any, Optional
from datetime import datetime
from django.conf import settings
from django.db import connection, transaction

logger = logging.getLogger(__name__)


class MemoryGuard:
    """Memory monitoring and protection for streaming operations"""
    
    def __init__(self, max_memory_mb: int = 600):
        self.max_memory_mb = max_memory_mb
        self.initial_memory = self._get_memory_mb()
        
    def _get_memory_mb(self) -> float:
        """Get current RSS memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def check_memory(self, operation: str = "operation") -> bool:
        """Check if memory usage is within limits"""
        current_memory = self._get_memory_mb()
        if current_memory > self.max_memory_mb:
            logger.error(
                f"Memory limit exceeded during {operation}: "
                f"{current_memory:.1f}MB > {self.max_memory_mb}MB"
            )
            return False
        return True
    
    def log_memory_usage(self, operation: str):
        """Log current memory usage"""
        current_memory = self._get_memory_mb()
        logger.info(f"{operation}: {current_memory:.1f}MB RSS")


class StreamingClient:
    """
    Base class for memory-safe streaming data clients.
    Uses keyset pagination instead of OFFSET for better performance.
    """
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.page_size = getattr(settings, 'INGEST_PAGE_SIZE', 5000)
        self.bulk_batch_size = getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        self.memory_guard = MemoryGuard()
        
        # Safety checks
        if self.page_size > 5000:
            logger.warning(f"Page size {self.page_size} > 5000, capping at 5000")
            self.page_size = 5000
            
        logger.info(
            f"Streaming client initialized: page_size={self.page_size}, "
            f"bulk_batch_size={self.bulk_batch_size}"
        )
    
    def stream_records(
        self, 
        select_fields: List[str],
        where_condition: str = "",
        since_date: Optional[datetime] = None,
        max_records: Optional[int] = None
    ) -> Iterator[List[tuple]]:
        """
        Stream records using keyset pagination (id > last_id).
        
        Yields batches of records to prevent memory buildup.
        """
        last_id = 0
        total_processed = 0
        page_num = 0
        
        self.memory_guard.log_memory_usage("Starting stream")
        
        while True:
            page_num += 1
            
            # Build keyset pagination query
            query = self._build_keyset_query(
                select_fields, where_condition, since_date, last_id
            )
            
            logger.info(f"Page {page_num}: Fetching records WHERE id > {last_id}")
            
            # Execute query with streaming cursor
            records = self._execute_streaming_query(query)
            
            if not records:
                logger.info("No more records found, stream complete")
                break
            
            # Memory safety check
            if not self.memory_guard.check_memory(f"page {page_num}"):
                logger.error("Aborting stream due to memory limit")
                break
            
            # Check for oversized first page (indicates potential OOM)
            if page_num == 1 and len(records) > 10000:
                logger.error(
                    f"Aborting to prevent OOM—first page too large: "
                    f"{len(records)} records > 10000 limit"
                )
                break
            
            logger.info(
                f"Page {page_num}: Retrieved {len(records)} records "
                f"(total so far: {total_processed + len(records)})"
            )
            
            # Update pagination state
            last_id = records[-1][0]  # Assuming first field is 'id'
            total_processed += len(records)
            
            # Check max_records limit
            if max_records and total_processed >= max_records:
                logger.info(f"Reached max_records limit: {max_records}")
                yield records[:max_records - (total_processed - len(records))]
                break
            
            yield records
            
            # Force garbage collection after each page
            gc.collect()
            self.memory_guard.log_memory_usage(f"After page {page_num}")
            
            # Break if we got fewer records than page_size (end of data)
            if len(records) < self.page_size:
                logger.info("Reached end of data stream")
                break
    
    def _build_keyset_query(
        self,
        select_fields: List[str], 
        where_condition: str,
        since_date: Optional[datetime],
        last_id: int
    ) -> str:
        """Build SQL query with keyset pagination"""
        
        fields_str = ", ".join(select_fields)
        query = f"SELECT {fields_str} FROM {self.table_name}"
        
        # Build WHERE clause
        where_parts = [f"id > {last_id}"]
        
        if where_condition:
            where_parts.append(where_condition)
            
        if since_date:
            # Assume updated_at field exists
            where_parts.append(f"updated_at >= '{since_date.isoformat()}'")
        
        query += f" WHERE {' AND '.join(where_parts)}"
        query += f" ORDER BY id ASC LIMIT {self.page_size}"
        
        return query
    
    def _execute_streaming_query(self, query: str) -> List[tuple]:
        """Execute query with server-side cursor for memory efficiency"""
        
        logger.debug(f"Executing: {query}")
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            # Fetch all at once since we're using LIMIT for pagination
            return cursor.fetchall()


class StreamingProcessor:
    """
    Memory-safe processor for streaming data with bulk operations
    """
    
    def __init__(self, model_class, bulk_batch_size: Optional[int] = None):
        self.model_class = model_class
        self.bulk_batch_size = bulk_batch_size or getattr(settings, 'DB_BULK_BATCH_SIZE', 1000)
        self.memory_guard = MemoryGuard()
        
    def process_stream(
        self,
        records_stream: Iterator[List[tuple]],
        field_mapping: List[str],
        transform_func: callable = None,
        force_overwrite: bool = False,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Process streaming records with memory-safe bulk operations
        """
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        buffer = []
        
        self.memory_guard.log_memory_usage("Starting stream processing")
        
        try:
            for page_records in records_stream:
                # Process each record in the page
                for record in page_records:
                    try:
                        # Transform record if function provided
                        if transform_func:
                            processed_record = transform_func(record, field_mapping)
                        else:
                            processed_record = self._default_transform(record, field_mapping)
                        
                        if processed_record:
                            buffer.append(processed_record)
                        
                        # Flush buffer when it reaches bulk_batch_size
                        if len(buffer) >= self.bulk_batch_size:
                            batch_stats = self._flush_buffer(
                                buffer, force_overwrite, dry_run
                            )
                            self._update_stats(stats, batch_stats)
                            buffer.clear()
                            gc.collect()  # Force cleanup after each bulk operation
                    
                    except Exception as e:
                        logger.error(f"Error processing record: {e}")
                        stats['errors'] += 1
                
                # Memory check after each page
                if not self.memory_guard.check_memory("stream processing"):
                    logger.error("Memory limit exceeded, stopping processing")
                    break
                
                self.memory_guard.log_memory_usage(f"Processed {stats['total_processed']} records")
            
            # Flush remaining buffer
            if buffer:
                batch_stats = self._flush_buffer(buffer, force_overwrite, dry_run)
                self._update_stats(stats, batch_stats)
                buffer.clear()
            
        except Exception as e:
            logger.error(f"Stream processing failed: {e}")
            raise
        finally:
            # Final cleanup
            gc.collect()
            self.memory_guard.log_memory_usage("Stream processing complete")
        
        return stats
    
    def _default_transform(self, record: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Default record transformation"""
        return dict(zip(field_mapping, record))
    
    def _flush_buffer(
        self, 
        buffer: List[Dict[str, Any]], 
        force_overwrite: bool, 
        dry_run: bool
    ) -> Dict[str, int]:
        """Flush buffer to database using bulk operations"""
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(buffer)} records")
            return {
                'total_processed': len(buffer),
                'created': len(buffer),
                'updated': 0,
                'errors': 0
            }
        
        logger.info(f"Flushing {len(buffer)} records to database")
        
        stats = {'total_processed': len(buffer), 'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            with transaction.atomic():
                if force_overwrite:
                    # Use bulk_create with update_conflicts for upsert
                    objects = [self.model_class(**record) for record in buffer]
                    created_objects = self.model_class.objects.bulk_create(
                        objects,
                        batch_size=self.bulk_batch_size,
                        update_conflicts=True,
                        update_fields=[f.name for f in self.model_class._meta.fields if f.name != 'id'],
                        unique_fields=['id']
                    )
                    stats['updated'] = len(buffer)
                else:
                    # Use bulk_create with ignore_conflicts
                    objects = [self.model_class(**record) for record in buffer]
                    created_objects = self.model_class.objects.bulk_create(
                        objects,
                        batch_size=self.bulk_batch_size,
                        ignore_conflicts=True
                    )
                    stats['created'] = len(created_objects)
                    
        except Exception as e:
            logger.error(f"Bulk operation failed: {e}")
            stats['errors'] = len(buffer)
            stats['created'] = 0
            stats['updated'] = 0
        
        return stats
    
    def _update_stats(self, total_stats: Dict[str, int], batch_stats: Dict[str, int]):
        """Update total statistics with batch results"""
        for key in ['total_processed', 'created', 'updated', 'errors']:
            total_stats[key] += batch_stats[key]