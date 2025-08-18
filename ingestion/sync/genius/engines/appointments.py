"""
Genius Appointments Sync Engine
Orchestrates the synchronization of appointments data from Genius to local database
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ingestion.sync.genius.engines.base import GeniusBaseSyncEngine
from ingestion.sync.genius.clients.appointments import GeniusAppointmentsClient
from ingestion.sync.genius.processors.appointments import GeniusAppointmentsProcessor

logger = logging.getLogger(__name__)


class GeniusAppointmentsSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius appointments"""
    
    def __init__(self):
        super().__init__(entity_type="appointments")
        self.client = GeniusAppointmentsClient()
        self.processor = GeniusAppointmentsProcessor()
    
    async def execute_sync(self,
                          full: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the appointments sync process"""
        
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
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
            
            logger.info(f"Starting Genius appointments sync with strategy: {sync_strategy}")
            if dry_run:
                logger.warning("🔍 DRY RUN MODE - No database changes will be made")
            
            # Get total count for progress tracking
            total_count = self.client.get_appointments_count(
                since=effective_since,
                start_date=start_date,
                end_date=end_date
            )
            
            if max_records and max_records < total_count:
                total_count = max_records
                logger.info(f"Limiting to {max_records} records (max_records parameter)")
            
            logger.info(f"Total records to process: {total_count}")
            
            if total_count == 0:
                total_stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
            else:
                # Get the data
                raw_data = self.client.get_appointments(
                    since=effective_since,
                    start_date=start_date,
                    end_date=end_date,
                    limit=max_records
                )
                
                # Process in batches
                total_stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
                batch_size = 500
                
                for i in range(0, len(raw_data), batch_size):
                    batch = raw_data[i:i + batch_size]
                    batch_stats = await self.processor.process_batch(batch, dry_run)
                    
                    # Update totals
                    for key, value in batch_stats.items():
                        total_stats[key] += value
                    
                    total_stats['processed'] += len(batch)
                    logger.info(f"Processed batch: {len(batch)} records, Total: {total_stats['processed']}/{total_count}")
            
            # Complete sync record
            await self.complete_sync_record(sync_record, total_stats)
            
            logger.info(f"Completed Genius appointments sync: {total_stats['created']} created, "
                       f"{total_stats['updated']} updated, {total_stats['errors']} errors")
            
            return {
                'success': True,
                'stats': total_stats,
                'sync_id': sync_record.id,
                'strategy': sync_strategy
            }
            
        except Exception as e:
            # Mark sync as failed
            error_msg = f"Genius appointments sync failed: {str(e)}"
            await self.complete_sync_record(sync_record, {'processed': 0, 'errors': 1}, error_msg)
            logger.error(error_msg)
            raise
