"""
CallRail text messages sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.text_messages import TextMessagesClient
from ..processors.text_messages import TextMessagesProcessor

logger = logging.getLogger(__name__)


class TextMessagesSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail text messages"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = TextMessagesClient()
        self.processor = TextMessagesProcessor()
        self.entity_name = "text_messages"
    
    @sync_to_async
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for text messages"""
        from ingestion.models.callrail import CallRail_TextMessage
        latest_message = (CallRail_TextMessage.objects
                         .filter(company_id=account_id)
                         .order_by('-sent_at')
                         .first())
        return latest_message.sent_at if latest_message else None
    
    async def sync_text_messages(self, **kwargs) -> Dict[str, Any]:
        """Sync text messages from CallRail API"""
        logger.info("Starting text messages sync")
        
        sync_stats = {
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'errors': []
        }
        
        try:
            # Use async context manager for client
            async with TextMessagesClient() as client:
                # Filter out boolean parameters that shouldn't go to API client
                client_kwargs = {k: v for k, v in kwargs.items() 
                               if k not in ['full_sync', 'force_overwrite', 'force'] and not isinstance(v, bool)}
                
                # Fetch text messages data
                async for messages_batch in client.fetch_text_messages(**client_kwargs):
                    if not messages_batch:
                        continue
                        
                    sync_stats['total_fetched'] += len(messages_batch)
                    logger.info(f"Processing {len(messages_batch)} text messages...")
                    
                    # Process text messages batch
                    processed_messages = []
                    for message in messages_batch:
                        try:
                            # Transform message data
                            transformed = self.processor.transform_record(message)
                            
                            # Validate transformed data
                            if self.processor.validate_record(transformed):
                                processed_messages.append(transformed)
                                sync_stats['total_processed'] += 1
                            else:
                                logger.warning(f"Text message validation failed: {message.get('id', 'unknown')}")
                                
                        except Exception as e:
                            error_msg = f"Error processing text message {message.get('id', 'unknown')}: {e}"
                            logger.error(error_msg)
                            sync_stats['errors'].append(error_msg)
                            continue
                    
                    # Save processed text messages
                    if processed_messages:
                        from ingestion.models.callrail import CallRail_TextMessage
                        save_stats = await self.bulk_save_records(
                            processed_messages,
                            CallRail_TextMessage,
                            'id'
                        )
                        sync_stats['total_created'] += save_stats['created']
                        sync_stats['total_updated'] += save_stats['updated']
            
            logger.info(f"Text messages sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            error_msg = f"Text messages sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
