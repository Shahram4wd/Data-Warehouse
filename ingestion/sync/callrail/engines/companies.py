"""
CallRail companies sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.companies import CompaniesClient
from ..processors.companies import CompaniesProcessor

logger = logging.getLogger(__name__)


class CompaniesSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail companies"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = CompaniesClient()
        self.processor = CompaniesProcessor()
        self.entity_name = "companies"
    
    @sync_to_async
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get the last sync timestamp for companies"""
        from ingestion.models.callrail import CallRail_Company
        latest_company = (CallRail_Company.objects
                         .order_by('-sync_updated_at')
                         .first())
        return latest_company.sync_updated_at if latest_company else None
    
    async def sync_companies(self, **kwargs) -> Dict[str, Any]:
        """Sync companies from CallRail API"""
        logger.info("Starting companies sync")
        
        sync_stats = {
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'errors': []
        }
        
        try:
            async with CompaniesClient() as client:
                # Get last sync timestamp for delta sync
                since_date = kwargs.get('since_date')
                if not since_date and not kwargs.get('force', False):
                    since_date = await self.get_last_sync_timestamp()
                    logger.info(f"Delta sync since: {since_date}")
                
                # Filter out boolean parameters that shouldn't go to API client
                client_kwargs = {k: v for k, v in kwargs.items() 
                               if k not in ['since_date', 'full_sync', 'force_overwrite', 'force'] and not isinstance(v, bool)}
                
                # Fetch companies data
                async for companies_batch in client.fetch_companies(
                    since_date=since_date,
                    **client_kwargs
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
