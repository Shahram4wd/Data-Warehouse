"""
Job change order statuses sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.job_change_order_statuses import GeniusJobChangeOrderStatusClient
from ..processors.job_change_order_statuses import GeniusJobChangeOrderStatusProcessor
from ingestion.models import Genius_JobChangeOrderStatus

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderStatusesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius job change order statuses data"""
    
    def __init__(self):
        super().__init__('job_change_order_statuses')
        self.client = GeniusJobChangeOrderStatusClient()
        self.processor = GeniusJobChangeOrderStatusProcessor(Genius_JobChangeOrderStatus)
    
    async def execute_sync(self, 
                          full: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False,
                          force_overwrite: bool = False,
                          **kwargs) -> Dict[str, Any]:
        """Execute sync operation"""
        
        logger.info(f"Starting {self.entity_type} sync (full={full}, dry_run={dry_run})")
        
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get total count for progress tracking  
            total_count = await sync_to_async(self.client.count_records)()
            logger.info(f"Total job change order statuses to process: {total_count:,}")
            
            if total_count == 0:
                logger.info("No job change order statuses to sync")
            else:
                # Get data from source
                raw_data = await sync_to_async(self.client.get_job_change_order_statuses)(
                    limit=max_records or 0
                )
                
                logger.info(f"Fetched {len(raw_data)} job change order statuses from Genius")
                
                if dry_run:
                    logger.info("DRY RUN: Would process job change order statuses but making no changes")
                    stats['processed'] = len(raw_data)
                else:
                    # Process records in batches
                    batch_size = 100
                    field_mapping = self.client.get_field_mapping()
                    
                    for i in range(0, len(raw_data), batch_size):
                        batch = raw_data[i:i + batch_size]
                        batch_stats = await self._process_batch(
                            batch, field_mapping, force_overwrite
                        )
                        
                        # Update overall stats
                        for key in stats:
                            stats[key] += batch_stats[key]
                        
                        logger.info(f"Processed batch {i//batch_size + 1}: "
                                  f"{batch_stats['created']} created, "
                                  f"{batch_stats['updated']} updated, "
                                  f"{batch_stats['errors']} errors")
            
            # Create sync history record using async-compatible method from base class
            configuration = {
                'full': full,
                'dry_run': dry_run,
                'max_records': max_records,
                'force_overwrite': force_overwrite
            }
            sync_history = await self.create_sync_record(configuration)
            
            # Complete the sync record with results using base class logic
            # Convert stats format for base class (expects 'total_processed' instead of 'processed')
            base_stats = {
                'total_processed': stats['processed'],
                'created': stats['created'],
                'updated': stats['updated'],
                'errors': stats['errors']
            }
            error_message = None if stats['errors'] == 0 else f"{stats['errors']} errors occurred"
            await self._complete_sync_record_async(sync_history, base_stats, error_message)
            
            logger.info(f"Job change order statuses sync completed. Total stats: {stats}")
            
            return {
                'stats': stats,
                'sync_id': sync_history.id
            }
            
        except Exception as e:
            logger.error(f"Job change order statuses sync failed: {str(e)}")
            raise
        finally:
            if hasattr(self.client, 'disconnect'):
                self.client.disconnect()
    
    @sync_to_async
    def _process_batch(self, batch: List[tuple], field_mapping: List[str], 
                      force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of job change order status records"""
        
        # Validate and transform records
        validated_records = []
        for raw_record in batch:
            validated_record = self.processor.validate_record(raw_record, field_mapping)
            if validated_record:
                validated_records.append(validated_record)
        
        # Process the batch
        return self.processor.process_batch(validated_records, force_overwrite)

