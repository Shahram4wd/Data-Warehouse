"""
CallRail accounts sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import CallRailBaseSyncEngine
from ..clients.accounts import AccountsClient
from ..processors.accounts import AccountsProcessor

logger = logging.getLogger(__name__)


class AccountsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail accounts"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = AccountsClient()
        self.processor = AccountsProcessor()
        self.entity_name = "accounts"
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the last sync timestamp for accounts"""
        from ingestion.models.callrail import CallRail_Account
        latest_account = (CallRail_Account.objects
                         .order_by('-updated_at')
                         .first())
        return latest_account.updated_at if latest_account else None
    
    async def sync_accounts(self, **kwargs) -> Dict[str, Any]:
        """Sync accounts from CallRail API"""
        logger.info("Starting accounts sync")
        
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
                since_date = self.get_last_sync_timestamp()
                logger.info(f"Delta sync since: {since_date}")
            
            # Fetch accounts data
            async for accounts_batch in self.client.fetch_accounts(
                since_date=since_date,
                **kwargs
            ):
                if not accounts_batch:
                    continue
                    
                sync_stats['total_fetched'] += len(accounts_batch)
                logger.info(f"Processing {len(accounts_batch)} accounts...")
                
                # Process accounts batch
                processed_accounts = []
                for account in accounts_batch:
                    try:
                        # Transform account data
                        transformed = self.processor.transform_record(account)
                        
                        # Validate transformed data
                        if self.processor.validate_record(transformed):
                            processed_accounts.append(transformed)
                            sync_stats['total_processed'] += 1
                        else:
                            logger.warning(f"Account validation failed: {account.get('id', 'unknown')}")
                            
                    except Exception as e:
                        error_msg = f"Error processing account {account.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        sync_stats['errors'].append(error_msg)
                        continue
                
                # Save processed accounts
                if processed_accounts:
                    from ingestion.models.callrail import CallRail_Account
                    save_stats = await self.bulk_save_records(
                        processed_accounts,
                        CallRail_Account,
                        'id'
                    )
                    sync_stats['total_created'] += save_stats['created']
                    sync_stats['total_updated'] += save_stats['updated']
            
            logger.info(f"Accounts sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            error_msg = f"Accounts sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
