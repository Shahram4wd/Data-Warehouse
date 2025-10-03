"""
Integration Field processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator, GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusIntegrationFieldProcessor(GeniusBaseProcessor):
    """Processor for Genius integration field data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean integration field record data"""
        
        # Use the record validator from validators.py
        validated = GeniusRecordValidator.validate_integration_field_record(record_data)
        
        # Convert timezone awareness for datetime fields
        for date_field in ['created_at', 'updated_at']:
            if validated.get(date_field):
                validated[date_field] = self.convert_timezone_aware(validated[date_field])
        
        # Ensure we have required fields
        if validated.get('id') is None:
            raise ValueError("Integration field must have an id")
        
        if not validated.get('definition_id'):
            raise ValueError("Integration field must have a definition_id")
        
        # Validate field_value length
        field_value = validated.get('field_value')
        if field_value and len(field_value) > 128:
            logger.warning(f"Truncating field_value from {len(field_value)} to 128 characters for record {validated.get('id')}")
            validated['field_value'] = field_value[:128]
        
        return validated
    
    def process_batch(self, records: List[Dict[str, Any]], force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of integration field records using bulk operations
        
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
                logger.error(f"Validation failed for integration field record {record.get('id', 'unknown')}: {e}")
                stats['errors'] += 1
                continue
        
        if not validated_records:
            return stats
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(validated_records)} integration fields")
            stats['created'] = len(validated_records)
            return stats
        
        # Perform bulk operations
        logger.info(f"Bulk processing {len(validated_records)} integration fields (force_overwrite={force_overwrite})")
        
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
                        'definition_id', 'user_id', 'division_id', 'field_value',
                        'created_at', 'updated_at'
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
    
    def _validate_integration_field_business_rules(self, record: Dict[str, Any]) -> List[str]:
        """Validate integration field-specific business rules"""
        errors = []
        
        # Either user_id or division_id should be set (not both)
        user_id = record.get('user_id')
        division_id = record.get('division_id')
        
        if user_id and division_id:
            errors.append("Integration field cannot have both user_id and division_id set")
        
        if not user_id and not division_id:
            errors.append("Integration field must have either user_id or division_id set")
        
        # Validate field_value if present
        field_value = record.get('field_value')
        if field_value is not None:
            if not isinstance(field_value, str):
                errors.append("field_value must be a string")
            elif len(field_value) > 128:
                errors.append(f"field_value length ({len(field_value)}) exceeds maximum of 128 characters")
        
        return errors
    
    def transform_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform integration field record data"""
        
        # Start with validated record
        validated = self.validate_record(record_data)
        
        # Additional transformations specific to integration fields
        
        # Ensure boolean fields are proper booleans
        # (None for this table, but keeping pattern consistent)
        
        # Clean string fields
        for string_field in ['field_value']:
            if validated.get(string_field):
                validated[string_field] = str(validated[string_field]).strip()
        
        # Convert empty strings to None for nullable fields
        for nullable_field in ['user_id', 'division_id', 'field_value']:
            if validated.get(nullable_field) == '':
                validated[nullable_field] = None
        
        # Ensure integer fields are proper integers
        for int_field in ['id', 'definition_id', 'user_id', 'division_id']:
            if validated.get(int_field) is not None:
                try:
                    validated[int_field] = int(validated[int_field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid integer value for {int_field}: {validated.get(int_field)}")
                    if int_field in ['id', 'definition_id']:
                        raise ValueError(f"Required field {int_field} must be a valid integer")
                    else:
                        validated[int_field] = None
        
        return validated
    
    def get_lookup_fields(self) -> List[str]:
        """Get fields used for record lookup/uniqueness"""
        return ['id']
    
    def get_update_fields(self) -> List[str]:
        """Get fields that should be updated during sync"""
        return [
            'definition_id', 'user_id', 'division_id', 'field_value',
            'created_at', 'updated_at'
        ]