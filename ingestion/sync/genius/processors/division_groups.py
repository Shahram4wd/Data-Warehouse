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
        
        # Validate each field based on actual model structure
        validated['id'] = GeniusValidator.validate_id_field(record_data.get('id'))
        validated['group_label'] = GeniusValidator.validate_string_field(record_data.get('group_label'), max_length=64, required=True)
        validated['region'] = GeniusValidator.validate_id_field(record_data.get('region')) or 1
        validated['default_time_zone_name'] = GeniusValidator.validate_string_field(record_data.get('default_time_zone_name'), max_length=64)
        validated['intern_payroll_start'] = GeniusValidator.validate_id_field(record_data.get('intern_payroll_start'))
        validated['painter_payroll_start'] = GeniusValidator.validate_id_field(record_data.get('painter_payroll_start'))
        validated['is_active'] = GeniusValidator.validate_boolean_field(record_data.get('is_active'))
        validated['cc_profile_id'] = GeniusValidator.validate_string_field(record_data.get('cc_profile_id'), max_length=32)
        validated['mes_profile_id'] = GeniusValidator.validate_string_field(record_data.get('mes_profile_id'), max_length=25)
        validated['mes_profile_key'] = GeniusValidator.validate_string_field(record_data.get('mes_profile_key'), max_length=50)
        validated['docusign_acct_id'] = GeniusValidator.validate_string_field(record_data.get('docusign_acct_id'), max_length=50)
        validated['paysimple_username'] = GeniusValidator.validate_string_field(record_data.get('paysimple_username'), max_length=20)
        validated['paysimple_secret'] = GeniusValidator.validate_string_field(record_data.get('paysimple_secret'), max_length=150)
        validated['hub_account_id'] = GeniusValidator.validate_id_field(record_data.get('hub_account_id'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record_data.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record_data.get('updated_at'))
        
        # Convert timezone awareness
        if validated.get('created_at'):
            validated['created_at'] = self.convert_timezone_aware(validated['created_at'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
        
        # Ensure we have required fields
        if not validated.get('id'):
            raise ValueError("Division group must have an id")
        
        if not validated.get('group_label'):
            raise ValueError("Division group must have a group_label")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw division group data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Division group-specific transformations
        
        # Convert is_active flag to boolean if needed
        if 'is_active' in record:
            record['is_active'] = bool(record['is_active'])
        
        return record
