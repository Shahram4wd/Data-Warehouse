"""
Marketing Sources sync engine for Genius CRM following CRM sync guide architecture
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.marketing_sources import GeniusMarketingSourceClient
from ..processors.marketing_sources import GeniusMarketingSourceProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)


class GeniusMarketingSourcesSyncEngine(GeniusBaseSyncEngine):
    """
    Sync engine for Genius marketing source data following CRM sync guide standards.
    MANDATORY: Uses SyncHistory table for tracking as required by CRM sync guide.
    """
    
    def __init__(self):
        super().__init__('marketing_sources')  # This sets crm_source='genius', sync_type='marketing_sources'
        self.client = GeniusMarketingSourceClient()
        
        # Import the model here to avoid circular imports
        from ingestion.models.genius import Genius_MarketingSource
        self.processor = GeniusMarketingSourceProcessor(Genius_MarketingSource)
        
        # Configuration constants (no separate config class needed)
        self.DEFAULT_CHUNK_SIZE = 1000
        self.BATCH_SIZE = 500

    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """MANDATORY: Get last successful sync timestamp from SyncHistory table"""
        try:
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='genius',                    # EXACT: CRM source name
                    sync_type='marketing_sources',          # EXACT: Entity type
                    status__in=['success', 'partial'],      # Only successful syncs
                    end_time__isnull=False                  # Only completed syncs
                ).order_by('-end_time').first()

                return last_sync.end_time if last_sync else None

            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None

    @sync_to_async
    def _create_sync_record_async(self, configuration: Dict[str, Any]) -> SyncHistory:
        """Create SyncHistory record asynchronously"""
        return SyncHistory.objects.create(
            crm_source='genius',
            sync_type='marketing_sources',
            status='running',
            start_time=timezone.now(),
            configuration=configuration
        )

    @sync_to_async
    def _complete_sync_record_async(self, sync_record: SyncHistory, stats: Dict[str, int], 
                                   error_message: str = None) -> None:
        """Complete sync record asynchronously using proper status logic"""
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('total_processed', 0)
        sync_record.records_created = stats.get('created', 0)
        sync_record.records_updated = stats.get('updated', 0)
        sync_record.records_failed = stats.get('errors', 0)
        
        if error_message:
            sync_record.status = 'failed'
            sync_record.error_message = error_message
        else:
            # CRITICAL: Use 'success' not 'completed'
            sync_record.status = 'success' if stats.get('errors', 0) == 0 else 'partial'
        
        # Calculate performance metrics
        duration = (sync_record.end_time - sync_record.start_time).total_seconds()
        total_processed = stats.get('total_processed', 0)
        success_rate = ((total_processed - stats.get('errors', 0)) / total_processed) if total_processed > 0 else 0
        
        sync_record.performance_metrics = {
            'duration_seconds': duration,
            'records_per_second': total_processed / duration if duration > 0 else 0,
            'success_rate': success_rate,
            'batch_size': self.BATCH_SIZE,
            'chunk_size': self.DEFAULT_CHUNK_SIZE
        }
        
        sync_record.save()
    
    def sync_marketing_sources(self, 
                              sync_mode: str = 'incremental',
                              batch_size: int = 500,
                              max_records: Optional[int] = None,
                              dry_run: bool = False,
                              debug: bool = False,
                              skip_validation: bool = False,
                              start_date: Optional[datetime] = None,
                              **kwargs) -> Dict[str, Any]:
        """
        MANDATORY: Synchronous wrapper following CRM sync guide patterns with SyncHistory integration
        """
        import asyncio
        
        # Map sync_mode to existing parameters following CRM sync guide
        # 1. Incremental Sync (Default): Only fetch records modified since last successful sync
        # 2. Full Sync: Fetch all records but respect local timestamps for updates  
        # 3. Force Overwrite: Fetch all records and completely replace local data
        force_overwrite = (sync_mode == 'force')
        full_sync = (sync_mode == 'full')
        
        # Prepare configuration for SyncHistory tracking
        configuration = {
            'sync_mode': sync_mode,
            'batch_size': batch_size,
            'max_records': max_records,
            'dry_run': dry_run,
            'debug': debug,
            'skip_validation': skip_validation,
            'start_date': start_date.isoformat() if start_date else None,
            **kwargs
        }
        
        # Set up parameters for async method
        sync_params = {
            'since_date': start_date,
            'force_overwrite': force_overwrite,
            'full_sync': full_sync,
            'dry_run': dry_run,
            'max_records': max_records or 0,
            'configuration': configuration,
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

    async def execute_sync_with_history(self, 
                                      since_date: Optional[datetime] = None,
                                      force_overwrite: bool = False,
                                      full_sync: bool = False,
                                      dry_run: bool = False,
                                      max_records: int = 0,
                                      configuration: Dict[str, Any] = None,
                                      **kwargs) -> Dict[str, Any]:
        """
        MANDATORY: Execute sync with proper SyncHistory tracking as required by CRM sync guide
        """
        
        # Step 1: Create SyncHistory record at start
        sync_record = await self._create_sync_record_async(configuration or {})
        
        stats = {
            'sync_record_id': sync_record.id,  # Return this for command display
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Step 2: Determine sync strategy based on CRM sync guide patterns
            effective_since_date = None
            
            if full_sync:
                # Full Sync: Fetch all records but respect local timestamps for updates
                effective_since_date = None
                logger.info("FULL SYNC: Fetching all records (ignoring last sync timestamp)")
            elif since_date:
                # Manual start date provided
                effective_since_date = since_date
                logger.info(f"MANUAL SYNC: Using provided start date: {since_date}")
            else:
                # Incremental Sync (Default): Only fetch records modified since last successful sync
                effective_since_date = await self.get_last_sync_timestamp()
                if effective_since_date:
                    logger.info(f"INCREMENTAL SYNC: Using last sync timestamp: {effective_since_date}")
                else:
                    logger.info("INITIAL SYNC: No previous sync found, fetching all records")
            
            # Step 3: Execute the actual sync
            sync_stats = await self.sync_marketing_sources_async(
                since_date=effective_since_date,
                force_overwrite=force_overwrite,
                dry_run=dry_run,
                max_records=max_records,
                **kwargs
            )
            
            # Update stats with sync results
            stats.update(sync_stats)
            
            # Step 4: Complete SyncHistory record with success
            error_message = None if stats['errors'] == 0 else f"{stats['errors']} errors occurred"
            await self._complete_sync_record_async(sync_record, stats, error_message)
            
            logger.info(f"Marketing sources sync completed successfully - SyncHistory ID: {sync_record.id}")
            return stats
            
        except Exception as e:
            # Step 5: Complete SyncHistory record with failure
            error_stats = {
                'total_processed': stats.get('total_processed', 0),
                'created': stats.get('created', 0),
                'updated': stats.get('updated', 0),
                'errors': stats.get('errors', 0) + 1  # Add this exception as an error
            }
            await self._complete_sync_record_async(sync_record, error_stats, str(e))
            
            logger.error(f"Marketing sources sync failed - SyncHistory ID: {sync_record.id}: {str(e)}")
            raise
    
    async def execute_sync(self, 
                          full: bool = False,
                          force: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False,
                          **kwargs) -> Dict[str, Any]:
        """Legacy sync interface - now properly uses SyncHistory tracking"""
        
        # Map legacy parameters to new sync method
        configuration = {
            'full': full,
            'force': force,
            'since': since.isoformat() if since else None,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'max_records': max_records,
            'dry_run': dry_run,
            'debug': debug
        }
        
        # Determine since_date based on full flag (legacy behavior)
        effective_since_date = None if full else (start_date or since)
        
        return await self.execute_sync_with_history(
            since_date=effective_since_date,
            force_overwrite=force,
            full_sync=full,
            dry_run=dry_run,
            max_records=max_records or 0,
            configuration=configuration
        )
    
    async def sync_marketing_sources_async(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for marketing sources with chunked processing for large datasets"""
        
        logger.info(f"Starting marketing sources sync - since_date: {since_date}, "
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
                raw_data = await sync_to_async(self.client.get_marketing_sources)(
                    since_date=since_date,
                    limit=max_records
                )
                
                if not raw_data:
                    logger.info("No marketing sources data retrieved")
                    return stats
                
                logger.info(f"Retrieved {len(raw_data)} marketing sources")
                
                if dry_run:
                    logger.info(f"DRY RUN: Would process {len(raw_data)} records")
                    stats['total_processed'] = len(raw_data)
                    return stats
                
                stats['total_processed'] = len(raw_data)
                
                # Process data using existing batch method
                batch_stats = await self._process_marketing_sources_batch(
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
                    first_chunk = next(self.client.get_marketing_sources_chunked(since_date=since_date, chunk_size=100), [])
                    stats['total_processed'] = len(first_chunk) if first_chunk else 0
                    return stats
                
                chunk_num = 0
                total_processed = 0
                
                # Process each chunk separately to avoid loading everything into memory
                for chunk_data in self.client.get_marketing_sources_chunked(
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
                        chunk_stats = await self._process_marketing_sources_batch(
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
            logger.error(f"Error in sync_marketing_sources_async: {e}")
            stats['errors'] += 1
            # Re-raise to let the caller handle it
            raise
        
        logger.info(f"Marketing sources sync completed - Stats: {stats}")
        return stats

    @sync_to_async
    def _process_marketing_sources_batch(self, batch: List[tuple], field_mapping: List[str], 
                          force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of marketing source records"""
        
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
                logger.error(f"Error validating marketing source record: {e}")
                error_count += 1
                continue
        
        if not validated_records:
            logger.warning("No valid marketing source records to process")
            return {'created': 0, 'updated': 0, 'errors': error_count}
        
        # Perform bulk upsert
        bulk_stats = self._bulk_upsert_records(validated_records, force_overwrite)
        
        # Add error count to stats
        bulk_stats['errors'] = error_count
        
        return bulk_stats

    def _bulk_upsert_records(self, validated_records: List[dict], force_overwrite: bool) -> Dict[str, int]:
        """Perform bulk upsert of marketing source records using modern bulk_create with update_conflicts"""
        
        from ingestion.models.genius import Genius_MarketingSource
        from django.db import transaction
        
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        if not validated_records:
            return stats
        
        try:
            with transaction.atomic():
                # Process in batches
                batch_size = self.BATCH_SIZE
                total_batches = (len(validated_records) + batch_size - 1) // batch_size
                logger.info(f"Processing {len(validated_records)} marketing sources in {total_batches} batches of {batch_size}")
                
                for i in range(0, len(validated_records), batch_size):
                    batch_num = (i // batch_size) + 1
                    batch = validated_records[i:i + batch_size]
                    
                    logger.info(f"Processing batch {batch_num}/{total_batches}: records {i+1}-{min(i+batch_size, len(validated_records))}")
                    
                    try:
                        # Prepare model instances
                        marketing_source_instances = []
                        for record in batch:
                            marketing_source_instances.append(Genius_MarketingSource(**record))
                        
                        # Bulk create with conflict resolution
                        update_fields = [
                            'type_id', 'label', 'description', 'start_date', 'end_date',
                            'add_user_id', 'add_date', 'is_active', 'is_allow_lead_modification',
                            'updated_at', 'sync_updated_at'
                        ]
                        
                        created_marketing_sources = Genius_MarketingSource.objects.bulk_create(
                            marketing_source_instances,
                            update_conflicts=True,
                            update_fields=update_fields,
                            unique_fields=['id']
                        )
                        
                        # Count results
                        batch_created = sum(1 for ms in created_marketing_sources if ms._state.adding)
                        stats['created'] += batch_created
                        stats['updated'] += len(batch) - batch_created
                        
                        logger.info(f"Batch {batch_num} completed - Created: {batch_created}, "
                                  f"Updated: {len(batch) - batch_created}, "
                                  f"Total so far: {stats['created']} created, {stats['updated']} updated")
                    
                    except Exception as batch_error:
                        logger.error(f"Error processing batch {batch_num}: {batch_error}")
                        stats['errors'] += len(batch)  # Count entire batch as errors
                        # Continue with next batch rather than failing entirely
                
        except Exception as e:
            logger.error(f"Error in bulk upsert: {e}")
            stats['errors'] += len(validated_records)
            raise
        
        logger.info(f"Bulk upsert completed - Created: {stats['created']}, "
                   f"Updated: {stats['updated']}, Errors: {stats['errors']}")
        return stats

