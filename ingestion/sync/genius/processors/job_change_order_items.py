"""
Job Change Order Items processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

from .base import GeniusBaseProcessor
from ..validators import GeniusFieldValidator

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderItemProcessor(GeniusBaseProcessor):
    """Processor for Genius job change order item data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job change order item record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_job_change_order_item_record(record_data)
        
        # Additional processing
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Job change order item must have an id")
        
        if not validated.get('change_order_id'):
            raise ValueError("Job change order item must have a change_order_id")
            
        if validated.get('amount') is None:
            raise ValueError("Job change order item must have an amount")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job change order item data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job change order item-specific transformations
        
        # Convert amount to Decimal if it's not already
        if record.get('amount') is not None:
            try:
                record['amount'] = Decimal(str(record['amount']))
            except (ValueError, TypeError):
                logger.warning(f"Invalid amount value: {record.get('amount')}")
                record['amount'] = Decimal('0.00')
        
        # Ensure description is string or None
        if record.get('description') is not None:
            record['description'] = str(record['description']).strip()[:256]  # Limit to model max_length
            if not record['description']:
                record['description'] = None
        
        return record
