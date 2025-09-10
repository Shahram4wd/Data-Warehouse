"""
job change order reasons sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.job_change_order_reasons import GeniusJobChangeOrderReasonClient
from ..processors.job_change_order_reasons import GeniusJobChangeOrderReasonProcessor
from ingestion.models import Genius_JobChangeOrderReason

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
    
    async def sync_job_change_order_reasons(self, since_date=None, force_overwrite=False, 
                           dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for job change order reasons
        
        Note: since_date is ignored as this table has no timestamp fields for delta sync.
        Always performs full sync of all records.
        """
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get job change order reasons from source (ignores since_date)
            raw_data = await sync_to_async(self.client.get_job_change_order_reasons)(
                since_date=None,  # Always None as delta sync not supported
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_data)} job change order reasons from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process job change order reasons but making no changes")
                stats['total_processed'] = len(raw_data)
                return stats
            
            # Process records in batches
            batch_size = 100
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i + batch_size]
                batch_stats = await self._process_job_change_order_reason_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Job change order reason sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Job change order reason sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_job_change_order_reason_batch(self, batch: List[tuple], field_mapping: List[str], 
                               force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of job change order reason records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Prepare data for bulk operations
        validated_records = []
        
        # First pass: transform and validate all records
        for raw_record in batch:
            try:
                stats['total_processed'] += 1
                
                # Transform raw data to dict
                record_data = self.processor.transform_record(raw_record, field_mapping)
                
                # Validate the record
                validated_record = self.processor.validate_record(record_data)
                
                validated_records.append(validated_record)
                
            except Exception as e:
                logger.error(f"Error processing job change order reason record {raw_record}: {e}")
                stats['errors'] += 1
                continue
        
        if validated_records:
            # Perform bulk upsert
            upsert_stats = self._bulk_upsert_records(validated_records, force_overwrite)
            stats['created'] += upsert_stats['created']
            stats['updated'] += upsert_stats['updated']
        
        return stats
    
    def _bulk_upsert_records(self, records: List[Dict[str, Any]], force: bool = False) -> Dict[str, int]:
        """Bulk upsert records with conflict resolution"""
        created_count = 0
        updated_count = 0
        
        if not records:
            return {'created': created_count, 'updated': updated_count}
        
        logger.info(f"Bulk upserting {len(records)} job change order reason records (force={force})")
        
        # Prepare model instances
        model_instances = []
        for record in records:
            instance = Genius_JobChangeOrderReason(**record)
            model_instances.append(instance)
        
        with transaction.atomic():
            # Get existing IDs BEFORE the operation to calculate created vs updated
            existing_ids = set(
                Genius_JobChangeOrderReason.objects.filter(
                    id__in=[r['id'] for r in records]
                ).values_list('id', flat=True)
            )
            
            if force:
                # Force mode: overwrite all fields including sync timestamps
                Genius_JobChangeOrderReason.objects.bulk_create(
                    model_instances,
                    batch_size=100,
                    update_conflicts=True,
                    unique_fields=['id'],
                    update_fields=['label', 'description', 'sync_created_at', 'sync_updated_at']
                )
                logger.info(f"Force mode: completely overwriting records")
            else:
                # Normal mode: standard upsert, preserve sync timestamps
                Genius_JobChangeOrderReason.objects.bulk_create(
                    model_instances,
                    batch_size=100,
                    update_conflicts=True,
                    unique_fields=['id'],
                    update_fields=['label', 'description']
                )
            
            # Calculate created vs updated counts
            created_count = len([r for r in records if r['id'] not in existing_ids])
            updated_count = len(records) - created_count
        
        logger.info(f"Bulk upsert completed: {created_count} created, {updated_count} updated")
        return {'created': created_count, 'updated': updated_count}

