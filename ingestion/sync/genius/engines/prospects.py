"""
Prospects sync engine for Genius CRM following CRM sync guide architecture
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.prospects import GeniusProspectsClient
from ..processors.prospects import GeniusProspectsProcessor

logger = logging.getLogger(__name__)


class GeniusProspectsSyncEngine(GeniusBaseSyncEngine):
    """
    Sync engine for Genius Prospects data following established patterns.
    Uses client → processor architecture with chunked processing for large datasets.
    """
    
    def __init__(self):
        super().__init__('prospects')
        self.client = GeniusProspectsClient()
        
        # Import the model here to avoid circular imports
        from ingestion.models.genius import Genius_Prospect
        self.processor = GeniusProspectsProcessor(Genius_Prospect)
        
        # Configuration constants (no separate config class needed)
        self.DEFAULT_CHUNK_SIZE = 100000
        self.BATCH_SIZE = 500
    
    async def execute_sync(self, 
                          full: bool = False,
                          force: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the prospects sync process - adapter for standard sync interface"""
        
        # Determine since_date based on full flag
        since_date = None if full else since
        
        return await self.sync_prospects(
            since_date=since_date, 
            force_overwrite=force,
            dry_run=dry_run, 
            max_records=max_records or 0
        )

    async def sync_prospects(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for prospects with chunked processing for large datasets"""
        
        logger.info(f"Starting prospects sync - since_date: {since_date}, "
                   f"force_overwrite: {force_overwrite}, dry_run: {dry_run}, "
                   f"max_records: {max_records}")
        
        # Initialize stats
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        try:
            if max_records and max_records > 0:
                # For limited records, use the old method (load all at once)
                logger.info(f"Processing limited dataset: {max_records} records")
                raw_data = await sync_to_async(self.client.get_prospects)(
                    since_date=since_date,
                    limit=max_records
                )
                
                if not raw_data:
                    logger.info("No prospects data retrieved")
                    return stats
                
                logger.info(f"Retrieved {len(raw_data)} prospects")
                
                if dry_run:
                    logger.info(f"DRY RUN: Would process {len(raw_data)} records")
                    stats['total_processed'] = len(raw_data)
                    return stats
                
                stats['total_processed'] = len(raw_data)
                
                # Process data using existing batch method
                batch_stats = await self._process_prospects_batch(
                    raw_data, self.client.get_field_mapping(), force_overwrite
                )
                
                # Update stats
                stats.update(batch_stats)
                
            else:
                # For unlimited records, use chunked processing 
                logger.info("Processing full dataset with chunked approach")
                offset = 0
                chunk_number = 1
                
                while True:
                    logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {self.DEFAULT_CHUNK_SIZE}):")
                    logger.info(f"            {self.client.get_chunked_query(offset, self.DEFAULT_CHUNK_SIZE, since_date)}")
                    
                    chunk_data = await sync_to_async(self.client.get_chunked_prospects)(
                        offset=offset, 
                        chunk_size=self.DEFAULT_CHUNK_SIZE,
                        since_date=since_date
                    )
                    
                    if not chunk_data:
                        logger.info("No more data to process")
                        break
                    
                    chunk_size = len(chunk_data)
                    total_processed_so_far = stats['total_processed'] + chunk_size
                    logger.info(f"Processing chunk {chunk_number}: {chunk_size} records (total processed so far: {total_processed_so_far})")
                    
                    if dry_run:
                        logger.info(f"DRY RUN: Would process chunk of {chunk_size} records")
                        stats['total_processed'] += chunk_size
                    else:
                        # Process this chunk
                        chunk_stats = await self._process_prospects_batch(
                            chunk_data, self.client.get_field_mapping(), force_overwrite
                        )
                        
                        # Update running totals
                        stats['total_processed'] += chunk_stats['total_processed']
                        stats['created'] += chunk_stats['created'] 
                        stats['updated'] += chunk_stats['updated']
                        stats['skipped'] += chunk_stats['skipped']
                        stats['errors'] += chunk_stats['errors']
                        
                        logger.info(f"Chunk {chunk_number} completed - Created: {chunk_stats['created']}, "
                                  f"Updated: {chunk_stats['updated']}, Running totals: "
                                  f"{stats['created']} created, {stats['updated']} updated")
                    
                    # Move to next chunk
                    offset += self.DEFAULT_CHUNK_SIZE
                    chunk_number += 1
                    
                    # If we got less than the full chunk size, we're done
                    if chunk_size < self.DEFAULT_CHUNK_SIZE:
                        break
            
            logger.info(f"Prospects sync completed - Stats: {stats}")
            
            # Add sync_history_id for command compatibility
            stats['sync_history_id'] = None
            return stats
            
        except Exception as e:
            logger.error(f"Prospects sync failed: {e}", exc_info=True)
            raise

    async def _process_prospects_batch(self, raw_data: List[tuple], field_mapping: List[str], 
                                      force_overwrite: bool) -> Dict[str, int]:
        """Process a batch of prospects data with bulk operations"""
        
        logger.info(f"Processing {len(raw_data)} prospects in {len(raw_data) // self.BATCH_SIZE + 1} batches of {self.BATCH_SIZE}")
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        # Process in smaller batches for bulk operations
        for i in range(0, len(raw_data), self.BATCH_SIZE):
            batch_number = i // self.BATCH_SIZE + 1
            batch_start = i + 1
            batch_end = min(i + self.BATCH_SIZE, len(raw_data))
            batch = raw_data[i:i + self.BATCH_SIZE]
            
            logger.info(f"Processing batch {batch_number}/{len(raw_data) // self.BATCH_SIZE + 1}: records {batch_start}-{batch_end}")
            
            # Process batch using the processor
            batch_stats = await self.processor.process_batch(
                batch, field_mapping, force_overwrite
            )
            
            # Accumulate stats
            stats['total_processed'] += batch_stats['total_processed']
            stats['created'] += batch_stats['created']
            stats['updated'] += batch_stats['updated']
            stats['skipped'] += batch_stats['skipped']
            stats['errors'] += batch_stats['errors']
            
            logger.info(f"Batch {batch_number} completed - Created: {batch_stats['created']}, "
                       f"Updated: {batch_stats['updated']}, Total so far: "
                       f"{stats['created']} created, {stats['updated']} updated")
        
        logger.info(f"Bulk upsert completed - Created: {stats['created']}, Updated: {stats['updated']}")
        
        return stats
