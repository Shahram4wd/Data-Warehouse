"""
Genius Services Sync Engine
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..clients.services import GeniusServicesClient
from ..processors.services import GeniusServicesProcessor
from .base import GeniusBaseSyncEngine

logger = logging.getLogger(__name__)


class GeniusServicesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius services data"""
    
    def __init__(self):
        super().__init__(entity_type="services")
        self.client = GeniusServicesClient()
        self.processor = GeniusServicesProcessor()
    
    async def execute_sync(self, 
                          full: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the services sync process"""
        
        # Create sync record
        configuration = {
            'full': full,
            'since': since.isoformat() if since else None,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'max_records': max_records,
            'dry_run': dry_run
        }
        sync_record = await self.create_sync_record(configuration)
        
        try:
            # Determine sync strategy and build WHERE clause
            since_param = since.strftime('%Y-%m-%d %H:%M:%S') if since else None
            sync_strategy_result = await self.determine_sync_strategy(since_param, False, full)
            sync_strategy = sync_strategy_result['type']
            effective_since = sync_strategy_result.get('since_date')
            
            where_clause = self.build_where_clause(effective_since, start_date, end_date, sync_strategy)
            
            logger.info(f"Starting Genius services sync with strategy: {sync_strategy}")
            if dry_run:
                logger.warning("🔍 DRY RUN MODE - No database changes will be made")
            
            # Get total count
            total_count = self.client.get_total_count(where_clause)
            logger.info(f"Total records to process: {total_count:,}")
            
            # Apply max_records limit
            effective_limit = min(max_records, total_count) if max_records else total_count
            if max_records and max_records < total_count:
                logger.info(f"Limited to max_records: {effective_limit:,}")
            
            # Fetch data
            raw_data = self.client.fetch_data(where_clause, effective_limit)
            
            # Process in batches
            total_stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
            batch_size = 500
            
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i + batch_size]
                batch_stats = await self.processor.process_batch(batch, dry_run)
                
                # Update totals
                for key, value in batch_stats.items():
                    total_stats[key] += value
                
                logger.info(f"Processed batch: {len(batch)} records, Total: {total_stats['processed']}/{effective_limit}")
            
            # Complete sync record
            await self.complete_sync_record(sync_record, total_stats)
            
            logger.info(f"Completed Genius services sync: {total_stats['created']} created, "
                       f"{total_stats['updated']} updated, {total_stats['errors']} errors")
            
            return {
                'status': 'success',
                'sync_id': sync_record.id,
                'stats': total_stats,
                'sync_strategy': sync_strategy
            }
            
        except Exception as e:
            # Mark sync as failed
            error_msg = f"Genius services sync failed: {str(e)}"
            await self.complete_sync_record(sync_record, {'errors': 1}, error_msg)
            logger.error(error_msg)
            raise
    
    def build_where_clause(self, 
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          sync_strategy: str = None) -> str:
        """Build WHERE clause based on sync parameters"""
        conditions = []
        
        # Strategy-based filtering
        if sync_strategy == "incremental" and since:
            conditions.append(f"updated_at > '{since.strftime('%Y-%m-%d %H:%M:%S')}'")
        elif sync_strategy == "manual_since" and since:
            conditions.append(f"updated_at >= '{since.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        # Date range filtering
        if start_date:
            conditions.append(f"updated_at >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'")
        if end_date:
            conditions.append(f"updated_at <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        return " AND ".join(conditions) if conditions else ""
