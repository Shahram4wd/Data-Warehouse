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
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_integration_field_record(record_data)
        
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