"""
Job Change Order Items processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

from .base import GeniusBaseProcessor
from ..validators import GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderItemProcessor(GeniusBaseProcessor):
    """Processor for Genius job change order item data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job change order item record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_job_change_order_item_record(record_data)
        
        # Additional processing
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Job change order item must have an id")
        
        if not validated.get('change_order_id'):
            raise ValueError("Job change order item must have a change_order_id")
            
        if validated.get('amount') is None:
            raise ValueError("Job change order item must have an amount")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job change order item data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job change order item-specific transformations
        
        # Convert amount to Decimal if it's not already
        if record.get('amount') is not None:
            try:
                record['amount'] = Decimal(str(record['amount']))
            except (ValueError, TypeError):
                logger.warning(f"Invalid amount value: {record.get('amount')}")
                record['amount'] = Decimal('0.00')
        
        # Ensure description is string or None
        if record.get('description') is not None:
            record['description'] = str(record['description']).strip()[:256]  # Limit to model max_length
            if not record['description']:
                record['description'] = None
        
        return record

    def process_batch(self, records: List[Dict[str, Any]], force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of job change order items records using bulk operations
        
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
            logger.info(f"DRY RUN: Would process {len(validated_records)} job change order items")
            stats['created'] = len(validated_records)
            return stats
        
        # Perform bulk operations
        logger.info(f"Bulk processing {len(validated_records)} job change order items (force_overwrite={force_overwrite})")
        
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
                    update_fields = ['change_order_id', 'description', 'amount', 'updated_at']
                    
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