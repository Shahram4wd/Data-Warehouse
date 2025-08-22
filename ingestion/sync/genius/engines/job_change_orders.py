"""
Job Change Order sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.job_change_orders import GeniusJobChangeOrderClient
from ..processors.job_change_orders import GeniusJobChangeOrderProcessor
from ingestion.models import (Genius_JobChangeOrder, Genius_Job, Genius_User,
                             Genius_JobChangeOrderType, Genius_JobChangeOrderStatus, 
                             Genius_JobChangeOrderReason)

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderSyncEngine(GeniusBaseSyncEngine):
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
            raw_job_change_orders = await sync_to_async(self.client.get_job_change_orders)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_job_change_orders)} job change orders from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process job change orders but making no changes")
                return stats
            
            # Process job change orders in batches
            batch_size = 500
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_job_change_orders), batch_size):
                batch = raw_job_change_orders[i:i + batch_size]
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
        
        # Preload lookup data for FK validation
        jobs = {j.genius_id: j for j in Genius_Job.objects.all()}
        users = {u.genius_id: u for u in Genius_User.objects.all()}
        
        # Try to get lookup tables, they may not exist yet
        change_order_types = {}
        change_order_statuses = {}
        change_order_reasons = {}
        
        try:
            change_order_types = {t.genius_id: t for t in Genius_JobChangeOrderType.objects.all()}
        except:
            logger.warning("Genius_JobChangeOrderType model not found, skipping type lookups")
            
        try:
            change_order_statuses = {s.genius_id: s for s in Genius_JobChangeOrderStatus.objects.all()}
        except:
            logger.warning("Genius_JobChangeOrderStatus model not found, skipping status lookups")
            
        try:
            change_order_reasons = {r.genius_id: r for r in Genius_JobChangeOrderReason.objects.all()}
        except:
            logger.warning("Genius_JobChangeOrderReason model not found, skipping reason lookups")
        
        with transaction.atomic():
            for raw_record in batch:
                try:
                    stats['total_processed'] += 1
                    
                    # Transform raw data to dict
                    record_data = self.processor.transform_record(raw_record, field_mapping)
                    
                    # Validate record
                    validated_data = self.processor.validate_record(record_data)
                    
                    # Skip if required data missing
                    if not validated_data.get('genius_id'):
                        logger.warning("Skipping job change order with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Validate required FK relationships exist
                    if validated_data.get('job_id') and validated_data['job_id'] not in jobs:
                        logger.warning(f"Job change order {validated_data['genius_id']} references non-existent job {validated_data['job_id']}")
                        stats['skipped'] += 1
                        continue
                    
                    # Get or create job change order
                    job_change_order, created = Genius_JobChangeOrder.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created job change order {job_change_order.genius_id}: {job_change_order.change_order_number}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_job_change_order(job_change_order, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(job_change_order, field, value)
                            job_change_order.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated job change order {job_change_order.genius_id}: {job_change_order.change_order_number}")
                        else:
                            stats['skipped'] += 1
                    
                    # Set relationships
                    if validated_data.get('job_id'):
                        job_change_order.job = jobs[validated_data['job_id']]
                    
                    if validated_data.get('requested_by_user_id') and validated_data['requested_by_user_id'] in users:
                        job_change_order.requested_by_user = users[validated_data['requested_by_user_id']]
                    
                    if validated_data.get('approved_by_user_id') and validated_data['approved_by_user_id'] in users:
                        job_change_order.approved_by_user = users[validated_data['approved_by_user_id']]
                    
                    # Set lookup table relationships if available
                    if validated_data.get('change_order_type_id') and validated_data['change_order_type_id'] in change_order_types:
                        job_change_order.change_order_type = change_order_types[validated_data['change_order_type_id']]
                    
                    if validated_data.get('change_order_status_id') and validated_data['change_order_status_id'] in change_order_statuses:
                        job_change_order.change_order_status = change_order_statuses[validated_data['change_order_status_id']]
                    
                    if validated_data.get('change_order_reason_id') and validated_data['change_order_reason_id'] in change_order_reasons:
                        job_change_order.change_order_reason = change_order_reasons[validated_data['change_order_reason_id']]
                    
                    job_change_order.save()
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing job change order record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_job_change_order(self, existing: Genius_JobChangeOrder, new_data: Dict[str, Any]) -> bool:
        """Check if job change order should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['change_order_number', 'description', 'amount', 'requested_date', 
                          'approved_date', 'completed_date', 'notes', 'job_id',
                          'change_order_type_id', 'change_order_status_id', 'change_order_reason_id',
                          'requested_by_user_id', 'approved_by_user_id']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
