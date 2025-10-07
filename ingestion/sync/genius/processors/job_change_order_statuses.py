"""
Job Change Order Status processor for data validation and transformation
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderStatusProcessor:
    """Processor for Job Change Order Status data validation and transformation"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def validate_record(self, record_tuple: tuple, field_mapping: List[str]) -> Optional[Dict[str, Any]]:
        """
        Validate and transform a single job change order status record following CRM sync guide patterns.
        
        Args:
            record_tuple: Raw database record as tuple
            field_mapping: Field names corresponding to tuple positions
            
        Returns:
            Validated dictionary record or None if invalid
        """
        if not record_tuple or len(record_tuple) != len(field_mapping):
            logger.error(f"Record length {len(record_tuple) if record_tuple else 0} does not match mapping length {len(field_mapping)}")
            return None
        
        # Convert tuple to dict using field mapping
        record_dict = dict(zip(field_mapping, record_tuple))
        
        # Basic validation
        if not record_dict.get('id'):
            logger.debug("Skipping record without id")
            return None
        
        # Transform and validate fields using simple conversions
        validated_record = {}
        
        # Required fields
        validated_record['id'] = int(record_dict.get('id')) if record_dict.get('id') else None
        if not validated_record['id']:
            return None
        
        # Optional fields with transformations
        validated_record['label'] = str(record_dict.get('label')).strip() if record_dict.get('label') else None
        
        # Handle is_selectable field (convert to boolean if needed)
        is_selectable_val = record_dict.get('is_selectable')
        if is_selectable_val is not None:
            if isinstance(is_selectable_val, bool):
                validated_record['is_selectable'] = 1 if is_selectable_val else 0
            else:
                validated_record['is_selectable'] = int(is_selectable_val) if str(is_selectable_val).isdigit() else 1
        else:
            validated_record['is_selectable'] = 1  # default value
        
        return validated_record
    
    def transform_record(self, raw_record: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """
        Transform raw record to dictionary format
        """
        return dict(zip(field_mapping, raw_record))
    
    def process_batch(self, records: List[Dict[str, Any]], force_overwrite: bool = False) -> Dict[str, int]:
        """
        Process a batch of job change order status records for database operations.
        
        Args:
            records: List of validated record dictionaries
            force_overwrite: Whether to force update existing records
            
        Returns:
            Dictionary with operation statistics
        """
        stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        if not records:
            return stats
        
        # Collect IDs for bulk existence check
        record_ids = [record['id'] for record in records]
        existing_ids = set(
            self.model_class.objects.filter(id__in=record_ids).values_list('id', flat=True)
        )
        
        # Separate records for create vs update
        create_records = []
        update_records = []
        
        for record in records:
            stats['processed'] += 1
            record_id = record['id']
            
            if record_id in existing_ids:
                if force_overwrite:
                    update_records.append(record)
                else:
                    stats['skipped'] += 1
                    logger.debug(f"Skipping existing job change order status ID {record_id}")
            else:
                create_records.append(record)
        
        # Bulk create new records
        if create_records:
            try:
                new_objects = [self.model_class(**record) for record in create_records]
                created_objects = self.model_class.objects.bulk_create(new_objects, ignore_conflicts=True)
                stats['created'] += len(created_objects)
                logger.info(f"Created {len(created_objects)} job change order status records")
            except Exception as e:
                logger.error(f"Error creating job change order status records: {e}")
                stats['errors'] += len(create_records)
        
        # Bulk update existing records
        if update_records:
            try:
                for record in update_records:
                    self.model_class.objects.filter(id=record['id']).update(**{
                        k: v for k, v in record.items() if k != 'id'
                    })
                stats['updated'] += len(update_records)
                logger.info(f"Updated {len(update_records)} job change order status records")
            except Exception as e:
                logger.error(f"Error updating job change order status records: {e}")
                stats['errors'] += len(update_records)
        
        return stats