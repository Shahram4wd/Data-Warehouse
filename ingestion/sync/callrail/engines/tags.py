"""
CallRail tags sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.tags import TagsClient
from ..processors.tags import TagsProcessor

logger = logging.getLogger(__name__)


class TagsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail tags"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = TagsClient()
        self.processor = TagsProcessor()
        self.entity_name = "tags"
    
    @sync_to_async
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for tags"""
        from ingestion.models.callrail import CallRail_Tag
        latest_tag = (CallRail_Tag.objects
                     .filter(company_id=account_id)
                     .order_by('-sync_updated_at')
                     .first())
        return latest_tag.sync_updated_at if latest_tag else None
    
    async def sync_tags(self, **kwargs) -> Dict[str, Any]:
        """Sync tags from CallRail API"""
        logger.info("Starting tags sync")
        
        sync_stats = {
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'errors': []
        }
        
        try:
            # Use async context manager for client
            async with TagsClient() as client:
                # Filter out boolean parameters that shouldn't go to API client
                client_kwargs = {k: v for k, v in kwargs.items() 
                               if k not in ['full_sync', 'force_overwrite', 'force'] and not isinstance(v, bool)}
                
                # Fetch tags data
                async for tags_batch in client.fetch_tags(**client_kwargs):
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
