"""
Appointment Outcome Type processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusAppointmentOutcomeTypeProcessor(GeniusBaseProcessor):
    """Processor for Genius appointment outcome type data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean appointment outcome type record data"""
        
        validated = {}
        
        # Validate each field using GeniusValidator - use exact model field names
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['label'] = GeniusValidator.validate_string_field(record.get('label'), max_length=50, required=True)
        validated['sort_idx'] = GeniusValidator.validate_id_field(record.get('sort_idx'))
        validated['is_active'] = GeniusValidator.validate_boolean_field(record.get('is_active'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        # Convert timezone awareness
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Appointment outcome type must have an id")
        
        if not validated.get('label'):
            raise ValueError("Appointment outcome type must have a label")
        
        # Handle NULL sort_idx
        if validated.get('sort_idx') is None:
            validated['sort_idx'] = 999  # Default sort order for null values
        
        # Default active flag if not set
        if validated.get('is_active') is None:
            validated['is_active'] = True
        
        return validated
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw appointment outcome type data to dictionary"""
        
        # Use direct record processing since input is already a dictionary
        transformed_record = record
        
        # No field name mapping needed since we're already selecting correct field names from database
        transformed_record = record
        
        # Convert active flag to boolean if needed
        if 'is_active' in transformed_record and transformed_record['is_active'] is not None:
            transformed_record['is_active'] = bool(transformed_record['is_active'])
        
        # Handle NULL sort_idx
        if transformed_record.get('sort_idx') is None:
            transformed_record['sort_idx'] = 999  # Default sort order for null values
        
        return transformed_record
