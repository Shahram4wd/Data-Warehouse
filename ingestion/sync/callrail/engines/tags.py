"""
CallRail tags sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import CallRailBaseSyncEngine
from ..clients.tags import TagsClient
from ..processors.tags import TagsProcessor

logger = logging.getLogger(__name__)


class TagsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail tags"""
    
    def __init__(self, account_id: str, **kwargs):
        super().__init__(account_id=account_id, **kwargs)
        self.client = TagsClient()
        self.processor = TagsProcessor()
        self.entity_name = "tags"
    
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for tags"""
        from ingestion.models.callrail import CallRail_Tag
        latest_tag = (CallRail_Tag.objects
                     .filter(company_id=account_id)
                     .order_by('-updated_at')
                     .first())
        return latest_tag.updated_at if latest_tag else None
    
    async def sync_tags(self, **kwargs) -> Dict[str, Any]:
        """Sync tags from CallRail API"""
        logger.info(f"Starting tags sync for account {self.account_id}")
        
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
            
            # Fetch tags data
            async for tags_batch in self.client.fetch_tags(
                account_id=self.account_id,
                since_date=since_date,
                **kwargs
            ):
                if not tags_batch:
                    continue
                    
                sync_stats['total_fetched'] += len(tags_batch)
                logger.info(f"Processing {len(tags_batch)} tags...")
                
                # Process tags batch
                processed_tags = []
                for tag in tags_batch:
                    try:
                        # Transform tag data
                        transformed = self.processor.transform_record(tag)
                        
                        # Validate transformed data
                        if self.processor.validate_record(transformed):
                            processed_tags.append(transformed)
                            sync_stats['total_processed'] += 1
                        else:
                            logger.warning(f"Tag validation failed: {tag.get('id', 'unknown')}")
                            
                    except Exception as e:
                        error_msg = f"Error processing tag {tag.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        sync_stats['errors'].append(error_msg)
                        continue
                
                # Save processed tags
                if processed_tags:
                    from ingestion.models.callrail import CallRail_Tag
                    save_stats = await self.bulk_save_records(
                        processed_tags,
                        CallRail_Tag,
                        'id'
                    )
                    sync_stats['total_created'] += save_stats['created']
                    sync_stats['total_updated'] += save_stats['updated']
            
            logger.info(f"Tags sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            error_msg = f"Tags sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
