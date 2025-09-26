"""
Job Change Order Reasons processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

from .base import GeniusBaseProcessor
from ..validators import GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderReasonProcessor(GeniusBaseProcessor):
    """Processor for Genius job change order reason data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job change order reason record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_job_change_order_reason_record(record_data)
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Job change order reason must have an id")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job change order reason data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job change order reason-specific transformations
        
        # Ensure label is string or None
        if record.get('label') is not None:
            record['label'] = str(record['label']).strip()[:100]  # Limit to model max_length
            if not record['label']:
                record['label'] = None
        
        # Ensure description is string or None
        if record.get('description') is not None:
            record['description'] = str(record['description']).strip()[:255]  # Limit to model max_length
            if not record['description']:
                record['description'] = None
        
        return record
    
    def process_batch(self, records: List[Dict[str, Any]], force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of job change order reason records using bulk operations
        
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
        
        # Transform and validate all records first
        validated_records = []
        field_mapping = ['id', 'label', 'description']  # Simple mapping for job change order reasons
        
        for record in records:
            try:
                # Transform if needed (convert from tuple if raw data)
                if isinstance(record, tuple):
                    record_dict = self.transform_record(record, field_mapping)
                else:
                    record_dict = record
                    
                validated_record = self.validate_record(record_dict)
                validated_records.append(validated_record)
                stats['total_processed'] += 1
            except Exception as e:
                logger.error(f"Validation failed for record {record}: {e}")
                stats['errors'] += 1
                continue
        
        if not validated_records:
            return stats
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(validated_records)} job change order reasons")
            stats['created'] = len(validated_records)
            return stats
        
        # Perform bulk operations
        logger.info(f"Bulk processing {len(validated_records)} job change order reason records (force_overwrite={force_overwrite})")
        
        try:
            from django.db import transaction
            
            with transaction.atomic():
                # Get existing IDs to calculate created vs updated
                existing_ids = set(
                    self.model_class.objects.filter(
                        id__in=[record['id'] for record in validated_records]
                    ).values_list('id', flat=True)
                )
                
                model_instances = [self.model_class(**record) for record in validated_records]
                
                if force_overwrite:
                    # Force mode: completely overwrite
                    self.model_class.objects.bulk_create(
                        model_instances,
                        update_conflicts=True,
                        unique_fields=['id'],
                        update_fields=['label', 'description', 'sync_created_at', 'sync_updated_at']
                    )
                else:
                    # Normal mode: preserve sync timestamps
                    self.model_class.objects.bulk_create(
                        model_instances,
                        update_conflicts=True, 
                        unique_fields=['id'],
                        update_fields=['label', 'description']
                    )
                
                # Calculate stats
                created_count = len([record for record in validated_records if record['id'] not in existing_ids])
                updated_count = len(validated_records) - created_count
                
                stats['created'] = created_count
                stats['updated'] = updated_count
                
                logger.info(f"Bulk operation completed - Created: {created_count}, Updated: {updated_count}")
                
        except Exception as e:
            logger.error(f"Bulk operation failed: {e}")
            stats['errors'] = len(validated_records)
            raise
        
        return stats
