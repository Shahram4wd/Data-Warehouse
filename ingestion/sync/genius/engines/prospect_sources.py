"""
Prospect Source sync engine for Genius CRM following CRM sync guide architecture
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.prospect_sources import GeniusProspectSourceClient
from ..processors.prospect_sources import GeniusProspectSourceProcessor

logger = logging.getLogger(__name__)


class GeniusProspectSourcesSyncEngine(GeniusBaseSyncEngine):
    """
    Sync engine for Genius Prospect Source data following established patterns.
    Uses client → processor architecture without config dependencies.
    """
    
    def __init__(self):
        super().__init__('prospect_sources')
        self.client = GeniusProspectSourceClient()
        
        # Import the model here to avoid circular imports
        from ingestion.models.genius import Genius_ProspectSource
        self.processor = GeniusProspectSourceProcessor(Genius_ProspectSource)
        
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
        """Execute the prospect sources sync process - adapter for standard sync interface"""
        
        # Determine since_date based on full flag
        since_date = None if full else since
        
        return await self.sync_prospect_sources(
            since_date=since_date, 
            force_overwrite=force,
            dry_run=dry_run, 
            max_records=max_records or 0
        )

    async def sync_prospect_sources(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for prospect sources with chunked processing for large datasets"""
        
        logger.info(f"Starting prospect sources sync - since_date: {since_date}, "
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
                raw_data = await sync_to_async(self.client.get_prospect_sources)(
                    since_date=since_date,
                    limit=max_records
                )
                
                if not raw_data:
                    logger.info("No prospect sources data retrieved")
                    return stats
                
                logger.info(f"Retrieved {len(raw_data)} prospect sources")
                
                if dry_run:
                    logger.info(f"DRY RUN: Would process {len(raw_data)} records")
                    stats['total_processed'] = len(raw_data)
                    return stats
                
                stats['total_processed'] = len(raw_data)
                
                # Process data using existing batch method
                batch_stats = await self._process_prospect_sources_batch(
                    raw_data, self.client.get_field_mapping(), force_overwrite
                )
                
                # Update stats
                stats.update(batch_stats)
                
            else:
                # For full sync (no max_records), use chunked processing to avoid memory issues
                logger.info(f"Starting chunked processing for full sync")
                
                if dry_run:
                    logger.info("DRY RUN: Would process all records using chunked processing")
                    # For dry run, just count first chunk
                    first_chunk = next(self.client.get_prospect_sources_chunked(since_date=since_date, chunk_size=100), [])
                    stats['total_processed'] = len(first_chunk) if first_chunk else 0
                    return stats
                
                chunk_num = 0
                total_processed = 0
                
                # Process each chunk separately to avoid loading everything into memory
                for chunk_data in self.client.get_prospect_sources_chunked(
                    since_date=since_date, 
                    chunk_size=self.DEFAULT_CHUNK_SIZE
                ):
                    if not chunk_data:
                        break
                    
                    chunk_num += 1
                    chunk_size_actual = len(chunk_data)
                    total_processed += chunk_size_actual
                    
                    logger.info(f"Processing chunk {chunk_num}: {chunk_size_actual} records "
                              f"(total processed so far: {total_processed})")
                    
                    # Process this chunk
                    chunk_stats = await self._process_prospect_sources_batch(
                        chunk_data, self.client.get_field_mapping(), force_overwrite
                    )
                    
                    # Update running totals
                    stats['created'] += chunk_stats['created']
                    stats['updated'] += chunk_stats['updated']
                    stats['total_processed'] = total_processed
                    
                    logger.info(f"Chunk {chunk_num} completed - Created: {chunk_stats['created']}, "
                              f"Updated: {chunk_stats['updated']}, "
                              f"Running totals: {stats['created']} created, {stats['updated']} updated")
            
        except Exception as e:
            logger.error(f"Error in sync_prospect_sources: {e}")
            stats['errors'] += 1
            raise
        
        logger.info(f"Prospect sources sync completed - Stats: {stats}")
        return stats

    @sync_to_async
    def _process_prospect_sources_batch(self, batch: List[tuple], field_mapping: List[str], 
                          force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of prospect source records"""
        
        # Validate and transform records
        validated_records = []
        for record_tuple in batch:
            try:
                record = self.processor.validate_record(record_tuple, field_mapping)
                if record:
                    validated_records.append(record)
            except Exception as e:
                logger.error(f"Error validating prospect source record: {e}")
                continue
        
        if not validated_records:
            logger.warning("No valid prospect source records to process")
            return {'created': 0, 'updated': 0}
        
        # Perform bulk upsert
        return self._bulk_upsert_records(validated_records, force_overwrite)

    def _bulk_upsert_records(self, validated_records: List[dict], force_overwrite: bool) -> Dict[str, int]:
        """Perform bulk upsert of prospect source records using modern bulk_create with update_conflicts"""
        
        from ingestion.models.genius import Genius_ProspectSource
        from django.db import transaction
        
        stats = {'created': 0, 'updated': 0}
        
        if not validated_records:
            return stats
        
        try:
            with transaction.atomic():
                # Process in batches
                batch_size = self.BATCH_SIZE
                total_batches = (len(validated_records) + batch_size - 1) // batch_size
                logger.info(f"Processing {len(validated_records)} prospect sources in {total_batches} batches of {batch_size}")
                
                for i in range(0, len(validated_records), batch_size):
                    batch_num = (i // batch_size) + 1
                    batch = validated_records[i:i + batch_size]
                    
                    logger.info(f"Processing batch {batch_num}/{total_batches}: records {i+1}-{min(i+batch_size, len(validated_records))}")
                    
                    # Prepare model instances
                    source_instances = []
                    for record in batch:
                        source_instances.append(Genius_ProspectSource(**record))
                    
                    # Bulk create with conflict resolution
                    update_fields = [
                        'prospect_id', 'marketing_source_id', 'source_date', 'notes', 
                        'add_user_id', 'add_date', 'updated_at'
                    ]
                    
                    created_sources = Genius_ProspectSource.objects.bulk_create(
                        source_instances,
                        update_conflicts=True,
                        update_fields=update_fields,
                        unique_fields=['id']
                    )
                    
                    # Count results
                    batch_created = sum(1 for s in created_sources if s._state.adding)
                    stats['created'] += batch_created
                    stats['updated'] += len(batch) - batch_created
                    
                    logger.info(f"Batch {batch_num} completed - Created: {batch_created}, "
                              f"Updated: {len(batch) - batch_created}, "
                              f"Total so far: {stats['created']} created, {stats['updated']} updated")
                
        except Exception as e:
            logger.error(f"Error in bulk upsert: {e}")
            raise
        
        logger.info(f"Bulk upsert completed - Created: {stats['created']}, "
                   f"Updated: {stats['updated']}")
        return stats

