"""
Integration Field Definition processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator, GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusIntegrationFieldDefinitionProcessor(GeniusBaseProcessor):
    """Processor for Genius integration field definition data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean integration field definition record data"""
        
        # Use the record validator from validators.py
        validated = GeniusRecordValidator.validate_integration_field_definition_record(record_data)
        
        # Note: This table has no timestamp fields to convert
        
        # Ensure we have required fields
        if validated.get('id') is None:
            raise ValueError("Integration field definition must have an id")
        
        if not validated.get('integration_id'):
            raise ValueError("Integration field definition must have an integration_id")
        
        if not validated.get('label'):
            raise ValueError("Integration field definition must have a label")
        
        if not validated.get('key_name'):
            raise ValueError("Integration field definition must have a key_name")
        
        # Validate field lengths
        label = validated.get('label')
        if label and len(label) > 32:
            logger.warning(f"Truncating label from {len(label)} to 32 characters for record {validated.get('id')}")
            validated['label'] = label[:32]
        
        key_name = validated.get('key_name')
        if key_name and len(key_name) > 64:
            logger.warning(f"Truncating key_name from {len(key_name)} to 64 characters for record {validated.get('id')}")
            validated['key_name'] = key_name[:64]
        
        hint = validated.get('hint')
        if hint and len(hint) > 255:
            logger.warning(f"Truncating hint from {len(hint)} to 255 characters for record {validated.get('id')}")
            validated['hint'] = hint[:255]
        
        input_type = validated.get('input_type')
        if input_type and len(input_type) > 50:
            logger.warning(f"Truncating input_type from {len(input_type)} to 50 characters for record {validated.get('id')}")
            validated['input_type'] = input_type[:50]
        
        return validated
    
    def process_batch(self, records: List[Dict[str, Any]], force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of integration field definition records using bulk operations
        
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
                logger.error(f"Validation failed for integration field definition record {record.get('id', 'unknown')}: {e}")
                stats['errors'] += 1
                continue
        
        if not validated_records:
            return stats
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(validated_records)} integration field definitions")
            stats['created'] = len(validated_records)
            return stats
        
        # Perform bulk operations
        logger.info(f"Bulk processing {len(validated_records)} integration field definitions (force_overwrite={force_overwrite})")
        
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
                        'integration_id', 'label', 'key_name', 'is_user', 'is_division',
                        'hint', 'input_type'
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
    
    def _validate_integration_field_definition_business_rules(self, record: Dict[str, Any]) -> List[str]:
        """Validate integration field definition-specific business rules"""
        errors = []
        
        # Validate label
        label = record.get('label')
        if not label or not label.strip():
            errors.append("label cannot be empty")
        elif len(label) > 32:
            errors.append(f"label length ({len(label)}) exceeds maximum of 32 characters")
        
        # Validate key_name
        key_name = record.get('key_name')
        if not key_name or not key_name.strip():
            errors.append("key_name cannot be empty")
        elif len(key_name) > 64:
            errors.append(f"key_name length ({len(key_name)}) exceeds maximum of 64 characters")
        
        # Validate hint if present
        hint = record.get('hint')
        if hint and len(hint) > 255:
            errors.append(f"hint length ({len(hint)}) exceeds maximum of 255 characters")
        
        # Validate input_type if present
        input_type = record.get('input_type')
        if input_type and len(input_type) > 50:
            errors.append(f"input_type length ({len(input_type)}) exceeds maximum of 50 characters")
        
        # Validate boolean fields
        for bool_field in ['is_user', 'is_division']:
            value = record.get(bool_field)
            if value is not None and not isinstance(value, (bool, int)):
                errors.append(f"{bool_field} must be a boolean or integer (0/1)")
        
        return errors
    
    def transform_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform integration field definition record data"""
        
        # Start with validated record
        validated = self.validate_record(record_data)
        
        # Additional transformations specific to integration field definitions
        
        # Ensure boolean fields are proper booleans
        for bool_field in ['is_user', 'is_division']:
            if validated.get(bool_field) is not None:
                # Convert tinyint (0/1) to boolean
                value = validated[bool_field]
                if isinstance(value, int):
                    validated[bool_field] = bool(value)
                elif isinstance(value, str):
                    validated[bool_field] = value.lower() in ('true', '1', 'yes')
        
        # Clean string fields
        for string_field in ['label', 'key_name', 'hint', 'input_type']:
            if validated.get(string_field):
                validated[string_field] = str(validated[string_field]).strip()
        
        # Convert empty strings to None for nullable fields
        for nullable_field in ['hint', 'input_type']:
            if validated.get(nullable_field) == '':
                validated[nullable_field] = None
        
        # Ensure integer fields are proper integers
        for int_field in ['id', 'integration_id']:
            if validated.get(int_field) is not None:
                try:
                    validated[int_field] = int(validated[int_field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid integer value for {int_field}: {validated.get(int_field)}")
                    raise ValueError(f"Required field {int_field} must be a valid integer")
        
        return validated
    
    def get_lookup_fields(self) -> List[str]:
        """Get fields used for record lookup/uniqueness"""
        return ['id']
    
    def get_update_fields(self) -> List[str]:
        """Get fields that should be updated during sync"""
        return [
            'integration_id', 'label', 'key_name', 'is_user', 'is_division', 
            'hint', 'input_type'
        ]