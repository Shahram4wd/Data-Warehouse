"""
Job Change Order Reasons processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

from .base import GeniusBaseProcessor
from ..validators import GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderReasonProcessor(GeniusBaseProcessor):
    """Processor for Genius job change order reason data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job change order reason record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_job_change_order_reason_record(record_data)
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Job change order reason must have an id")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job change order reason data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job change order reason-specific transformations
        
        # Ensure label is string or None
        if record.get('label') is not None:
            record['label'] = str(record['label']).strip()[:100]  # Limit to model max_length
            if not record['label']:
                record['label'] = None
        
        # Ensure description is string or None
        if record.get('description') is not None:
            record['description'] = str(record['description']).strip()[:255]  # Limit to model max_length
            if not record['description']:
                record['description'] = None
        
        return record
