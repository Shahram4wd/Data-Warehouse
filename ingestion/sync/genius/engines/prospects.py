"""
Prospects sync engine for Genius CRM
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from django.utils import timezone

from ingestion.sync.genius.engines.base import GeniusBaseSyncEngine
from ingestion.sync.genius.clients.prospects import GeniusProspectsClient
from ingestion.sync.genius.processors.prospects import GeniusProspectsProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class GeniusProspectsSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius prospects data"""
    
    def __init__(self):
        super().__init__('prospects')
        self.client = GeniusProspectsClient()
        self.processor = GeniusProspectsProcessor()
        self.batch_size = 500
    
    async def execute_sync(self, since: str = None, force_overwrite: bool = False, 
                          full: bool = False, dry_run: bool = False, 
                          max_records: int = 0, **kwargs) -> Dict[str, Any]:
        """Execute prospects sync with SyncHistory tracking"""
        
        # Create SyncHistory record at start
        configuration = {
            'since': since,
            'force_overwrite': force_overwrite,
            'full': full,
            'dry_run': dry_run,
            'max_records': max_records,
            'batch_size': self.batch_size
        }
        
        sync_record = await self.create_sync_record(configuration)
        
        stats = {
            'sync_history_id': sync_record.id,
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        try:
            # Determine sync strategy
            strategy = await self.determine_sync_strategy(since, force_overwrite, full)
            logger.info(f"Starting Genius prospects sync with strategy: {strategy['type']}")
            
            if dry_run:
                logger.warning("🔍 DRY RUN MODE - No database changes will be made")
            
            # Get record count for progress tracking
            total_records = self.client.get_record_count(strategy['since_date'])
            logger.info(f"Total records to process: {total_records:,}")
            
            if max_records > 0:
                total_records = min(total_records, max_records)
                logger.info(f"Limited to max_records: {total_records:,}")
            
            # Process records in batches
            offset = 0
            processed = 0
            
            while processed < total_records:
                current_batch_size = min(self.batch_size, total_records - processed)
                
                # Fetch batch from database
                batch_data = self.client.fetch_batch(
                    offset=offset,
                    batch_size=current_batch_size,
                    since_date=strategy['since_date']
                )
                
                if not batch_data:
                    break
                
                # Process batch
                batch_results = await self.processor.process_batch(
                    batch_data, 
                    force_overwrite=strategy['force_overwrite'],
                    dry_run=dry_run
                )
                
                # Update stats
                stats['total_processed'] += batch_results['processed']
                stats['created'] += batch_results['created'] 
                stats['updated'] += batch_results['updated']
                stats['errors'] += batch_results['errors']
                
                processed += len(batch_data)
                offset += current_batch_size
                
                logger.info(f"Processed batch: {len(batch_data)} records, "
                           f"Total: {stats['total_processed']:,}/{total_records:,}")
                
                # Check if we've hit max_records limit
                if max_records > 0 and stats['total_processed'] >= max_records:
                    break
            
            # Complete SyncHistory record with success
            await self.complete_sync_record(sync_record, stats)
            
            logger.info(f"Completed Genius prospects sync: "
                       f"{stats['created']} created, {stats['updated']} updated, "
                       f"{stats['errors']} errors")
            
            return stats
            
        except Exception as e:
            # Complete SyncHistory record with failure
            await self.complete_sync_record(sync_record, stats, str(e))
            logger.error(f"Genius prospects sync failed: {e}")
            raise
        finally:
            self.client.disconnect()
