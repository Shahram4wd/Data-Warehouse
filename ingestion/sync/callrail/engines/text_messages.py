"""
CallRail text messages sync engine for orchestrating text messages synchronization
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from .base import CallRailBaseSyncEngine
from ..clients.text_messages import TextMessagesClient
from ..processors.text_messages import TextMessagesProcessor
from ingestion.models.common import SyncHistory
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class TextMessagesSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail text messages"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = TextMessagesClient()
        self.processor = TextMessagesProcessor()
        self.entity_name = "text_messages"
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the last sync timestamp for text messages using SyncHistory framework"""
        try:
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='callrail',
                    sync_type='text_messages',
                    status='success',
                    end_time__isnull=False
                ).order_by('-end_time').first()
                
                return last_sync.end_time if last_sync else None
            
            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None

    async def sync_text_messages(
        self, 
        full_sync: bool = False,
        force_overwrite: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Sync text messages for all accounts following CRM sync guide standards
        
        Args:
            full_sync: Whether to perform a full sync (ignore timestamps)
            force_overwrite: Whether to completely replace existing records
            **kwargs: Additional parameters (since_date, batch_size, max_records, etc.)
            
        Returns:
            Dict with sync results
        """
        logger.info(f"Starting text messages sync for all accounts (full_sync={full_sync}, force_overwrite={force_overwrite})")
        
        # Create SyncHistory record following CRM sync guide standards
        sync_history_data = {
            'crm_source': 'callrail',
            'sync_type': 'text_messages',
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
            'entity': 'text_messages',
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
            async with TextMessagesClient() as client:
                # Handle since_date parameter according to CRM sync guide
                since_date = kwargs.get('since_date') or kwargs.get('start_date')
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
                # 1. --start-date parameter (manual override)
                # 2. --force flag (None = fetch all)
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
                
                # Fetch and process text messages in batches
                # Filter out parameters that shouldn't go to API client
                excluded_keys = {
                    'since_date', 'full_sync', 'force_overwrite', 'force',
                    'max_records', 'batch_size', 'start_date', 'end_date',
                    'dry_run', 'quiet'
                }
                client_kwargs = {k: v for k, v in kwargs.items() if k not in excluded_keys}

                # Map engine batch_size to API per_page if provided
                if getattr(self, 'batch_size', None):
                    try:
                        client_kwargs['per_page'] = int(self.batch_size)
                    except Exception:
                        # Fallback to default in client if conversion fails
                        pass
                
                max_records = kwargs.get('max_records') or 0
                processed_total = 0

                async for messages_batch in client.fetch_text_messages(
                    since_date=since_date,
                    **client_kwargs
                ):
                    if not messages_batch:
                        continue

                    # Defensive local filter: ensure delta by 'sent_at' if API returns older rows
                    if since_date:
                        try:
                            filtered = []
                            for m in messages_batch:
                                ts = m.get('sent_at')
                                if not ts:
                                    continue
                                # Accept ISO strings with or without microseconds; assume UTC if Z
                                from datetime import datetime as dt
                                from django.utils.dateparse import parse_datetime
                                parsed = parse_datetime(ts) or dt.fromisoformat(ts.replace('Z', '+00:00'))
                                if parsed and parsed >= since_date:
                                    filtered.append(m)
                            messages_batch = filtered
                            if not messages_batch:
                                logger.info("No text messages >= since_date on this page; stopping pagination early.")
                                break
                        except Exception:
                            # If parsing fails, proceed without local filter
                            pass
                    
                    # Trim to respect max_records across batches
                    if max_records and (processed_total + len(messages_batch)) > max_records:
                        take = max_records - processed_total
                        if take <= 0:
                            break
                        messages_batch = messages_batch[:take]
                    
                    sync_stats['total_fetched'] += len(messages_batch)
                    logger.info(f"Processing batch of {len(messages_batch)} text messages")
                    
                    # Process batch
                    processed_messages = []
                    for message_data in messages_batch:
                        try:
                            # Transform and validate each text message
                            transformed = self.processor.transform_record(message_data)
                            
                            # Validate transformed data
                            if self.processor.validate_record(transformed):
                                processed_messages.append(transformed)
                                sync_stats['total_processed'] += 1
                            else:
                                logger.warning(f"Text message validation failed: {message_data.get('id', 'unknown')}")
                                
                        except Exception as e:
                            logger.error(f"Error processing text message {message_data.get('id', 'unknown')}: {e}")
                            sync_stats['total_errors'] += 1
                            sync_stats['errors'].append(f"Text message {message_data.get('id', 'unknown')}: {str(e)}")
                    
                    # Save processed text messages
                    if processed_messages and not getattr(self, 'dry_run', False):
                        from ingestion.models.callrail import CallRail_TextMessage
                        save_stats = await self.bulk_save_records(
                            processed_messages,
                            CallRail_TextMessage,
                            'id'
                        )
                        sync_stats['total_created'] += save_stats['created']
                        sync_stats['total_updated'] += save_stats['updated']
                        sync_stats['total_errors'] += save_stats['errors']
                        sync_stats['errors'].extend(save_stats['error_details'])
                    
                    processed_total += len(messages_batch)
                    if max_records and processed_total >= max_records:
                        logger.info(f"Reached max_records={max_records}; stopping.")
                        break
            
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
                f"Text messages sync completed for all accounts. "
                f"Processed: {sync_stats['total_processed']}, "
                f"Created: {sync_stats['total_created']}, "
                f"Updated: {sync_stats['total_updated']}, "
                f"Errors: {sync_stats['total_errors']}"
            )
            
            return sync_stats
            
        except Exception as e:
            logger.error(f"Text messages sync failed: {e}")
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
