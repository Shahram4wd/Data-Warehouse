"""
CallRail form submissions data processor
"""
import logging
from typing import Dict, Any
from datetime import datetime
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class FormSubmissionsProcessor(CallRailBaseProcessor):
    """Processor for CallRail form submissions data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_FormSubmission
        super().__init__(model_class=CallRail_FormSubmission, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'company_id': 'company_id',
            'person_id': 'person_id',
            'form_url': 'form_url',
            'landing_page_url': 'landing_page_url',
            'form_data': 'form_data',
            'submission_time': 'submission_time',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail form submission record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Handle datetime fields
                    if source_field == 'submission_time' and value:
                        if isinstance(value, str):
                            try:
                                # Parse ISO datetime string
                                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except ValueError:
                                logger.warning(f"Invalid datetime format: {value}")
                                value = None
                    
                    # Handle JSON fields
                    elif source_field == 'form_data' and value is not None:
                        # Ensure form_data is a dict
                        if not isinstance(value, dict):
                            logger.warning(f"Form data is not a dict: {type(value)}")
                            value = {}
                    
                    transformed[target_field] = value
            
            # Ensure required fields have default values
            if 'form_data' not in transformed or transformed['form_data'] is None:
                transformed['form_data'] = {}
                
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming form submission record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed form submission record"""
        try:
            # Check required fields
            required_fields = ['id', 'company_id', 'form_url', 'submission_time', 'form_data']
            for field in required_fields:
                if field not in record or record[field] is None:
                    logger.warning(f"Missing required field '{field}' in form submission record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid form submission ID (empty)")
                return False
            
            # Validate submission_time is a datetime
            if not isinstance(record['submission_time'], datetime):
                logger.warning("Invalid submission_time (not datetime)")
                return False
                
            # Validate form_data is a dict
            if not isinstance(record['form_data'], dict):
                logger.warning("Invalid form_data (not dict)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating form submission record: {e}")
            return False
