"""
Job processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusFieldValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusJobProcessor(GeniusBaseProcessor):
    """Processor for Genius job data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_job_record(record_data)
        
        # Convert timezone awareness
        if validated.get('add_date'):
            validated['add_date'] = self.convert_timezone_aware(validated['add_date'])
        
        if validated.get('updated_at'):
            validated['updated_at'] = self.convert_timezone_aware(validated['updated_at'])
            
        if validated.get('start_date'):
            validated['start_date'] = self.convert_timezone_aware(validated['start_date'])
            
        if validated.get('end_date'):
            validated['end_date'] = self.convert_timezone_aware(validated['end_date'])
        
        # Ensure we have required fields  
        if not validated.get('id'):
            raise ValueError("Job must have an id")
        
        # Validate business rules
        relationship_errors = GeniusRecordValidator.validate_required_relationships('job', validated)
        business_errors = GeniusRecordValidator.validate_business_rules('job', validated)
        
        all_errors = relationship_errors + business_errors
        if all_errors:
            raise ValueError(f"Job validation errors: {', '.join(all_errors)}")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job-specific transformations
        
        # Handle NULL foreign keys
        for fk_field in ['prospect_id', 'division_id', 'job_status_id']:
            if record.get(fk_field) == 0:
                record[fk_field] = None
        
        # Clean job_number
        if record.get('job_number'):
            record['job_number'] = str(record['job_number']).strip()
        
        return record
