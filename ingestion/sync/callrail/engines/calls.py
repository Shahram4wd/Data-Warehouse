"""
CallRail calls sync engine for orchestrating calls synchronization
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import CallRailBaseSyncEngine
from ..clients.calls import CallsClient
from ..processors.calls import CallsProcessor

logger = logging.getLogger(__name__)


class CallsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail calls"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = CallsClient()
        self.processor = CallsProcessor()
        self.entity_name = "calls"
    
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for calls"""
        from ingestion.models.callrail import CallRail_Call
        latest_call = (CallRail_Call.objects
                      .filter(company_id=account_id)  # Using company_id as account filter
                      .order_by('-start_time')
                      .first())
        return latest_call.start_time if latest_call else None
    
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
        
        sync_stats = {
            'entity': 'calls',
            'full_sync': full_sync,
            'force_overwrite': force_overwrite,
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'start_time': datetime.now(),
            'errors': []
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
                # 4. Database last sync timestamp
                if since_date:
                    logger.info(f"Performing manual sync since: {since_date}")
                elif force_overwrite:
                    since_date = None
                    logger.info("Performing force overwrite sync (fetching all records)")
                elif full_sync:
                    since_date = None
                    logger.info("Performing full sync (fetching all records)")
                else:
                    # TODO: Implement database last sync timestamp lookup
                    since_date = None
                    logger.info("Performing delta sync for all accounts")
                
                # Fetch and process calls in batches (client now handles all accounts)
                async for call_batch in client.fetch_calls(
                    since_date=since_date,
                    **kwargs
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
            
            sync_stats['end_time'] = datetime.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            
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
            sync_stats['end_time'] = datetime.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            sync_stats['total_errors'] += 1
            sync_stats['errors'].append(f"Sync failed: {str(e)}")
            raise
