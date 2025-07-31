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
    
    def __init__(self, account_id: str, **kwargs):
        super().__init__(account_id=account_id, **kwargs)
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
        account_id: str, 
        full_sync: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync calls for a specific account
        
        Args:
            account_id: CallRail account ID
            full_sync: Whether to perform a full sync or delta sync
            **kwargs: Additional parameters
            
        Returns:
            Dict with sync results
        """
        logger.info(f"Starting calls sync for account {account_id} (full_sync={full_sync})")
        
        sync_stats = {
            'account_id': account_id,
            'entity': 'calls',
            'full_sync': full_sync,
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'start_time': datetime.now(),
            'errors': []
        }
        
        try:
            # Determine sync strategy
            since_date = None if full_sync else self.get_last_sync_timestamp(account_id)
            
            if since_date:
                logger.info(f"Performing delta sync since {since_date}")
            else:
                logger.info("Performing full sync")
            
            # Fetch and process calls in batches
            async for call_batch in self.client.fetch_calls(
                account_id=account_id,
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
                        # Add account ID
                        transformed['account_id'] = account_id
                        validated = self.processor.validate_record(transformed)
                        processed_calls.append(validated)
                        sync_stats['total_processed'] += 1
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
                f"Calls sync completed for account {account_id}. "
                f"Processed: {sync_stats['total_processed']}, "
                f"Created: {sync_stats['total_created']}, "
                f"Updated: {sync_stats['total_updated']}, "
                f"Errors: {sync_stats['total_errors']}"
            )
            
            return sync_stats
            
        except Exception as e:
            logger.error(f"Calls sync failed for account {account_id}: {e}")
            sync_stats['end_time'] = datetime.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            sync_stats['total_errors'] += 1
            sync_stats['errors'].append(f"Sync failed: {str(e)}")
            raise
