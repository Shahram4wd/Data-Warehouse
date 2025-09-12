"""
Job Financing processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusJobFinancingProcessor(GeniusBaseProcessor):
    """Processor for Genius job financing data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> bool:
        """Validate job financing record data"""
        
        try:
            # Ensure we have required fields
            if not record_data.get('job_id'):
                logger.warning("Job financing missing required job_id field")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating job financing record: {e}")
            return False
    
    def transform_record(self, raw_data: Dict[str, Any], field_mapping: List[str] = None) -> Dict[str, Any]:
        """Transform raw job financing data to dictionary"""
        
        # If raw_data is already a dict, use it directly
        if isinstance(raw_data, dict):
            record = raw_data
        else:
            # Use base class transformation for tuple to dict conversion
            record = super().transform_record(raw_data, field_mapping)
        
        # Job financing-specific transformations
        transformed = {}
        
        # Validate each field based on actual model structure
        transformed['job_id'] = GeniusValidator.validate_id_field(record.get('job_id'))
        transformed['term_id'] = GeniusValidator.validate_id_field(record.get('term_id'))
        transformed['financed_amount'] = GeniusValidator.validate_decimal_field(record.get('financed_amount'), max_digits=9, decimal_places=2)
        transformed['max_financed_amount'] = GeniusValidator.validate_decimal_field(record.get('max_financed_amount'), max_digits=9, decimal_places=2)
        transformed['bid_rate'] = GeniusValidator.validate_decimal_field(record.get('bid_rate'), max_digits=5, decimal_places=3)
        transformed['commission_reduction'] = GeniusValidator.validate_decimal_field(record.get('commission_reduction'), max_digits=5, decimal_places=3)
        transformed['signed_on'] = GeniusValidator.validate_datetime_field(record.get('signed_on'))
        transformed['cancellation_period_expires_on'] = GeniusValidator.validate_datetime_field(record.get('cancellation_period_expires_on'))
        transformed['app_submission_date'] = GeniusValidator.validate_datetime_field(record.get('app_submission_date'))
        transformed['is_joint_application'] = GeniusValidator.validate_id_field(record.get('is_joint_application'))
        transformed['applicant'] = GeniusValidator.validate_string_field(record.get('applicant'), max_length=50)
        transformed['co_applicant'] = GeniusValidator.validate_string_field(record.get('co_applicant'), max_length=50)
        transformed['status'] = GeniusValidator.validate_id_field(record.get('status'))
        transformed['approved_on'] = GeniusValidator.validate_datetime_field(record.get('approved_on'))
        transformed['loan_expiration_date'] = GeniusValidator.validate_datetime_field(record.get('loan_expiration_date'))
        transformed['denied_on'] = GeniusValidator.validate_datetime_field(record.get('denied_on'))
        transformed['denied_by'] = GeniusValidator.validate_id_field(record.get('denied_by'))
        transformed['why_book'] = GeniusValidator.validate_string_field(record.get('why_book'))
        transformed['would_book'] = GeniusValidator.validate_id_field(record.get('would_book'))
        transformed['is_financing_factor'] = GeniusValidator.validate_id_field(record.get('is_financing_factor'))
        transformed['satisfied'] = GeniusValidator.validate_string_field(record.get('satisfied'))
        transformed['docs_completed'] = GeniusValidator.validate_datetime_field(record.get('docs_completed'))
        transformed['active_stipulation_notes'] = GeniusValidator.validate_string_field(record.get('active_stipulation_notes'))
        transformed['is_active_stipulations_cleared'] = GeniusValidator.validate_id_field(record.get('is_active_stipulations_cleared'))
        transformed['legal_app_name'] = GeniusValidator.validate_string_field(record.get('legal_app_name'), max_length=100)
        
        # Convert timezone awareness for datetime fields
        datetime_fields = ['signed_on', 'cancellation_period_expires_on', 'app_submission_date', 
                          'approved_on', 'loan_expiration_date', 'denied_on', 'docs_completed']
        
        for field in datetime_fields:
            if transformed.get(field):
                transformed[field] = self.convert_timezone_aware(transformed[field])
        
        # Set defaults for decimal fields if needed
        if transformed.get('financed_amount') is None:
            transformed['financed_amount'] = Decimal('0.00')
        if transformed.get('max_financed_amount') is None:
            transformed['max_financed_amount'] = Decimal('0.00')
        
        # Set defaults for small int fields if needed
        if transformed.get('is_joint_application') is None:
            transformed['is_joint_application'] = 0
        if transformed.get('status') is None:
            transformed['status'] = 1
        if transformed.get('is_active_stipulations_cleared') is None:
            transformed['is_active_stipulations_cleared'] = 0
        
        # Convert decimal fields
        decimal_fields = ['financed_amount', 'max_financed_amount', 'bid_rate', 'commission_reduction']
        for field in decimal_fields:
            if field in transformed and transformed[field] is not None:
                try:
                    transformed[field] = Decimal(str(transformed[field]))
                except (ValueError, TypeError):
                    transformed[field] = None
        
        # Convert small int fields
        small_int_fields = ['is_joint_application', 'status', 'would_book', 'is_financing_factor', 'is_active_stipulations_cleared']
        for field in small_int_fields:
            if field in transformed and transformed[field] is not None:
                try:
                    transformed[field] = int(transformed[field])
                except (ValueError, TypeError):
                    transformed[field] = None
        
        return transformed
