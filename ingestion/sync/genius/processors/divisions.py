"""
Division processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

from .base import GeniusBaseProcessor
from ..validators import GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusDivisionProcessor(GeniusBaseProcessor):
    """Processor for Genius division data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean division record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_division_record(record_data)
        
        # Additional processing
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Division must have an id")
        
        if not validated.get('label'):
            raise ValueError("Division must have a label")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw division data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Division-specific transformations
        
        # Convert active flag to boolean
        if 'active' in record:
            record['active'] = bool(record['active'])
        
        # Handle NULL division_group_id
        if record.get('division_group_id') == 0:
            record['division_group_id'] = None
        
        return record
