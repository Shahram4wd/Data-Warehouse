"""
Lead processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusLeadProcessor(GeniusBaseProcessor):
    """Processor for Genius lead data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean lead record data"""
        
        validated = {}
        
        # Validate each field using GeniusValidator
        validated['genius_id'] = GeniusValidator.validate_id_field(record_data.get('id'))
        validated['first_name'] = GeniusValidator.validate_string_field(record_data.get('first_name'), max_length=100)
        validated['last_name'] = GeniusValidator.validate_string_field(record_data.get('last_name'), max_length=100)
        validated['email'] = GeniusValidator.validate_email_field(record_data.get('email'))
        validated['phone'] = GeniusValidator.validate_phone_field(record_data.get('phone'))
        validated['address'] = GeniusValidator.validate_string_field(record_data.get('address'), max_length=500)
        validated['city'] = GeniusValidator.validate_string_field(record_data.get('city'), max_length=100)
        validated['state'] = GeniusValidator.validate_string_field(record_data.get('state'), max_length=50)
        validated['zip_code'] = GeniusValidator.validate_string_field(record_data.get('zip_code'), max_length=20)
        validated['prospect_source_id'] = GeniusValidator.validate_id_field(record_data.get('prospect_source_id'))
        validated['user_id'] = GeniusValidator.validate_id_field(record_data.get('user_id'))
        validated['division_id'] = GeniusValidator.validate_id_field(record_data.get('division_id'))
        validated['notes'] = GeniusValidator.validate_string_field(record_data.get('notes'), max_length=2000)
        validated['status'] = GeniusValidator.validate_string_field(record_data.get('status'), max_length=50)
        validated['converted_to_prospect_id'] = GeniusValidator.validate_id_field(record_data.get('converted_to_prospect_id'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record_data.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record_data.get('updated_at'))
        
        # Convert timezone awareness
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('genius_id'):
            raise ValueError("Lead must have a genius_id")
        
        # At least first name or last name is required
        if not validated.get('first_name') and not validated.get('last_name'):
            logger.warning(f"Lead {validated.get('genius_id')} has no first or last name")
        
        # Validate business rules
        business_errors = GeniusRecordValidator.validate_business_rules('lead', validated)
        if business_errors:
            raise ValueError(f"Lead validation errors: {', '.join(business_errors)}")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw lead data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Lead-specific transformations
        
        # Handle NULL foreign keys
        for fk_field in ['prospect_source_id', 'user_id', 'division_id', 'converted_to_prospect_id']:
            if record.get(fk_field) == 0:
                record[fk_field] = None
        
        # Clean and standardize status
        if record.get('status'):
            record['status'] = str(record['status']).strip().lower()
        
        # Ensure we have some contact info
        if not record.get('email') and not record.get('phone'):
            logger.warning(f"Lead {record.get('id')} has no email or phone")
        
        return record
