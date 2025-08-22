"""
Quote processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusQuoteProcessor(GeniusBaseProcessor):
    """Processor for Genius quote data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean quote record data"""
        
        validated = {}
        
        # Validate each field using GeniusValidator
        validated['genius_id'] = GeniusValidator.validate_id_field(record_data.get('id'))
        validated['prospect_id'] = GeniusValidator.validate_id_field(record_data.get('prospect_id'))
        validated['user_id'] = GeniusValidator.validate_id_field(record_data.get('user_id'))
        validated['division_id'] = GeniusValidator.validate_id_field(record_data.get('division_id'))
        validated['quote_number'] = GeniusValidator.validate_string_field(record_data.get('quote_number'), max_length=100)
        validated['quote_date'] = GeniusValidator.validate_datetime_field(record_data.get('quote_date'))
        validated['total_amount'] = GeniusValidator.validate_decimal_field(record_data.get('total_amount'), max_digits=10, decimal_places=2)
        validated['status'] = GeniusValidator.validate_string_field(record_data.get('status'), max_length=50)
        validated['notes'] = GeniusValidator.validate_string_field(record_data.get('notes'), max_length=2000)
        validated['valid_until'] = GeniusValidator.validate_datetime_field(record_data.get('valid_until'))
        validated['converted_to_job_id'] = GeniusValidator.validate_id_field(record_data.get('converted_to_job_id'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record_data.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record_data.get('updated_at'))
        
        # Convert timezone awareness
        for date_field in ['quote_date', 'valid_until', 'created_at', 'updated_at']:
            if validated.get(date_field):
                validated[date_field] = self.convert_timezone_aware(validated[date_field])
        
        # Ensure we have required fields
        if not validated.get('genius_id'):
            raise ValueError("Quote must have a genius_id")
        
        if not validated.get('prospect_id'):
            raise ValueError("Quote must have a prospect_id")
        
        # Validate business rules for quotes
        business_errors = self._validate_quote_business_rules(validated)
        if business_errors:
            raise ValueError(f"Quote validation errors: {', '.join(business_errors)}")
        
        return validated
    
    def _validate_quote_business_rules(self, record: Dict[str, Any]) -> List[str]:
        """Validate quote-specific business rules"""
        errors = []
        
        # Quote date should not be in future (with some tolerance)
        if record.get('quote_date'):
            from datetime import datetime, timedelta
            if record['quote_date'] > datetime.now() + timedelta(days=1):
                logger.warning(f"Quote {record.get('genius_id')} has future quote_date")
        
        # Valid until should be after quote date
        if (record.get('quote_date') and record.get('valid_until') and 
            record['valid_until'] < record['quote_date']):
            errors.append("Quote valid_until cannot be before quote_date")
        
        # Total amount should be positive
        if record.get('total_amount') and record['total_amount'] < 0:
            errors.append("Quote total_amount cannot be negative")
        
        return errors
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw quote data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Quote-specific transformations
        
        # Handle NULL foreign keys
        for fk_field in ['prospect_id', 'user_id', 'division_id', 'converted_to_job_id']:
            if record.get(fk_field) == 0:
                record[fk_field] = None
        
        # Clean quote_number
        if record.get('quote_number'):
            record['quote_number'] = str(record['quote_number']).strip()
        
        # Clean and standardize status
        if record.get('status'):
            record['status'] = str(record['status']).strip().lower()
        
        return record
