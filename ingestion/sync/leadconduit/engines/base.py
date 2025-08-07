"""
LeadConduit Sync Engine

Main sync orchestration engine for LeadConduit data following
sync_crm_guide.md architecture.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from ingestion.models.common import SyncHistory
from ..clients.events import LeadConduitEventsClient  # Used for leads data retrieval
from ..processors.leads import LeadConduitLeadsProcessor

logger = logging.getLogger(__name__)


class LeadConduitSyncEngine:
    """
    Main sync engine for LeadConduit data
    
    Orchestrates data synchronization between LeadConduit API and local storage
    following sync_crm_guide architecture patterns.
    """
    
    SOURCE_SYSTEM = "leadconduit"
    ENTITY_TYPES = ["events", "leads"]
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_system = self.SOURCE_SYSTEM
        
        # Initialize clients and processors
        self.leads_client = LeadConduitEventsClient(**config)  # Events client used for leads data
        self.leads_processor = LeadConduitLeadsProcessor()
        
        logger.info(f"Initialized LeadConduit sync engine with config: {list(config.keys())}")
    
    async def sync_all(self, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      force: bool = False) -> Dict[str, Any]:
        """
        Sync all LeadConduit data types
        
        Args:
            start_date: Start date for sync (UTC)
            end_date: End date for sync (UTC)
            force: Force sync even if already completed
            
        Returns:
            Dict containing sync results
        """
        logger.info("Starting full LeadConduit sync")
        
        results = {
            'started_at': datetime.now(timezone.utc),
            'source_system': self.SOURCE_SYSTEM,
            'sync_type': 'all',
            'entity_results': {}
        }
        
        try:
            # Skip events sync temporarily (schema mismatch issue)
            logger.info("Skipping LeadConduit events sync (schema mismatch)")
            results['entity_results']['events'] = {
                'skipped': True,
                'reason': 'Schema mismatch - events table needs migration update',
                'success': True
            }
            
            # Sync leads (working perfectly)
            logger.info("Syncing LeadConduit leads...")
            leads_result = await self.sync_leads(start_date, end_date, force)
            results['entity_results']['leads'] = leads_result
            
            # Calculate overall result
            results['completed_at'] = datetime.now(timezone.utc)
            results['total_duration'] = (results['completed_at'] - results['started_at']).total_seconds()
            results['success'] = all(r.get('success', False) for r in results['entity_results'].values())
            
            # Record sync in history
            await self.record_sync_completion(
                entity_type='all',
                start_date=start_date,
                end_date=end_date,
                records_processed=sum(r.get('records_processed', 0) for r in results['entity_results'].values()),
                records_created=sum(r.get('records_created', 0) for r in results['entity_results'].values()),
                records_updated=sum(r.get('records_updated', 0) for r in results['entity_results'].values()),
                records_failed=sum(r.get('records_failed', 0) for r in results['entity_results'].values()),
                success=results['success']
            )
            
            logger.info(f"Full LeadConduit sync completed: {results['success']}")
            return results
            
        except Exception as e:
            logger.error(f"Full LeadConduit sync failed: {e}")
            results['error'] = str(e)
            results['success'] = False
            results['completed_at'] = datetime.now(timezone.utc)
            return results
    
    async def sync_events(self, 
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         force: bool = False) -> Dict[str, Any]:
        """
        Sync LeadConduit events - CURRENTLY DISABLED
        
        Events sync is temporarily disabled due to model removal.
        Returns disabled status without processing.
        """
        entity_type = "events"
        logger.info(f"LeadConduit events sync is disabled - model removed")
        
        return {
            'entity_type': entity_type,
            'started_at': datetime.now(timezone.utc),
            'completed_at': datetime.now(timezone.utc),
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'records_failed': 0,
            'skipped': True,
            'reason': 'Events sync disabled - model removed',
            'success': True
        }
    
    async def sync_leads(self, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        force: bool = False) -> Dict[str, Any]:
        """
        Sync LeadConduit leads (derived from events)
        
        Processes source events to extract lead data
        """
        entity_type = "leads"
        logger.info(f"Starting {self.SOURCE_SYSTEM} {entity_type} sync")
        
        result = {
            'entity_type': entity_type,
            'started_at': datetime.now(timezone.utc),
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'records_failed': 0
        }
        
        try:
            # Check if sync needed based on CRM sync guide patterns
            if not force:
                # If date parameters are provided, always sync (manual override)
                if start_date is None and end_date is None:
                    # Only check recent sync if no specific dates requested
                    last_sync = await self.get_last_successful_sync(entity_type)
                    if last_sync and self.is_recent_sync(last_sync):
                        logger.info(f"Recent {entity_type} sync found, skipping")
                        result['skipped'] = True
                        result['reason'] = 'Recent sync exists'
                        result['success'] = True
                        return result
            
            # Set default date range if not provided
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=1)
            if not end_date:
                end_date = datetime.now(timezone.utc)
            
            logger.info(f"Syncing {entity_type} from {start_date} to {end_date}")
            
            # Process each day in the date range
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_failed = 0
            
            while current_date <= end_date_only:
                logger.info(f"Processing leads for date: {current_date}")
                
                # Get batch size from config or use default
                batch_size = self.config.get('batch_size', 100)
                logger.info(f"Using batch size: {batch_size}")
                
                # Process leads in batches to avoid memory issues with large datasets
                batch_count = 0
                async for leads_batch in self.leads_client.get_leads_in_batches_utc(current_date, batch_size):
                    if not leads_batch:
                        continue
                    
                    batch_count += 1
                    logger.info(f"Processing batch {batch_count} with {len(leads_batch)} leads")
                    
                    # Process this batch through processor
                    batch_result = await self.leads_processor.process_batch(leads_batch)
                    
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
                
                if batch_count == 0:
                    logger.info(f"No leads data found for {current_date}")
                else:
                    logger.info(f"Date {current_date} completed: {batch_count} batches processed")
                
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
                'date_range_processed': f"{start_date.date()} to {end_date.date()}"
            })
            
            # Record sync completion
            await self.record_sync_completion(
                entity_type=entity_type,
                start_date=start_date,
                end_date=end_date,
                records_processed=result['records_processed'],
                records_created=result.get('records_created', 0),
                records_updated=result.get('records_updated', 0),
                records_failed=result.get('records_failed', 0),
                success=result['success']
            )
            
            logger.info(f"Leads sync completed: {result['records_processed']} processed")
            return result
            
        except Exception as e:
            logger.error(f"{entity_type} sync failed: {e}")
            result['error'] = str(e)
            result['success'] = False
            result['completed_at'] = datetime.now(timezone.utc)
            return result
    
    async def get_last_successful_sync(self, entity_type: str) -> Optional[SyncHistory]:
        """Get the last successful sync for an entity type"""
        try:
            from asgiref.sync import sync_to_async
            
            get_sync = sync_to_async(
                lambda: SyncHistory.objects.filter(
                    crm_source='leadconduit',
                    sync_type=entity_type,
                    status='success'
                ).order_by('-end_time').first()
            )
            
            return await get_sync()
        except Exception as e:
            logger.warning(f"Error getting last sync: {e}")
            return None
    
    def is_recent_sync(self, sync_record: SyncHistory, hours: int = 0.25) -> bool:
        """Check if sync record is recent enough to skip"""
        if not sync_record.end_time:
            return False
        
        time_diff = datetime.now(timezone.utc) - sync_record.end_time
        return time_diff.total_seconds() < (hours * 3600)  # 15 minutes default for testing
    
    async def record_sync_completion(self,
                                   entity_type: str,
                                   start_date: Optional[datetime],
                                   end_date: Optional[datetime],
                                   records_processed: int,
                                   records_created: int = 0,
                                   records_updated: int = 0,
                                   records_failed: int = 0,
                                   success: bool = True,
                                   error_message: str = None) -> None:
        """Record sync completion in SyncHistory following CRM sync guide pattern"""
        try:
            from asgiref.sync import sync_to_async
            
            def create_sync_record():
                return SyncHistory.objects.create(
                    crm_source='leadconduit',
                    sync_type=entity_type,
                    start_time=start_date or datetime.now(timezone.utc),
                    end_time=end_date or datetime.now(timezone.utc),
                    records_processed=records_processed,
                    records_created=records_created,
                    records_updated=records_updated,
                    records_failed=records_failed,
                    status='success' if success else 'failed',
                    error_message=error_message,
                    performance_metrics={
                        'duration_seconds': ((end_date or datetime.now(timezone.utc)) - (start_date or datetime.now(timezone.utc))).total_seconds(),
                        'records_per_second': records_processed / max(1, ((end_date or datetime.now(timezone.utc)) - (start_date or datetime.now(timezone.utc))).total_seconds()),
                        'success_rate': (records_processed - records_failed) / max(1, records_processed) if records_processed > 0 else 0
                    }
                )
            
            save_sync = sync_to_async(create_sync_record)
            await save_sync()
            logger.debug(f"Recorded sync completion for {entity_type}: {records_processed} processed, {records_created} created, {records_updated} updated")
        except Exception as e:
            logger.error(f"Failed to record sync completion: {e}")


class LeadConduitEventsSyncEngine(LeadConduitSyncEngine):
    """Events-only sync engine"""
    
    async def sync(self, **kwargs) -> Dict[str, Any]:
        """Sync only events"""
        return await self.sync_events(**kwargs)


class LeadConduitLeadsSyncEngine(LeadConduitSyncEngine):
    """Leads-only sync engine"""
    
    async def sync(self, **kwargs) -> Dict[str, Any]:
        """Sync only leads"""
        return await self.sync_leads(**kwargs)
