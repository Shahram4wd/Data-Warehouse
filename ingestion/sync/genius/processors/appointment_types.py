"""
Appointment Type processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusAppointmentTypeProcessor(GeniusBaseProcessor):
    """Processor for Genius appointment type data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean appointment type record data"""
        
        validated = {}
        
        # Validate each field using GeniusValidator
        validated['genius_id'] = GeniusValidator.validate_id_field(record_data.get('id'))
        validated['name'] = GeniusValidator.validate_string_field(record_data.get('name'), max_length=255, required=True)
        validated['code'] = GeniusValidator.validate_string_field(record_data.get('code'), max_length=50)
        validated['description'] = GeniusValidator.validate_string_field(record_data.get('description'), max_length=1000)
        validated['duration_minutes'] = GeniusValidator.validate_id_field(record_data.get('duration_minutes'))
        validated['color'] = GeniusValidator.validate_string_field(record_data.get('color'), max_length=20)
        validated['active'] = GeniusValidator.validate_boolean_field(record_data.get('active'))
        validated['sort_order'] = GeniusValidator.validate_id_field(record_data.get('sort_order'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record_data.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record_data.get('updated_at'))
        
        # Convert timezone awareness
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('genius_id'):
            raise ValueError("Appointment type must have a genius_id")
        
        if not validated.get('name'):
            raise ValueError("Appointment type must have a name")
        
        # Validate business rules
        if validated.get('duration_minutes') and validated['duration_minutes'] <= 0:
            logger.warning(f"Appointment type {validated['genius_id']} has invalid duration: {validated['duration_minutes']}")
            validated['duration_minutes'] = 30  # Default to 30 minutes
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw appointment type data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Appointment type-specific transformations
        
        # Convert active flag to boolean
        if 'active' in record:
            record['active'] = bool(record['active'])
        
        # Handle NULL sort_order
        if record.get('sort_order') is None:
            record['sort_order'] = 999  # Default sort order for null values
        
        # Clean color field (remove # if present)
        if record.get('color'):
            color = str(record['color']).strip()
            if color.startswith('#'):
                color = color[1:]
            record['color'] = color
        
        return record
