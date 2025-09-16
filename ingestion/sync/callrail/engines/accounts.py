"""
CallRail accounts sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.db import transaction
from asgiref.sync import sync_to_async
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
    
    @sync_to_async
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get last successful SyncHistory end_time for delta sync"""
        from ingestion.models.common import SyncHistory
        last = (SyncHistory.objects
                .filter(crm_source='callrail', sync_type='accounts', status='success')
                .order_by('-end_time')
                .first())
        return last.end_time if last else None
    
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
            async with AccountsClient() as client:
                # Determine delta vs full
                since_date = kwargs.get('since_date')
                force = kwargs.get('force', False)
                full_sync = kwargs.get('full_sync', False)

                if not since_date and not full_sync and not force:
                    since_date = await self.get_last_sync_timestamp()
                    if since_date:
                        logger.info(f"Delta sync since: {since_date}")

                # Build API params
                api_params = {}
                if self.batch_size:
                    api_params['per_page'] = int(self.batch_size)

                max_records = kwargs.get('max_records') or 0
                processed_total = 0

                async for accounts_batch in client.fetch_accounts(
                    since_date=since_date,
                    **api_params
                ):
                    if not accounts_batch:
                        continue

                    # Enforce max_records across batches
                    if max_records and (processed_total + len(accounts_batch)) > max_records:
                        take = max_records - processed_total
                        if take <= 0:
                            break
                        accounts_batch = accounts_batch[:take]

                    sync_stats['total_fetched'] += len(accounts_batch)

                    logger.info(f"Processing {len(accounts_batch)} accounts...")

                    # Transform/validate
                    processed_accounts = []
                    for account in accounts_batch:
                        try:
                            transformed = self.processor.transform_record(account)
                            if self.processor.validate_record(transformed):
                                processed_accounts.append(transformed)
                            else:
                                logger.warning(f"Account validation failed: {account.get('id', 'unknown')}")
                        except Exception as e:
                            error_msg = f"Error processing account {account.get('id', 'unknown')}: {e}"
                            logger.error(error_msg)
                            sync_stats['errors'].append(error_msg)

                    # Save
                    if processed_accounts and not getattr(self, 'dry_run', False):
                        from ingestion.models.callrail import CallRail_Account
                        if force:
                            # emulate overwrite: delete then recreate keys in this chunk
                            # reuse bulk_save_records upsert (safe), or implement custom if needed later
                            save_stats = await self.bulk_save_records(processed_accounts, CallRail_Account, 'id')
                        else:
                            save_stats = await self.bulk_save_records(processed_accounts, CallRail_Account, 'id')
                        sync_stats['total_created'] += save_stats.get('created', 0)
                        sync_stats['total_updated'] += save_stats.get('updated', 0)

                    processed_total += len(accounts_batch)

                    if max_records and processed_total >= max_records:
                        logger.info(f"Reached max_records={max_records}; stopping.")
                        break

                logger.info(f"Accounts sync completed: {sync_stats}")
                return sync_stats
                
        except Exception as e:
            error_msg = f"Accounts sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
