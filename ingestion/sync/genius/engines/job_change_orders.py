"""
Job Change Order sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.job_change_orders import GeniusJobChangeOrderClient
from ..processors.job_change_orders import GeniusJobChangeOrderProcessor
from ingestion.models import Genius_JobChangeOrder

logger = logging.getLogger(__name__)


class GeniusJobChangeOrdersSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius job change order data"""
    
    def __init__(self):
        super().__init__('job_change_orders')
        self.client = GeniusJobChangeOrderClient()
        self.processor = GeniusJobChangeOrderProcessor(Genius_JobChangeOrder)
    
    async def sync_job_change_orders(self, since_date=None, force_overwrite=False, 
                                   dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for job change orders"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get job change orders from source
            raw_data = await sync_to_async(self.client.get_job_change_orders)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_data)} job change orders from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process job change orders but making no changes")
                stats['total_processed'] = len(raw_data)
                return stats
            
            # Process records in batches
            batch_size = 100
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i + batch_size]
                batch_stats = await self._process_job_change_order_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Job change order sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Job change order sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_job_change_order_batch(self, batch: List[tuple], field_mapping: List[str], 
                                      force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of job change order records"""
        
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
                logger.error(f"Error processing job change order record {raw_record}: {e}")
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
        
        logger.info(f"Bulk upserting {len(records)} job change order records (force={force})")
        
        # Prepare model instances
        model_instances = []
        for record in records:
            instance = Genius_JobChangeOrder(**record)
            model_instances.append(instance)
        
        with transaction.atomic():
            # Get existing IDs BEFORE the operation to calculate created vs updated
            existing_ids = set(
                Genius_JobChangeOrder.objects.filter(
                    id__in=[r['id'] for r in records]
                ).values_list('id', flat=True)
            )
            
            if force:
                # Force mode: overwrite all fields including sync timestamps
                Genius_JobChangeOrder.objects.bulk_create(
                    model_instances,
                    batch_size=100,
                    update_conflicts=True,
                    unique_fields=['id'],
                    update_fields=[
                        'job_id', 'number', 'status_id', 'type_id', 'adjustment_change_order_id',
                        'effective_date', 'total_amount', 'add_user_id', 'add_date',
                        'sold_user_id', 'sold_date', 'cancel_user_id', 'cancel_date',
                        'reason_id', 'envelope_id', 'total_contract_amount', 
                        'total_pre_change_orders_amount', 'signer_name', 'signer_email',
                        'financing_note', 'updated_at', 'sync_created_at', 'sync_updated_at'
                    ]
                )
                logger.info(f"Force mode: completely overwriting records")
            else:
                # Normal mode: standard upsert, preserve sync timestamps
                Genius_JobChangeOrder.objects.bulk_create(
                    model_instances,
                    batch_size=100,
                    update_conflicts=True,
                    unique_fields=['id'],
                    update_fields=[
                        'job_id', 'number', 'status_id', 'type_id', 'adjustment_change_order_id',
                        'effective_date', 'total_amount', 'add_user_id', 'add_date',
                        'sold_user_id', 'sold_date', 'cancel_user_id', 'cancel_date',
                        'reason_id', 'envelope_id', 'total_contract_amount', 
                        'total_pre_change_orders_amount', 'signer_name', 'signer_email',
                        'financing_note', 'updated_at'
                    ]
                )
            
            # Calculate created vs updated counts
            created_count = len([r for r in records if r['id'] not in existing_ids])
            updated_count = len(records) - created_count
        
        logger.info(f"Bulk upsert completed: {created_count} created, {updated_count} updated")
        return {'created': created_count, 'updated': updated_count}

