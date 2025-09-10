"""
Refactored Lead sync engine for Genius CRM - Enterprise Architecture Compliant
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.leads import GeniusLeadClient
from ..services.leads import GeniusLeadService
from ..config.leads import GeniusLeadSyncConfig

logger = logging.getLogger(__name__)


class GeniusLeadsSyncEngine(GeniusBaseSyncEngine):
    """
    Lightweight sync engine for Genius lead data.
    Focuses on orchestration, delegates business logic to service layer.
    """
    
    def __init__(self):
        super().__init__('leads')
        self.client = GeniusLeadClient()
        self.service = GeniusLeadService()
        self.config = GeniusLeadSyncConfig()
    
    async def execute_sync(self, 
                          full: bool = False,
                          force: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the leads sync process - adapter for standard sync interface"""
        
        # Determine since_date based on full flag
        since_date = None if full else since
        
        return await self.sync_leads(
            since_date=since_date, 
            force_overwrite=force,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
    async def sync_leads(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """
        Main sync method for leads.
        Orchestrates the sync process using service layer for business logic.
        """
        logger.info(f"Starting leads sync - since_date: {since_date}, "
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
        
        # Configure chunk size
        chunk_size = self.config.DEFAULT_CHUNK_SIZE
        if max_records and max_records < chunk_size:
            chunk_size = max_records
        
        try:
            # Process data in chunks
            await self._process_chunks(
                since_date=since_date,
                chunk_size=chunk_size,
                max_records=max_records,
                force_overwrite=force_overwrite,
                dry_run=dry_run,
                stats=stats
            )
            
        except Exception as e:
            logger.error(f"Error in sync_leads: {e}")
            stats['errors'] += 1
            raise
        
        logger.info(f"Sync completed - Stats: {stats}")
        return stats
    
    async def _process_chunks(self, since_date, chunk_size, max_records, 
                            force_overwrite, dry_run, stats):
        """
        Process data in chunks.
        Lightweight orchestration method that delegates to service layer.
        """
        chunk_num = 0
        total_processed = 0
        
        # Use a sync function to iterate through chunks
        def get_chunks():
            nonlocal chunk_num
            
            for chunk in self.client.get_leads_chunked(
                since_date=since_date, 
                chunk_size=min(chunk_size, max_records) if max_records else chunk_size
            ):
                chunk_num += 1
                
                # Apply max_records limit if specified
                if max_records and total_processed >= max_records:
                    logger.info(f"Reached max_records limit of {max_records}, stopping")
                    break
                    
                # Trim chunk if it would exceed max_records
                if max_records and total_processed + len(chunk) > max_records:
                    remaining = max_records - total_processed
                    chunk = chunk[:remaining]
                    logger.info(f"Trimming chunk to {len(chunk)} records to respect max_records limit")
                
                yield chunk_num, chunk
                
                # If we trimmed the chunk, we're done
                if max_records and total_processed + len(chunk) >= max_records:
                    break
        
        # Process each chunk
        for chunk_num, chunk in await sync_to_async(list)(get_chunks()):
            logger.info(f"Processing chunk {chunk_num} with {len(chunk)} records")
            
            # Delegate chunk processing to service layer
            batch_stats = await self._process_chunk_with_service(
                chunk, force_overwrite, dry_run
            )
            
            # Update overall stats
            for key in stats:
                stats[key] += batch_stats[key]
            
            total_processed += len(chunk)
            
            logger.info(f"Completed chunk {chunk_num}. "
                       f"Batch stats: {batch_stats}. "
                       f"Total processed: {total_processed}")
    
    async def _process_chunk_with_service(self, chunk, force_overwrite, dry_run):
        """
        Process a single chunk using the service layer.
        Engine only handles coordination, service handles business logic.
        """
        stats = {
            'total_processed': len(chunk),
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(chunk)} records")
            return stats
        
        try:
            # Delegate validation and transformation to service
            processed_data = await sync_to_async(
                self.service.validate_and_transform_batch
            )(chunk)
            
            if not processed_data:
                logger.warning("No valid records to process in this chunk")
                stats['skipped'] = len(chunk)
                return stats
            
            # Delegate bulk operations to service
            operation_stats = await sync_to_async(
                self.service.bulk_upsert_records
            )(processed_data, force_overwrite)
            
            # Merge operation stats into chunk stats
            stats.update(operation_stats)
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            stats['errors'] = len(chunk)
            raise
        
        return stats
