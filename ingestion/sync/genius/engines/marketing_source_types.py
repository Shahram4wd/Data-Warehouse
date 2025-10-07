"""
Marketing Source Types sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.marketing_source_types import GeniusMarketingSourceTypeClient
from ..processors.marketing_source_types import GeniusMarketingSourceTypeProcessor
from ingestion.models import Genius_MarketingSourceType, SyncHistory

logger = logging.getLogger(__name__)


class GeniusMarketingSourceTypesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius marketing source type data"""
    
    def __init__(self):
        super().__init__('marketing_source_types')
        self.client = GeniusMarketingSourceTypeClient()
        self.processor = GeniusMarketingSourceTypeProcessor(Genius_MarketingSourceType)
        
        # Configuration constants (no separate config class needed)
        self.DEFAULT_CHUNK_SIZE = 1000
        self.BATCH_SIZE = 500

    @sync_to_async
    def get_last_sync_timestamp(self):
        """Get the timestamp of the last successful sync from SyncHistory table"""
        try:
            latest_sync = SyncHistory.objects.filter(
                crm_source='genius',
                sync_type='marketing_source_types',
                status__in=['success', 'completed'],
                end_time__isnull=False
            ).order_by('-end_time').first()
            
            if latest_sync and latest_sync.end_time:
                logger.info(f"Last successful sync completed at: {latest_sync.end_time}")
                return latest_sync.end_time
            else:
                logger.info("No previous successful sync found")
                return None
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None

    @sync_to_async
    def _create_sync_record(self, sync_mode: str, since_date: Optional[datetime] = None, 
                           max_records: Optional[int] = None) -> SyncHistory:
        """Create a new SyncHistory record for this sync operation"""
        sync_record = SyncHistory.objects.create(
            crm_source='genius',
            sync_type='marketing_source_types',
            status='running',
            start_time=timezone.now(),
            configuration={
                'sync_mode': sync_mode,
                'since_date': since_date.isoformat() if since_date else None,
                'max_records': max_records
            }
        )
        logger.info(f"Created sync history record: {sync_record.id}")
        return sync_record

    @sync_to_async  
    def _complete_sync_record_async(self, sync_record: SyncHistory, stats: Dict[str, Any], 
                                   status: str = 'success'):
        """Complete the sync record with final stats and status"""
        sync_record.status = status
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('total_processed', 0)
        sync_record.records_created = stats.get('created', 0)
        sync_record.records_updated = stats.get('updated', 0)
        sync_record.records_failed = stats.get('errors', 0)
        
        # Calculate duration
        if sync_record.start_time:
            duration = sync_record.end_time - sync_record.start_time
            sync_record.performance_metrics = {
                'duration_seconds': duration.total_seconds()
            }
        
        sync_record.save()
        logger.info(f"Completed sync history record {sync_record.id}: {status}")
        return sync_record

    async def execute_sync_with_history(self, sync_mode: str = 'incremental', 
                                       since_date: Optional[datetime] = None,
                                       max_records: Optional[int] = None,
                                       dry_run: bool = False,
                                       **kwargs) -> Dict[str, Any]:
        """Execute sync with proper SyncHistory tracking"""
        
        # If since_date not provided and mode is incremental, get from last sync
        if sync_mode == 'incremental' and since_date is None:
            since_date = await self.get_last_sync_timestamp()
        
        # Create sync record (unless dry run)
        sync_record = None
        if not dry_run:
            sync_record = await self._create_sync_record(sync_mode, since_date, max_records)
        
        try:
            # Execute the actual sync
            stats = await self.sync_marketing_source_types_async(
                since_date=since_date,
                force_overwrite=(sync_mode == 'force'),
                dry_run=dry_run,
                max_records=max_records or 0,
                **kwargs
            )
            
            # Complete sync record on success
            if sync_record:
                await self._complete_sync_record_async(sync_record, stats, 'success')
            
            return stats
            
        except Exception as e:
            # Mark sync record as failed
            if sync_record:
                error_stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 1}
                await self._complete_sync_record_async(sync_record, error_stats, 'failed')
            
            logger.error(f"Sync failed: {e}")
            raise
    
    def sync_marketing_source_types(self, 
                                   sync_mode: str = 'incremental',
                                   batch_size: int = 500,
                                   max_records: Optional[int] = None,
                                   dry_run: bool = False,
                                   debug: bool = False,
                                   skip_validation: bool = False,
                                   start_date: Optional[datetime] = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Synchronous wrapper for async sync method - compatible with CRM sync guide patterns
        """
        import asyncio
        
        # Use the new execute_sync_with_history method for proper SyncHistory tracking
        sync_params = {
            'sync_mode': sync_mode,
            'since_date': start_date,  # Use start_date parameter directly 
            'max_records': max_records,
            'dry_run': dry_run,
            **kwargs
        }
        
        # Run the async method synchronously
        try:
            return asyncio.run(self.execute_sync_with_history(**sync_params))
        except RuntimeError as e:
            if "asyncio.run() cannot be called from a running event loop" in str(e):
                # Already in an event loop, use different approach
                import asyncio
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self.execute_sync_with_history(**sync_params))
            else:
                raise
    
    async def execute_sync(self, 
                          full: bool = False,
                          force: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the marketing source types sync process"""
        
        # Determine since_date based on full flag  
        since_date = None if full else since
        
        return await self.sync_marketing_source_types_async(
            since_date=since_date, 
            force_overwrite=force,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
    async def sync_marketing_source_types_async(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for marketing source types with chunked processing for large datasets"""
        
        logger.info(f"Starting marketing source types sync - since_date: {since_date}, "
                   f"force_overwrite: {force_overwrite}, dry_run: {dry_run}, "
                   f"max_records: {max_records}")
        
        # Initialize stats with proper error tracking
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
                raw_data = self.client.get_marketing_source_types(since_date, max_records)
                
                if not raw_data:
                    logger.info("No marketing source types data to process")
                    return stats
                
                logger.info(f"Retrieved {len(raw_data)} marketing source types")
                
                if dry_run:
                    logger.info("DRY RUN: Would process marketing source types data")
                    stats['total_processed'] = len(raw_data)
                    return stats
                
                stats['total_processed'] = len(raw_data)
                
                # Process data using existing batch method
                batch_stats = await self._process_marketing_source_type_batch(
                    raw_data, self.client.get_field_mapping(), force_overwrite
                )
                
                # Update stats properly
                stats['created'] = batch_stats.get('created', 0)
                stats['updated'] = batch_stats.get('updated', 0)
                # Preserve any errors from batch processing
                stats['errors'] = batch_stats.get('errors', 0)
                
            else:
                # For full sync (no max_records), use chunked processing to avoid memory issues
                logger.info(f"Starting chunked processing for full sync")
                
                if dry_run:
                    logger.info("DRY RUN: Would process all records using chunked processing")
                    # For dry run, just count first chunk
                    first_chunk = next(self.client.get_marketing_source_types_chunked(since_date=since_date, chunk_size=100), [])
                    stats['total_processed'] = len(first_chunk) if first_chunk else 0
                    return stats
                
                chunk_num = 0
                total_processed = 0
                
                # Process each chunk separately to avoid loading everything into memory
                for chunk_data in self.client.get_marketing_source_types_chunked(
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
                    
                    try:
                        # Process this chunk
                        chunk_stats = await self._process_marketing_source_type_batch(
                            chunk_data, self.client.get_field_mapping(), force_overwrite
                        )
                        
                        # Update running totals
                        stats['created'] += chunk_stats.get('created', 0)
                        stats['updated'] += chunk_stats.get('updated', 0)
                        stats['errors'] += chunk_stats.get('errors', 0)
                        stats['total_processed'] = total_processed
                        
                        logger.info(f"Chunk {chunk_num} completed - Created: {chunk_stats.get('created', 0)}, "
                                  f"Updated: {chunk_stats.get('updated', 0)}, "
                                  f"Errors: {chunk_stats.get('errors', 0)}, "
                                  f"Running totals: {stats['created']} created, {stats['updated']} updated, {stats['errors']} errors")
                    
                    except Exception as chunk_error:
                        logger.error(f"Error processing chunk {chunk_num}: {chunk_error}")
                        stats['errors'] += chunk_size_actual  # Count entire chunk as errors
                        stats['total_processed'] = total_processed  # Still count as processed
                        # Continue with next chunk rather than failing entirely
            
        except Exception as e:
            logger.error(f"Error in sync_marketing_source_types_async: {e}")
            stats['errors'] += 1
            # Re-raise to let the caller handle it
            raise
        
        logger.info(f"Marketing source types sync completed - Stats: {stats}")
        return stats
    
    @sync_to_async
    def _process_marketing_source_type_batch(self, batch: List[tuple], field_mapping: List[str], 
                          force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of marketing source type records"""
        
        # Validate and transform records
        validated_records = []
        error_count = 0
        
        for record_tuple in batch:
            try:
                record = self.processor.validate_record(record_tuple, field_mapping)
                if record:
                    validated_records.append(record)
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Error validating marketing source type record: {e}")
                error_count += 1
                continue
        
        if not validated_records:
            logger.warning("No valid marketing source type records to process")
            return {'created': 0, 'updated': 0, 'errors': error_count}
        
        # Perform bulk upsert
        bulk_stats = self._bulk_upsert_records(validated_records, force_overwrite)
        
        # Add error count to stats
        bulk_stats['errors'] = error_count
        
        return bulk_stats
    
    def _bulk_upsert_records(self, validated_records: List[dict], force_overwrite: bool) -> Dict[str, int]:
        """Perform bulk upsert of marketing source type records using modern bulk_create with update_conflicts"""
        
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        if not validated_records:
            return stats
        
        try:
            with transaction.atomic():
                # Process in batches
                batch_size = self.BATCH_SIZE
                total_batches = (len(validated_records) + batch_size - 1) // batch_size
                logger.info(f"Processing {len(validated_records)} marketing source types in {total_batches} batches of {batch_size}")
                
                for i in range(0, len(validated_records), batch_size):
                    batch_num = (i // batch_size) + 1
                    batch = validated_records[i:i + batch_size]
                    
                    logger.info(f"Processing batch {batch_num}/{total_batches}: records {i+1}-{min(i+batch_size, len(validated_records))}")
                    
                    try:
                        # Prepare model instances for this batch
                        source_type_instances = []
                        for record_data in batch:
                            # Handle NULL updated_at with current timestamp workaround
                            if record_data.get('updated_at') is None:
                                record_data['updated_at'] = timezone.now()
                            
                            try:
                                source_type_instances.append(Genius_MarketingSourceType(**record_data))
                            except Exception as e:
                                logger.error(f"Error creating MarketingSourceType object for id {record_data.get('id')}: {e}")
                                stats['errors'] += 1
                                continue
                        
                        if not source_type_instances:
                            logger.warning(f"No valid MarketingSourceType objects in batch {batch_num}")
                            stats['errors'] += len(batch)
                            continue
                        
                        # Perform bulk upsert for this batch
                        if force_overwrite:
                            # Force mode: update all fields
                            update_fields = ['label', 'description', 'is_active', 'list_order',
                                           'created_at', 'updated_at', 'sync_updated_at']
                        else:
                            # Normal mode: update selective fields
                            update_fields = ['updated_at', 'sync_updated_at', 'label', 'description', 
                                           'is_active', 'list_order', 'created_at']
                        
                        # Bulk create with conflict resolution
                        created_source_types = Genius_MarketingSourceType.objects.bulk_create(
                            source_type_instances,
                            update_conflicts=True,
                            update_fields=update_fields,
                            unique_fields=['id']
                        )
                        
                        # Count results
                        batch_created = sum(1 for st in created_source_types if st._state.adding)
                        stats['created'] += batch_created
                        stats['updated'] += len(source_type_instances) - batch_created
                        
                        logger.info(f"Batch {batch_num} completed - Created: {batch_created}, "
                                  f"Updated: {len(source_type_instances) - batch_created}, "
                                  f"Total so far: {stats['created']} created, {stats['updated']} updated, {stats['errors']} errors")
                    
                    except Exception as batch_error:
                        logger.error(f"Error processing batch {batch_num}: {batch_error}")
                        stats['errors'] += len(batch)  # Count entire batch as errors
                        # Continue with next batch rather than failing entirely
                              
        except Exception as e:
            logger.error(f"Error in bulk_upsert_records: {e}")
            stats['errors'] += len(validated_records)
            raise
        
        logger.info(f"Bulk upsert completed - Created: {stats['created']}, "
                   f"Updated: {stats['updated']}, Errors: {stats['errors']}")
        return stats

