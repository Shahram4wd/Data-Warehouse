"""
Division Group processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusDivisionGroupProcessor(GeniusBaseProcessor):
    """Processor for Genius division group data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean division group record data"""
        
        validated = {}
        
        # Validate each field using GeniusValidator
        validated['genius_id'] = GeniusValidator.validate_id_field(record_data.get('id'))
        validated['name'] = GeniusValidator.validate_string_field(record_data.get('name'), max_length=255, required=True)
        validated['code'] = GeniusValidator.validate_string_field(record_data.get('code'), max_length=50)
        validated['active'] = GeniusValidator.validate_boolean_field(record_data.get('active'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record_data.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record_data.get('updated_at'))
        
        # Convert timezone awareness
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('genius_id'):
            raise ValueError("Division group must have a genius_id")
        
        if not validated.get('name'):
            raise ValueError("Division group must have a name")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw division group data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Division group-specific transformations
        
        # Convert active flag to boolean
        if 'active' in record:
            record['active'] = bool(record['active'])
        
        return record
