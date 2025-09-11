"""
Jobs sync engine for Genius CRM data synchronization
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..clients.jobs import GeniusJobClient
from ..processors.jobs import GeniusJobProcessor

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
    
    def sync_jobs(self, since_date: Optional[datetime] = None, 
                 force_overwrite: bool = False, 
                 dry_run: bool = False,
                 max_records: Optional[int] = None) -> Dict[str, Any]:
        """
        Sync jobs data with chunked processing
        
        Args:
            since_date: Optional datetime to sync from (for delta updates)
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            max_records: Maximum number of records to process (for testing)
            
        Returns:
            Dictionary containing sync statistics
        """
        logger.info(f"Starting jobs sync - since_date: {since_date}, force_overwrite: {force_overwrite}, "
                   f"dry_run: {dry_run}, max_records: {max_records}")
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if max_records and max_records <= 10000:
            # For smaller datasets, use direct processing
            logger.info(f"Processing limited dataset: {max_records} records")
            jobs_data = self.client.get_jobs(since_date=since_date, limit=max_records)
            stats = self._process_jobs_batch(jobs_data, force_overwrite, dry_run, stats)
        else:
            # For larger datasets, use chunked processing
            stats = self._sync_chunked_jobs(since_date, force_overwrite, dry_run, max_records, stats)
        
        logger.info(f"Jobs sync completed - Stats: {stats}")
        return stats
    
    def _sync_chunked_jobs(self, since_date: Optional[datetime], force_overwrite: bool, 
                          dry_run: bool, max_records: Optional[int], 
                          stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process jobs data in chunks for large datasets"""
        
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
            chunk_data = self.client.get_chunked_jobs(offset, current_chunk_size, since_date)
            
            if not chunk_data:
                logger.info("No more data to process")
                break
                
            logger.info(f"Processing chunk {(offset // self.chunk_size) + 1}: "
                       f"{len(chunk_data)} records (total processed so far: {total_processed + len(chunk_data)})")
            
            # Process this chunk
            chunk_stats = self._process_jobs_batch(chunk_data, force_overwrite, dry_run, stats)
            
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
    
    def _process_jobs_batch(self, jobs_data: list, force_overwrite: bool, 
                           dry_run: bool, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Process a batch of jobs data using bulk operations"""
        
        if not jobs_data:
            return stats
            
        field_mapping = self.client.get_field_mapping()
        
        # Process in smaller batches for efficiency
        batch_count = (len(jobs_data) + self.batch_size - 1) // self.batch_size
        logger.info(f"Processing {len(jobs_data)} jobs in {batch_count} batches of {self.batch_size}")
        
        for i in range(0, len(jobs_data), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch_data = jobs_data[i:i + self.batch_size]
            
            logger.info(f"Processing batch {batch_num}/{batch_count}: records {i+1}-{min(i+self.batch_size, len(jobs_data))}")
            
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
