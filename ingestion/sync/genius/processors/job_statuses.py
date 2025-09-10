"""
Job Status processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusJobStatusProcessor(GeniusBaseProcessor):
    """Processor for Genius job status data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job status record data"""
        
        validated = {}
        
        # Validate each field using GeniusValidator
        validated['id'] = GeniusValidator.validate_id_field(record_data.get('id'))
        validated['label'] = GeniusValidator.validate_string_field(record_data.get('label'), max_length=50)
        validated['is_system'] = GeniusValidator.validate_id_field(record_data.get('is_system'))
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Job status must have an id")
        
        # Convert is_system to int if it's not already
        if validated.get('is_system') is None:
            validated['is_system'] = 0
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job status data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job status-specific transformations
        
        # Convert is_system to int
        if 'is_system' in record and record['is_system'] is not None:
            record['is_system'] = int(record['is_system'])
        
        return record
