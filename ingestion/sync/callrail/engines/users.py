"""
CallRail users sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.users import UsersClient
from ..processors.users import UsersProcessor

logger = logging.getLogger(__name__)


class UsersSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail users"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = UsersClient()
        self.processor = UsersProcessor()
        self.entity_name = "users"
    
    @sync_to_async
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for users"""
        from ingestion.models.callrail import CallRail_User
        latest_user = (CallRail_User.objects
                      .order_by('-sync_updated_at')
                      .first())
        return latest_user.sync_updated_at if latest_user else None
    
    async def sync_users(self, **kwargs) -> Dict[str, Any]:
        """Sync users from CallRail API"""
        logger.info("Starting users sync")
        
        sync_stats = {
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'errors': []
        }
        
        try:
            # Use async context manager for client
            async with UsersClient() as client:
                # Filter out boolean parameters that shouldn't go to API client
                client_kwargs = {k: v for k, v in kwargs.items() 
                               if k not in ['full_sync', 'force_overwrite', 'force'] and not isinstance(v, bool)}
                
                # Fetch users data
                async for users_batch in client.fetch_users(**client_kwargs):
                    if not users_batch:
                        continue
                        
                    sync_stats['total_fetched'] += len(users_batch)
                    logger.info(f"Processing {len(users_batch)} users...")
                    
                    # Process users batch
                    processed_users = []
                    for user in users_batch:
                        try:
                            # Transform user data
                            transformed = self.processor.transform_record(user)
                            
                            # Validate transformed data
                            if self.processor.validate_record(transformed):
                                processed_users.append(transformed)
                                sync_stats['total_processed'] += 1
                            else:
                                logger.warning(f"User validation failed: {user.get('id', 'unknown')}")
                                
                        except Exception as e:
                            error_msg = f"Error processing user {user.get('id', 'unknown')}: {e}"
                            logger.error(error_msg)
                            sync_stats['errors'].append(error_msg)
                            continue
                    
                    # Save processed users
                    if processed_users:
                        from ingestion.models.callrail import CallRail_User
                        save_stats = await self.bulk_save_records(
                            processed_users,
                            CallRail_User,
                            'id'
                        )
                        sync_stats['total_created'] += save_stats['created']
                        sync_stats['total_updated'] += save_stats['updated']
            
            logger.info(f"Users sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            error_msg = f"Users sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
