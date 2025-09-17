"""
LeadConduit Sync Engine

Main sync orchestration engine for LeadConduit leads data following
sync_crm_guide.md architecture with batched processing for optimal performance.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from ingestion.models.common import SyncHistory
from ..clients.leads import LeadConduitLeadsClient  # Used for leads data retrieval
from ..processors.leads import LeadConduitLeadsProcessor

logger = logging.getLogger(__name__)


class LeadConduitSyncEngine:
    """
    Main sync engine for LeadConduit leads data
    
    Orchestrates leads data synchronization between LeadConduit API and local storage
    following sync_crm_guide architecture patterns with batched processing.
    """
    
    SOURCE_SYSTEM = "leadconduit"
    ENTITY_TYPES = ["leads"]
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_system = self.SOURCE_SYSTEM
        
        # Initialize clients and processors
        self.leads_client = LeadConduitLeadsClient(**config)  # Client provides leads data
        self.leads_processor = LeadConduitLeadsProcessor()
        
        logger.info(f"Initialized LeadConduit sync engine with config: {list(config.keys())}")
    
    async def sync_all(self, 
                      since_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      force_overwrite: bool = False,
                      full_sync: bool = False,
                      dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync all LeadConduit leads data following sync_crm_guide.md patterns
        
        Args:
            since_date: Start date for sync (UTC)
            end_date: End date for sync (UTC)
            force_overwrite: Force overwrite existing records
            full_sync: Perform full sync ignoring last sync timestamp
            dry_run: Test run without database writes
            
        Returns:
            Dict containing sync results
        """
        logger.info("Starting full LeadConduit leads sync")
        
        results = {
            'started_at': datetime.now(timezone.utc),
            'source_system': self.SOURCE_SYSTEM,
            'sync_type': 'all',
            'entity_results': {},
            'dry_run': dry_run
        }
        
        try:
            # Sync leads (currently the only entity for LeadConduit)
            logger.info("Syncing LeadConduit leads...")
            leads_result = await self.sync_leads(
                since_date=since_date,
                end_date=end_date, 
                force_overwrite=force_overwrite,
                full_sync=full_sync,
                dry_run=dry_run
            )
            results['entity_results']['leads'] = leads_result
            
            # Calculate overall result
            results['completed_at'] = datetime.now(timezone.utc)
            results['total_duration'] = (results['completed_at'] - results['started_at']).total_seconds()
            results['success'] = all(r.get('success', False) for r in results['entity_results'].values())
            
            logger.info(f"Full LeadConduit leads sync completed: {results['success']}")
            return results
            
        except Exception as e:
            logger.error(f"Full LeadConduit leads sync failed: {e}")
            results['error'] = str(e)
            results['success'] = False
            results['completed_at'] = datetime.now(timezone.utc)
            return results
    
    async def sync_leads(self, 
                        since_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        force_overwrite: bool = False,
                        full_sync: bool = False,
                        dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync LeadConduit leads from API following sync_crm_guide.md patterns
        
        Processes lead data from LeadConduit API using batched processing
        for memory efficiency with large datasets.
        """
        entity_type = "leads"
        logger.info(f"Starting {self.SOURCE_SYSTEM} {entity_type} sync")
        
        # MANDATORY: Create SyncHistory record at START following guide pattern
        from asgiref.sync import sync_to_async
        from django.utils import timezone as django_timezone
        
        @sync_to_async
        def create_sync_record():
            return SyncHistory.objects.create(
                crm_source=self.SOURCE_SYSTEM,  # 'leadconduit'
                sync_type=entity_type,         # 'leads' (NO suffix)
                status='running',              # Standard status
                start_time=django_timezone.now(),
                configuration={
                    'since_date': since_date.isoformat() if since_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'force_overwrite': force_overwrite,
                    'full_sync': full_sync,
                    'dry_run': dry_run,
                    'batch_size': self.config.get('batch_size', 100)
                }
            )
        
        sync_record = await create_sync_record()
        
        result = {
            'entity_type': entity_type,
            'sync_history_id': sync_record.id,
            'started_at': sync_record.start_time,
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'records_failed': 0,
            'dry_run': dry_run
        }
        
        try:
            # Determine sync strategy following guide priority:
            # 1. --start-date parameter (manual override) 
            # 2. --force flag (None = fetch all, ignore history)
            # 3. --full flag (None = fetch all, ignore history) 
            # 4. SyncHistory table last successful sync timestamp with lookback
            # 5. Default: last 7 days (bounded initial sync)
            
            if not since_date and not full_sync and not force_overwrite:
                # Get last successful sync timestamp from SyncHistory
                last_sync_time = await self.get_last_sync_timestamp()
                if last_sync_time:
                    # Apply lookback for safety (LeadConduit data may have delays)
                    lookback_hours = 2  # Small lookback for LeadConduit
                    since_date = last_sync_time - timedelta(hours=lookback_hours)
                    logger.info(f"Delta sync: using last sync {last_sync_time} with {lookback_hours}h lookback = {since_date}")
                else:
                    # Initial bounded sync (avoid full history on first run)
                    since_date = datetime.now(timezone.utc) - timedelta(days=7)
                    logger.info(f"Initial sync: last 7 days from {since_date}")
            elif force_overwrite:
                since_date = None
                logger.info("Force overwrite: fetching all data")
            elif full_sync:
                since_date = None  
                logger.info("Full sync: fetching all data")
            
            # Set fallback date range for bounded sync
            if not since_date:
                since_date = datetime.now(timezone.utc) - timedelta(days=7)  # Default 7-day window
            if not end_date:
                end_date = datetime.now(timezone.utc)
            
            logger.info(f"Syncing {entity_type} from {since_date} to {end_date}")
            
            if dry_run:
                logger.info("DRY RUN MODE: No database writes will be performed")
            
            # Process each day in the date range
            current_date = since_date.date()
            end_date_only = end_date.date()
            
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_failed = 0
            
            while current_date <= end_date_only:
                logger.info(f"Processing leads for date: {current_date}")
                
                # Get batch size from config or use default
                batch_size = self.config.get('batch_size', 100)
                max_records = self.config.get('max_records', 0)
                logger.info(f"Using batch size: {batch_size}, max records: {max_records}")
                
                # Process leads in batches to avoid memory issues with large datasets
                batch_count = 0
                async for leads_batch in self.leads_client.get_leads_in_batches_utc(current_date, batch_size):
                    if not leads_batch:
                        continue
                    
                    batch_count += 1
                    logger.info(f"Processing batch {batch_count} with {len(leads_batch)} leads")
                    
                    # Apply max_records limit if specified
                    if max_records > 0 and total_processed >= max_records:
                        logger.info(f"Reached max_records limit: {max_records}")
                        break
                    
                    # Truncate batch if it would exceed max_records
                    if max_records > 0:
                        remaining = max_records - total_processed
                        if len(leads_batch) > remaining:
                            leads_batch = leads_batch[:remaining]
                    
                    # Process this batch through processor
                    if not dry_run:
                        batch_result = await self.leads_processor.process_batch(leads_batch)
                    else:
                        # In dry run mode, just validate but don't save
                        batch_result = {
                            'processed': len(leads_batch),
                            'created': len(leads_batch),  # Assume all would be created
                            'updated': 0,
                            'failed': 0
                        }
                        logger.info(f"DRY RUN: Would process {len(leads_batch)} leads")
                    
                    batch_processed = batch_result.get('processed', 0)
                    batch_created = batch_result.get('created', 0)
                    batch_updated = batch_result.get('updated', 0)
                    batch_failed = batch_result.get('failed', 0)
                    
                    total_processed += batch_processed
                    total_created += batch_created
                    total_updated += batch_updated
                    total_failed += batch_failed
                    
                    logger.info(f"Batch {batch_count} results: {batch_processed} processed, "
                              f"{batch_created} created, {batch_updated} updated, {batch_failed} failed")
                    logger.info(f"Running totals: {total_processed} processed, {total_created} created, "
                              f"{total_updated} updated, {total_failed} failed")
                    
                    # Check if we've reached max_records
                    if max_records > 0 and total_processed >= max_records:
                        break
                
                if batch_count == 0:
                    logger.info(f"No leads data found for {current_date}")
                else:
                    logger.info(f"Date {current_date} completed: {batch_count} batches processed")
                
                # Check if we've reached max_records
                if max_records > 0 and total_processed >= max_records:
                    logger.info(f"Stopping sync - reached max_records limit: {max_records}")
                    break
                
                # Move to next day
                current_date += timedelta(days=1)
            
            # Update results with totals
            result.update({
                'records_processed': total_processed,
                'records_created': total_created,
                'records_updated': total_updated,
                'records_failed': total_failed,
                'success': total_failed == 0,
                'completed_at': datetime.now(timezone.utc),
                'date_range_processed': f"{since_date.date()} to {end_date.date()}"
            })
            
            # MANDATORY: Update SyncHistory record with SUCCESS following guide pattern
            @sync_to_async
            def update_sync_success():
                sync_record.status = 'success' if total_failed == 0 else 'partial'
                sync_record.end_time = django_timezone.now()
                sync_record.records_processed = total_processed
                sync_record.records_created = total_created
                sync_record.records_updated = total_updated
                sync_record.records_failed = total_failed
                sync_record.performance_metrics = {
                    'duration_seconds': (sync_record.end_time - sync_record.start_time).total_seconds(),
                    'records_per_second': total_processed / (sync_record.end_time - sync_record.start_time).total_seconds() if total_processed > 0 else 0,
                    'success_rate': (total_processed - total_failed) / total_processed if total_processed > 0 else 0
                }
                sync_record.save()
                return sync_record
            
            await update_sync_success()
            
            logger.info(f"Leads sync completed: {result['records_processed']} processed")
            return result
            
        except Exception as e:
            logger.error(f"{entity_type} sync failed: {e}")
            
            # MANDATORY: Update SyncHistory record with FAILURE following guide pattern
            @sync_to_async
            def update_sync_failure():
                sync_record.status = 'failed'
                sync_record.end_time = django_timezone.now()
                sync_record.error_message = str(e)
                sync_record.records_failed = result.get('records_failed', 0)
                sync_record.save()
                return sync_record
            
            await update_sync_failure()
            
            result['error'] = str(e)
            result['success'] = False
            result['completed_at'] = datetime.now(timezone.utc)
            return result
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        STANDARD PATTERN: Get last successful sync timestamp from SyncHistory
        Following sync_crm_guide.md mandatory implementation
        """
        try:
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='leadconduit',        # EXACT: CRM source name
                    sync_type='leads',               # EXACT: Entity type (NO '_sync' suffix)
                    status__in=['success', 'completed'], # Include successful syncs
                    end_time__isnull=False          # Only completed syncs
                ).order_by('-end_time').first()

                return last_sync.end_time if last_sync else None

            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
class LeadConduitLeadsSyncEngine(LeadConduitSyncEngine):
    """Leads-only sync engine following sync_crm_guide.md patterns"""
    
    async def sync(self, **kwargs) -> Dict[str, Any]:
        """Sync only leads with proper parameter mapping"""
        # Map parameters to match guide standards
        sync_params = {
            'since_date': kwargs.get('since_date') or kwargs.get('start_date'),
            'end_date': kwargs.get('end_date'),
            'force_overwrite': kwargs.get('force_overwrite') or kwargs.get('force', False),
            'full_sync': kwargs.get('full_sync') or kwargs.get('full', False),
            'dry_run': kwargs.get('dry_run', False)
        }
        return await self.sync_leads(**sync_params)
