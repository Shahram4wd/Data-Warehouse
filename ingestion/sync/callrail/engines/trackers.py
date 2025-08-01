"""
CallRail trackers sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import CallRailBaseSyncEngine
from ..clients.trackers import TrackersClient
from ..processors.trackers import TrackersProcessor

logger = logging.getLogger(__name__)


class TrackersSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail trackers"""
    
    def __init__(self, account_id: str, **kwargs):
        super().__init__(account_id=account_id, **kwargs)
        self.client = TrackersClient()
        self.processor = TrackersProcessor()
        self.entity_name = "trackers"
    
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for trackers"""
        from ingestion.models.callrail import CallRail_Tracker
        latest_tracker = (CallRail_Tracker.objects
                         .filter(company_id=account_id)
                         .order_by('-updated_at')
                         .first())
        return latest_tracker.updated_at if latest_tracker else None
    
    async def sync_trackers(self, **kwargs) -> Dict[str, Any]:
        """Sync trackers from CallRail API"""
        logger.info(f"Starting trackers sync for account {self.account_id}")
        
        sync_stats = {
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'errors': []
        }
        
        try:
            # Get last sync timestamp for delta sync
            since_date = kwargs.get('since_date')
            if not since_date and not kwargs.get('force', False):
                since_date = self.get_last_sync_timestamp(self.account_id)
                logger.info(f"Delta sync since: {since_date}")
            
            # Fetch trackers data
            async for trackers_batch in self.client.fetch_trackers(
                account_id=self.account_id,
                since_date=since_date,
                **kwargs
            ):
                if not trackers_batch:
                    continue
                    
                sync_stats['total_fetched'] += len(trackers_batch)
                logger.info(f"Processing {len(trackers_batch)} trackers...")
                
                # Process trackers batch
                processed_trackers = []
                for tracker in trackers_batch:
                    try:
                        # Transform tracker data
                        transformed = self.processor.transform_record(tracker)
                        
                        # Validate transformed data
                        if self.processor.validate_record(transformed):
                            processed_trackers.append(transformed)
                            sync_stats['total_processed'] += 1
                        else:
                            logger.warning(f"Tracker validation failed: {tracker.get('id', 'unknown')}")
                            
                    except Exception as e:
                        error_msg = f"Error processing tracker {tracker.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        sync_stats['errors'].append(error_msg)
                        continue
                
                # Save processed trackers
                if processed_trackers:
                    from ingestion.models.callrail import CallRail_Tracker
                    save_stats = await self.bulk_save_records(
                        processed_trackers,
                        CallRail_Tracker,
                        'id'
                    )
                    sync_stats['total_created'] += save_stats['created']
                    sync_stats['total_updated'] += save_stats['updated']
            
            logger.info(f"Trackers sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            error_msg = f"Trackers sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
