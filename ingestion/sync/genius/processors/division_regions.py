"""
Division Region processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusDivisionRegionProcessor(GeniusBaseProcessor):
    """Processor for Genius division region data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> bool:
        """Validate division region record data"""
        
        try:
            # Ensure we have required fields
            if not record_data.get('id'):
                logger.warning("Division region missing required id field")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating division region record: {e}")
            return False
    
    def transform_record(self, raw_data: Dict[str, Any], field_mapping: List[str] = None) -> Dict[str, Any]:
        """Transform raw division region data to dictionary"""
        
        # If raw_data is already a dict, use it directly
        if isinstance(raw_data, dict):
            record = raw_data
        else:
            # Use base class transformation for tuple to dict conversion
            record = super().transform_record(raw_data, field_mapping)
        
        # Division region-specific transformations
        transformed = {}
        
        # Validate each field based on actual model structure
        transformed['id'] = GeniusValidator.validate_id_field(record.get('id'))
        transformed['name'] = GeniusValidator.validate_string_field(record.get('name'), max_length=64)
        transformed['is_active'] = GeniusValidator.validate_boolean_field(record.get('is_active'))
        
        # Convert is_active flag to boolean if needed
        if 'is_active' in transformed and transformed['is_active'] is not None:
            transformed['is_active'] = bool(transformed['is_active'])
        else:
            transformed['is_active'] = True  # Default value
        
        return transformed
