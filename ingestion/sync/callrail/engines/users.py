"""
CallRail users sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import CallRailBaseSyncEngine
from ..clients.users import UsersClient
from ..processors.users import UsersProcessor

logger = logging.getLogger(__name__)


class UsersSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail users"""
    
    def __init__(self, account_id: str, **kwargs):
        super().__init__(account_id=account_id, **kwargs)
        self.client = UsersClient()
        self.processor = UsersProcessor()
        self.entity_name = "users"
    
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for users"""
        from ingestion.models.callrail import CallRail_User
        latest_user = (CallRail_User.objects
                      .order_by('-updated_at')
                      .first())
        return latest_user.updated_at if latest_user else None
    
    async def sync_users(self, **kwargs) -> Dict[str, Any]:
        """Sync users from CallRail API"""
        logger.info(f"Starting users sync for account {self.account_id}")
        
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
            
            # Fetch users data
            async for users_batch in self.client.fetch_users(
                account_id=self.account_id,
                since_date=since_date,
                **kwargs
            ):
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
