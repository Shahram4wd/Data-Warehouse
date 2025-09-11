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

    def process_batch(self, batch_data: List[tuple], field_mapping: Dict[str, int], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Process a batch of jobs data using bulk operations"""
        if not batch_data:
            return {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(batch_data)} job records")
            return {'total_processed': len(batch_data), 'created': len(batch_data), 'updated': 0, 'errors': 0}
        
        # Transform raw data to model instances
        records_to_create = []
        processed_ids = []
        
        for raw_record in batch_data:
            try:
                # Transform using field mapping (dict format)
                record_dict = {}
                for field_name, column_index in field_mapping.items():
                    if column_index < len(raw_record):
                        record_dict[field_name] = raw_record[column_index]
                
                # Validate and clean the record
                validated_record = self.validate_record(record_dict)
                
                # Create model instance
                records_to_create.append(self.model_class(**validated_record))
                processed_ids.append(validated_record['id'])
                
            except Exception as e:
                logger.error(f"Error processing job record {raw_record}: {e}")
                continue
        
        if not records_to_create:
            return {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': len(batch_data)}
        
        try:
            # Use bulk_create with update_conflicts for efficient upsert
            created_records = self.model_class.objects.bulk_create(
                records_to_create,
                update_conflicts=True,
                unique_fields=['id'],
                update_fields=[
                    'prospect_id', 'division_id', 'status', 'contract_amount',
                    'start_date', 'end_date', 'add_user_id', 'add_date', 
                    'updated_at', 'service_id'
                ]
            )
            
            stats = {
                'total_processed': len(batch_data),
                'created': len(created_records),
                'updated': 0,  # bulk_create doesn't distinguish between created and updated
                'errors': len(batch_data) - len(records_to_create)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in bulk_create for jobs: {e}")
            return {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': len(batch_data)}
