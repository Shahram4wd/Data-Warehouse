"""
CallRail companies sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import CallRailBaseSyncEngine
from ..clients.companies import CompaniesClient
from ..processors.companies import CompaniesProcessor

logger = logging.getLogger(__name__)


class CompaniesSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail companies"""
    
    def __init__(self, account_id: str, **kwargs):
        super().__init__(account_id=account_id, **kwargs)
        self.client = CompaniesClient()
        self.processor = CompaniesProcessor()
        self.entity_name = "companies"
    
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for companies"""
        from ingestion.models.callrail import CallRail_Company
        latest_company = (CallRail_Company.objects
                         .filter(account_id=account_id)
                         .order_by('-updated_at')
                         .first())
        return latest_company.updated_at if latest_company else None
    
    async def sync_companies(self, **kwargs) -> Dict[str, Any]:
        """Sync companies from CallRail API"""
        logger.info(f"Starting companies sync for account {self.account_id}")
        
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
            
            # Fetch companies data
            async for companies_batch in self.client.fetch_companies(
                account_id=self.account_id,
                since_date=since_date,
                **kwargs
            ):
                if not companies_batch:
                    continue
                    
                sync_stats['total_fetched'] += len(companies_batch)
                logger.info(f"Processing {len(companies_batch)} companies...")
                
                # Process companies batch
                processed_companies = []
                for company in companies_batch:
                    try:
                        # Transform company data
                        transformed = self.processor.transform_record(company)
                        
                        # Validate transformed data
                        if self.processor.validate_record(transformed):
                            processed_companies.append(transformed)
                            sync_stats['total_processed'] += 1
                        else:
                            logger.warning(f"Company validation failed: {company.get('id', 'unknown')}")
                            
                    except Exception as e:
                        error_msg = f"Error processing company {company.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        sync_stats['errors'].append(error_msg)
                        continue
                
                # Save processed companies
                if processed_companies:
                    from ingestion.models.callrail import CallRail_Company
                    save_stats = await self.bulk_save_records(
                        processed_companies,
                        CallRail_Company,
                        'id'
                    )
                    sync_stats['total_created'] += save_stats['created']
                    sync_stats['total_updated'] += save_stats['updated']
            
            logger.info(f"Companies sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            error_msg = f"Companies sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
