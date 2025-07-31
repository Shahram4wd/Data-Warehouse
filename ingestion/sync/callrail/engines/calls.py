"""
CallRail calls sync engine for orchestrating calls synchronization
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import CallRailBaseSyncEngine
from ..clients.calls import CallsClient
from ..processors.calls import CallsProcessor
from ingestion.models.common import SyncHistory
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class CallsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail calls"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = CallsClient()
        self.processor = CallsProcessor()
        self.entity_name = "calls"
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the last sync timestamp for calls using SyncHistory framework"""
        try:
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='callrail',
                    sync_type='calls',
                    status='success',
                    end_time__isnull=False
                ).order_by('-end_time').first()
                
                return last_sync.end_time if last_sync else None
            
            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    async def sync_calls(
        self, 
        full_sync: bool = False,
        force_overwrite: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync calls for all accounts following CRM sync guide standards
        
        Args:
            full_sync: Whether to perform a full sync (ignore timestamps)
            force_overwrite: Whether to completely replace existing records
            **kwargs: Additional parameters (since_date, batch_size, max_records, etc.)
            
        Returns:
            Dict with sync results
        """
        logger.info(f"Starting calls sync for all accounts (full_sync={full_sync}, force_overwrite={force_overwrite})")
        
        # Create SyncHistory record following CRM sync guide standards
        sync_history_data = {
            'crm_source': 'callrail',
            'sync_type': 'calls',
            'start_time': timezone.now(),
            'status': 'running',
            'configuration': {
                'full_sync': full_sync,
                'force_overwrite': force_overwrite,
                **kwargs
            }
        }
        
        @sync_to_async
        def create_sync_history():
            return SyncHistory.objects.create(**sync_history_data)
        
        sync_history = await create_sync_history()
        
        sync_stats = {
            'entity': 'calls',
            'full_sync': full_sync,
            'force_overwrite': force_overwrite,
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'start_time': sync_history.start_time,
            'errors': [],
            'sync_history_id': sync_history.id
        }
        
        try:
            async with CallsClient() as client:
                # Handle since_date parameter according to CRM sync guide
                since_date = kwargs.get('since_date')
                if since_date and isinstance(since_date, str):
                    # Convert string date to datetime object
                    from datetime import datetime as dt
                    try:
                        since_date = dt.strptime(since_date, '%Y-%m-%d')
                        logger.info(f"Using manual since date: {since_date}")
                    except ValueError:
                        logger.warning(f"Invalid since date format: {since_date}, ignoring")
                        since_date = None
                
                # Determine sync strategy following CRM sync guide priority:
                # 1. --since parameter (manual override)
                # 2. --force-overwrite flag (None = fetch all)
                # 3. --full flag (None = fetch all)
                # 4. Database last sync timestamp from SyncHistory
                if since_date:
                    logger.info(f"Performing manual sync since: {since_date}")
                elif force_overwrite:
                    since_date = None
                    logger.info("Performing force overwrite sync (fetching all records)")
                elif full_sync:
                    since_date = None
                    logger.info("Performing full sync (fetching all records)")
                else:
                    # Use SyncHistory to determine last sync timestamp
                    since_date = await self.get_last_sync_timestamp()
                    if since_date:
                        logger.info(f"Performing delta sync since last successful sync: {since_date}")
                    else:
                        logger.info("No previous sync found, performing initial full sync")
                
                # Fetch and process calls in batches (client now handles all accounts)
                # Remove since_date from kwargs to avoid duplicate parameter error
                client_kwargs = {k: v for k, v in kwargs.items() if k != 'since_date'}
                
                async for call_batch in client.fetch_calls(
                    since_date=since_date,
                    **client_kwargs
                ):
                    if not call_batch:
                        continue
                    
                    sync_stats['total_fetched'] += len(call_batch)
                    logger.info(f"Processing batch of {len(call_batch)} calls")
                    
                    # Process batch
                    processed_calls = []
                    for call_data in call_batch:
                        try:
                            # Transform and validate each call
                            transformed = self.processor.transform_record(call_data)
                            
                            # Validate transformed data
                            if self.processor.validate_record(transformed):
                                processed_calls.append(transformed)
                                sync_stats['total_processed'] += 1
                            else:
                                logger.warning(f"Call validation failed: {call_data.get('id', 'unknown')}")
                                
                        except Exception as e:
                            logger.error(f"Error processing call {call_data.get('id', 'unknown')}: {e}")
                            sync_stats['total_errors'] += 1
                            sync_stats['errors'].append(f"Call {call_data.get('id', 'unknown')}: {str(e)}")
                    
                    # Save processed calls
                    if processed_calls:
                        from ingestion.models.callrail import CallRail_Call
                        save_stats = await self.bulk_save_records(
                            processed_calls,
                            CallRail_Call,
                            'id'
                        )
                        sync_stats['total_created'] += save_stats['created']
                        sync_stats['total_updated'] += save_stats['updated']
                        sync_stats['total_errors'] += save_stats['errors']
                        sync_stats['errors'].extend(save_stats['error_details'])
            
            sync_stats['end_time'] = timezone.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            
            # Update SyncHistory record with completion status
            @sync_to_async
            def update_sync_history():
                sync_history.end_time = sync_stats['end_time']
                sync_history.status = 'success' if sync_stats['total_errors'] == 0 else 'partial'
                sync_history.records_processed = sync_stats['total_processed']
                sync_history.records_created = sync_stats['total_created']
                sync_history.records_updated = sync_stats['total_updated']
                sync_history.records_failed = sync_stats['total_errors']
                sync_history.performance_metrics = {
                    'duration_seconds': sync_stats['duration'],
                    'records_per_second': sync_stats['total_processed'] / sync_stats['duration'] if sync_stats['duration'] > 0 else 0
                }
                sync_history.save()
                return sync_history
            
            await update_sync_history()
            
            logger.info(
                f"Calls sync completed for all accounts. "
                f"Processed: {sync_stats['total_processed']}, "
                f"Created: {sync_stats['total_created']}, "
                f"Updated: {sync_stats['total_updated']}, "
                f"Errors: {sync_stats['total_errors']}"
            )
            
            return sync_stats
            
        except Exception as e:
            logger.error(f"Calls sync failed: {e}")
            sync_stats['end_time'] = timezone.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            sync_stats['total_errors'] += 1
            sync_stats['errors'].append(f"Sync failed: {str(e)}")
            
            # Update SyncHistory record with failure status
            @sync_to_async
            def update_sync_history_failed():
                sync_history.end_time = sync_stats['end_time']
                sync_history.status = 'failed'
                sync_history.records_failed = sync_stats['total_errors']
                sync_history.error_message = str(e)
                sync_history.performance_metrics = {
                    'duration_seconds': sync_stats['duration']
                }
                sync_history.save()
                return sync_history
            
            await update_sync_history_failed()
            raise
