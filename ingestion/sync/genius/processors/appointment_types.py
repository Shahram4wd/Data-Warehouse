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
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw appointment type data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Appointment type-specific transformations
        
        # Convert is_active flag to boolean if needed
        if 'is_active' in record:
            record['is_active'] = bool(record['is_active'])
        
        return record
