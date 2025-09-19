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
        
        # Validate each field based on actual model structure
        # Model fields: id, label, is_active
        validated['id'] = GeniusValidator.validate_id_field(record_data.get('id'))
        validated['label'] = GeniusValidator.validate_string_field(record_data.get('label'), max_length=50, required=True)
        validated['is_active'] = GeniusValidator.validate_boolean_field(record_data.get('is_active'))
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Appointment type must have an id")
        
        if not validated.get('label'):
            raise ValueError("Appointment type must have a label")
        
        
        return validated
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform appointment type record data"""
        
        # Apply basic transformations
        transformed = record.copy()
        
        # Convert is_active flag to boolean if needed
        if 'is_active' in transformed:
            transformed['is_active'] = bool(transformed['is_active'])
        
        # Ensure all required fields exist
        if 'id' not in transformed or transformed['id'] is None:
            raise ValueError("Appointment type record must have an id")
        
        return transformed
