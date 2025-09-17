"""
CallRail users sync engine (enterprise pattern)
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.users import UsersClient
from ..processors.users import UsersProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)


class UsersSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail users"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = UsersClient()
        self.processor = UsersProcessor()
        self.entity_name = "users"

    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the last sync timestamp for users using SyncHistory framework"""
        try:
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='callrail',
                    sync_type='users',
                    status='success',
                    end_time__isnull=False
                ).order_by('-end_time').first()
                return last_sync.end_time if last_sync else None

            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    async def sync_users(self, full_sync: bool = False, force_overwrite: bool = False, **kwargs) -> Dict[str, Any]:
        """Sync users from CallRail API with SyncHistory tracking"""
        logger.info(f"Starting users sync (full_sync={full_sync}, force_overwrite={force_overwrite})")

        # Create SyncHistory record following CRM sync guide standards
        @sync_to_async
        def create_sync_history_record():
            """Create initial SyncHistory record for tracking"""
            sync_history_data = {
                'crm_source': 'callrail',
                'sync_type': 'users', 
                'endpoint': 'users',
                'start_time': timezone.now(),
                'status': 'running',
                'configuration': {
                    'full_sync': full_sync,
                    'force_overwrite': force_overwrite,
                    **{k: v for k, v in kwargs.items() if k not in ['full_sync', 'force_overwrite']}
                }
            }
            
            return SyncHistory.objects.create(**sync_history_data)

        sync_history = await create_sync_history_record()

        # Working stats we will also persist into SyncHistory on completion 
        stats = {
            'entity': 'users',
            'full_sync': full_sync,
            'force_overwrite': force_overwrite,
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'errors': [],
            'start_time': sync_history.start_time,
        }

        try:
            async with UsersClient() as client:
                # Determine since_date priority: manual > force/full (None) > last SyncHistory
                since_date = kwargs.get('since_date')
                if since_date and isinstance(since_date, str):
                    from datetime import datetime as dt
                    try:
                        since_date = dt.strptime(since_date, '%Y-%m-%d')
                        logger.info(f"Using manual since date: {since_date}")
                    except ValueError:
                        logger.warning(f"Invalid since date format: {since_date}, ignoring")
                        since_date = None

                if force_overwrite:
                    since_date = None
                    logger.info("Force overwrite/full fetch for users")
                elif full_sync:
                    since_date = None
                    logger.info("Full users sync (fetch all)")
                else:
                    # Use SyncHistory to determine last sync timestamp
                    last_sync_timestamp = await self.get_last_sync_timestamp()
                    if last_sync_timestamp:
                        since_date = last_sync_timestamp
                        logger.info(f"Delta sync since last successful: {since_date}")
                    else:
                        logger.info("No previous users sync found; performing initial full sync")

                # Apply max_records limit if specified
                max_records = kwargs.get('max_records', 0)
                processed_count = 0

                # Prepare client kwargs - exclude problematic parameters
                client_kwargs = {k: v for k, v in kwargs.items() 
                               if k not in ['since_date', 'max_records', 'full_sync', 'force_overwrite']}

                # Fetch users from all accounts
                async for users_batch in client.fetch_users(since_date=since_date, **client_kwargs):
                    if not users_batch:
                        continue
                        
                    stats['total_fetched'] += len(users_batch)
                    logger.info(f"Processing {len(users_batch)} users...")

                    # Apply max_records limit if needed
                    if max_records > 0 and processed_count + len(users_batch) > max_records:
                        remaining = max_records - processed_count
                        users_batch = users_batch[:remaining]
                        logger.info(f"Limiting batch to {remaining} users (max_records={max_records})")

                    # Process users batch
                    processed_users = []
                    for user in users_batch:
                        try:
                            # Transform user data
                            transformed = self.processor.transform_record(user)
                            
                            # Validate transformed data
                            if self.processor.validate_record(transformed):
                                processed_users.append(transformed)
                                stats['total_processed'] += 1
                            else:
                                logger.warning(f"User validation failed: {user.get('id', 'unknown')}")
                                
                        except Exception as e:
                            error_msg = f"Error processing user {user.get('id', 'unknown')}: {e}"
                            logger.error(error_msg)
                            stats['errors'].append(error_msg)
                            stats['total_errors'] += 1
                            continue
                    
                    # Save processed users in batches
                    if processed_users:
                        from ingestion.models.callrail import CallRail_User
                        save_stats = await self.bulk_save_records(
                            processed_users,
                            CallRail_User,
                            'id'
                        )
                        stats['total_created'] += save_stats['created']
                        stats['total_updated'] += save_stats['updated']

                    processed_count += len(users_batch)

                    # Check max_records limit
                    if max_records > 0 and processed_count >= max_records:
                        logger.info(f"Reached max_records={max_records}; stopping.")
                        break

            # Calculate duration
            end_time = timezone.now()
            stats['duration'] = (end_time - stats['start_time'])
            stats['success'] = True

            # Update SyncHistory record with completion status
            @sync_to_async
            def complete_sync_history():
                sync_history.end_time = end_time
                sync_history.status = 'success'
                sync_history.records_processed = stats['total_processed']
                sync_history.records_created = stats['total_created']
                sync_history.records_updated = stats['total_updated']
                sync_history.records_failed = stats['total_errors']
                sync_history.performance_metrics = {
                    'duration_seconds': stats['duration'].total_seconds(),
                    'records_per_second': stats['total_processed'] / max(stats['duration'].total_seconds(), 1),
                    'total_fetched': stats['total_fetched']
                }
                sync_history.save()
                return sync_history

            await complete_sync_history()
            logger.info(f"Users sync completed: processed={stats['total_processed']}, created={stats['total_created']}, updated={stats['total_updated']}, errors={stats['total_errors']}")
            return stats
            
        except Exception as e:
            # Calculate duration for failed sync
            end_time = timezone.now()
            stats['duration'] = (end_time - stats['start_time'])
            error_msg = f"Users sync failed: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            stats['success'] = False

            # Update SyncHistory record with failure status
            @sync_to_async
            def fail_sync_history():
                sync_history.end_time = end_time
                sync_history.status = 'failed'
                sync_history.error_message = str(e)
                sync_history.records_processed = stats['total_processed']
                sync_history.records_created = stats['total_created']
                sync_history.records_updated = stats['total_updated']
                sync_history.records_failed = stats['total_errors']
                sync_history.save()

            await fail_sync_history()
            return stats
