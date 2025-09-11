"""
MarketSharp Marketing Source Map sync engine for Genius CRM following CRM sync guide architecture
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.marketsharp_marketing_source_maps import GeniusMarketSharpMarketingSourceMapClient
from ..processors.marketsharp_marketing_source_maps import GeniusMarketSharpMarketingSourceMapProcessor

logger = logging.getLogger(__name__)


class GeniusMarketsharpMarketingSourceMapsSyncEngine(GeniusBaseSyncEngine):
    """
    Sync engine for Genius MarketSharp marketing source map data following established patterns.
    Uses client → processor architecture without config dependencies.
    """
    
    def __init__(self):
        super().__init__('marketsharp_marketing_source_maps')
        self.client = GeniusMarketSharpMarketingSourceMapClient()
        
        # Import the model here to avoid circular imports
        from ingestion.models.genius import Genius_MarketSharpMarketingSourceMap
        self.processor = GeniusMarketSharpMarketingSourceMapProcessor(Genius_MarketSharpMarketingSourceMap)
        
        # Configuration constants (no separate config class needed)
        self.DEFAULT_CHUNK_SIZE = 1000
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
        """Execute the marketsharp marketing source maps sync process - adapter for standard sync interface"""
        
        # Determine since_date based on full flag
        since_date = None if full else since
        
        return await self.sync_marketsharp_marketing_source_maps(
            since_date=since_date, 
            force_overwrite=force,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
    async def sync_marketsharp_marketing_source_maps(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for marketsharp marketing source maps with chunked processing for large datasets"""
        
        logger.info(f"Starting marketsharp marketing source maps sync - since_date: {since_date}, "
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
                raw_data = await sync_to_async(self.client.get_marketsharp_marketing_source_maps)(
                    since_date=since_date,
                    limit=max_records
                )
                
                if not raw_data:
                    logger.info("No marketsharp marketing source maps data retrieved")
                    return stats
                
                logger.info(f"Retrieved {len(raw_data)} marketsharp marketing source maps")
                
                if dry_run:
                    logger.info(f"DRY RUN: Would process {len(raw_data)} records")
                    stats['total_processed'] = len(raw_data)
                    return stats
                
                stats['total_processed'] = len(raw_data)
                
                # Process data using existing batch method
                batch_stats = await self._process_marketsharp_marketing_source_maps_batch(
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
                    first_chunk = next(self.client.get_marketsharp_marketing_source_maps_chunked(since_date=since_date, chunk_size=100), [])
                    stats['total_processed'] = len(first_chunk) if first_chunk else 0
                    return stats
                
                chunk_num = 0
                total_processed = 0
                
                # Process each chunk separately to avoid loading everything into memory
                for chunk_data in self.client.get_marketsharp_marketing_source_maps_chunked(
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
                    chunk_stats = await self._process_marketsharp_marketing_source_maps_batch(
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
            logger.error(f"Error in sync_marketsharp_marketing_source_maps: {e}")
            stats['errors'] += 1
            raise
        
        logger.info(f"MarketSharp marketing source maps sync completed - Stats: {stats}")
        return stats

    @sync_to_async
    def _process_marketsharp_marketing_source_maps_batch(self, batch: List[tuple], field_mapping: List[str], 
                          force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of marketsharp marketing source map records"""
        
        # Validate and transform records
        validated_records = []
        for record_tuple in batch:
            try:
                record = self.processor.validate_record(record_tuple, field_mapping)
                if record:
                    validated_records.append(record)
            except Exception as e:
                logger.error(f"Error validating marketsharp marketing source map record: {e}")
                continue
        
        if not validated_records:
            logger.warning("No valid marketsharp marketing source map records to process")
            return {'created': 0, 'updated': 0}
        
        # Perform bulk upsert
        return self._bulk_upsert_records(validated_records, force_overwrite)

    def _bulk_upsert_records(self, validated_records: List[dict], force_overwrite: bool) -> Dict[str, int]:
        """Perform bulk upsert of marketsharp marketing source map records using modern bulk_create with update_conflicts"""
        
        from ingestion.models.genius import Genius_MarketSharpMarketingSourceMap
        from django.db import transaction
        
        stats = {'created': 0, 'updated': 0}
        
        if not validated_records:
            return stats
        
        try:
            with transaction.atomic():
                # Process in batches
                batch_size = self.BATCH_SIZE
                total_batches = (len(validated_records) + batch_size - 1) // batch_size
                logger.info(f"Processing {len(validated_records)} marketsharp marketing source maps in {total_batches} batches of {batch_size}")
                
                for i in range(0, len(validated_records), batch_size):
                    batch_num = (i // batch_size) + 1
                    batch = validated_records[i:i + batch_size]
                    
                    logger.info(f"Processing batch {batch_num}/{total_batches}: records {i+1}-{min(i+batch_size, len(validated_records))}")
                    
                    # Prepare model instances
                    map_instances = []
                    for record in batch:
                        map_instances.append(Genius_MarketSharpMarketingSourceMap(**record))
                    
                    # Bulk create with conflict resolution
                    update_fields = [
                        'marketing_source_id', 'created_at', 'updated_at'
                    ]
                    
                    created_maps = Genius_MarketSharpMarketingSourceMap.objects.bulk_create(
                        map_instances,
                        update_conflicts=True,
                        update_fields=update_fields,
                        unique_fields=['marketsharp_id']
                    )
                    
                    # Count results
                    batch_created = sum(1 for m in created_maps if m._state.adding)
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
