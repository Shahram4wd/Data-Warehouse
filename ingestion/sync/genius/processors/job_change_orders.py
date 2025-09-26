"""
Job Change Order processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator, GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderProcessor(GeniusBaseProcessor):
    """Processor for Genius job change order data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job change order record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_job_change_order_record(record_data)
        
        # Convert timezone awareness for datetime fields
        for date_field in ['effective_date', 'add_date', 'sold_date', 'cancel_date', 'updated_at']:
            if validated.get(date_field):
                validated[date_field] = self.convert_timezone_aware(validated[date_field])
        
        # Ensure we have required fields
        if validated.get('id') is None:
            raise ValueError("Job change order must have an id")
        
        if not validated.get('job_id'):
            raise ValueError("Job change order must have a job_id")
        
        # Handle required fields that might be NULL in source but required in Django model
        if not validated.get('add_date') and validated.get('effective_date'):
            # If add_date is missing but effective_date exists, use effective_date
            validated['add_date'] = validated['effective_date']
        
        return validated
    
    def _validate_job_change_order_business_rules(self, record: Dict[str, Any]) -> List[str]:
        """Validate job change order-specific business rules"""
        errors = []
        
        # Requested date should not be in future
        requested_date = record.get('requested_date')
        if requested_date:
            from datetime import datetime, timedelta
            if requested_date > datetime.now() + timedelta(days=1):
                logger.warning(f"Job change order {record.get('genius_id')} has future requested_date")
        
        # Approved date should be after requested date
        approved_date = record.get('approved_date')
        if requested_date and approved_date and approved_date < requested_date:
            errors.append("Approved date cannot be before requested date")
        
        # Completed date should be after approved date
        completed_date = record.get('completed_date')
        if approved_date and completed_date and completed_date < approved_date:
            errors.append("Completed date cannot be before approved date")
        
        # Change order amount validation
        amount = record.get('amount')
        if amount is not None and amount == 0:
            logger.warning(f"Job change order {record.get('genius_id')} has zero amount")
        
        return errors
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job change order data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job change order-specific transformations
        
        # Handle NULL foreign keys
        for fk_field in ['job_id', 'change_order_type_id', 'change_order_status_id', 
                        'change_order_reason_id', 'requested_by_user_id', 'approved_by_user_id']:
            if record.get(fk_field) == 0:
                record[fk_field] = None
        
        # Clean change_order_number
        if record.get('change_order_number'):
            record['change_order_number'] = str(record['change_order_number']).strip()
        
        return record
    
    def process_batch(self, records: List[Dict[str, Any]], force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of job change order records using bulk operations
        
        Args:
            records: List of record dictionaries
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            
        Returns:
            Dictionary containing processing statistics
        """
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not records:
            return stats
        
        # Validate all records first
        validated_records = []
        for record in records:
            try:
                validated_record = self.validate_record(record)
                validated_records.append(validated_record)
                stats['total_processed'] += 1
            except Exception as e:
                logger.error(f"Validation failed for record {record}: {e}")
                stats['errors'] += 1
                continue
        
        if not validated_records:
            return stats
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(validated_records)} job change orders")
            stats['created'] = len(validated_records)
            return stats
        
        # Perform bulk operations
        logger.info(f"Bulk processing {len(validated_records)} job change orders (force_overwrite={force_overwrite})")
        
        try:
            # Use Django's bulk_create with update_conflicts for PostgreSQL
            from django.db import transaction
            
            with transaction.atomic():
                model_instances = [self.model_class(**record) for record in validated_records]
                
                if force_overwrite:
                    # Delete existing records first, then create new ones
                    existing_ids = [record['id'] for record in validated_records]
                    deleted_count = self.model_class.objects.filter(id__in=existing_ids).delete()[0]
                    logger.info(f"Deleted {deleted_count} existing records")
                    
                    # Create all records as new
                    created_objects = self.model_class.objects.bulk_create(model_instances)
                    stats['created'] = len(created_objects)
                    
                else:
                    # Use bulk_create with update_conflicts for upsert behavior
                    update_fields = [
                        'job_id', 'number', 'status_id', 'type_id', 'adjustment_change_order_id',
                        'effective_date', 'total_amount', 'add_user_id', 'add_date',
                        'sold_user_id', 'sold_date', 'cancel_user_id', 'cancel_date',
                        'reason_id', 'envelope_id', 'total_contract_amount', 
                        'total_pre_change_orders_amount', 'signer_name', 'signer_email',
                        'financing_note', 'updated_at'
                    ]
                    
                    # Get existing IDs to calculate created vs updated
                    existing_ids = set(
                        self.model_class.objects.filter(
                            id__in=[record['id'] for record in validated_records]
                        ).values_list('id', flat=True)
                    )
                    
                    created_objects = self.model_class.objects.bulk_create(
                        model_instances,
                        update_conflicts=True,
                        update_fields=update_fields,
                        unique_fields=['id']
                    )
                    
                    # Calculate created vs updated counts
                    total_processed = len(model_instances)
                    existing_count = len([r for r in validated_records if r['id'] in existing_ids])
                    stats['created'] = total_processed - existing_count
                    stats['updated'] = existing_count
            
            logger.info(f"Bulk operation completed - Created: {stats['created']}, Updated: {stats['updated']}")
            
        except Exception as e:
            logger.error(f"Bulk operation failed: {e}")
            stats['errors'] += len(validated_records)
            stats['created'] = 0
            stats['updated'] = 0
        
        return stats
