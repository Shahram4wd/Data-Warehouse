"""
Job Change Order Reasons sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.job_change_order_reasons import GeniusJobChangeOrderReasonClient
from ..processors.job_change_order_reasons import GeniusJobChangeOrderReasonProcessor
from ingestion.models import Genius_JobChangeOrderReason, SyncHistory

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderReasonsSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius job change order reasons data
    
    Note: This is a lookup table without timestamp fields, so delta sync is not supported.
    All syncs are full syncs regardless of the since_date parameter.
    """
    
    def __init__(self):
        super().__init__('job_change_order_reasons')
        self.client = GeniusJobChangeOrderReasonClient()
        self.processor = GeniusJobChangeOrderReasonProcessor(Genius_JobChangeOrderReason)
    
    def sync_job_change_order_reasons(self, since_date=None, force_overwrite=False, 
                                   dry_run=False, max_records=0, full_sync=False, **kwargs) -> Dict[str, Any]:
        """Main sync method for job change order reasons with SyncHistory tracking
        
        Note: Since this is a lookup table without timestamp fields, delta sync is not supported.
        Always performs full sync of all records.
        """
        
        # Create sync history record
        sync_history = SyncHistory.objects.create(
            crm_source='genius',
            sync_type='job_change_order_reasons',
            start_time=timezone.now(),
            status='running'
        )
        
        logger.info(f"🚀 Starting job change order reasons sync")
        logger.info(f"   📅 Since date: {since_date} (ignored - full sync only)")
        logger.info(f"   🔄 Force overwrite: {force_overwrite}")
        logger.info(f"   🧪 Dry run: {dry_run}")
        logger.info(f"   📊 Max records: {max_records or 'unlimited'}")
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get job change order reasons from source (always full sync)
            raw_data = self.client.get_job_change_order_reasons(
                since_date=None,  # Always None as delta sync not supported
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_data)} job change order reasons from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process job change order reasons but making no changes")
                stats['total_processed'] = len(raw_data)
                self.complete_sync_record(sync_history, stats)
                return stats
            
            # Process records using the processor
            if raw_data:
                processor_stats = self.processor.process_batch(raw_data, force_overwrite=force_overwrite)
                stats.update(processor_stats)
            
            logger.info(f"✅ Job change order reasons sync completed. Stats: {stats}")
            
            # Complete sync history with success
            self.complete_sync_record(sync_history, stats)
            return stats
            
        except Exception as e:
            logger.error(f"Job change order reasons sync failed: {str(e)}")
            # Complete sync history with failure
            self.complete_sync_record(sync_history, stats, error_message=str(e))
            raise


