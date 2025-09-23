"""
Lead processor for Genius CRM data transformation
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusLeadProcessor(GeniusBaseProcessor):
    """Processor for Genius lead data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
        
        # Track validation issues for summary logging
        self.validation_stats = {
            'missing_names': 0,
            'missing_contact_info': 0,
            'processed_count': 0
        }
    
    def validate_record(self, record_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Validate and clean lead record data"""
        
        # Convert tuple to dict using field mapping
        if isinstance(record_data, tuple) and len(record_data) == len(field_mapping):
            record_dict = dict(zip(field_mapping, record_data))
        else:
            logger.error(f"Record length {len(record_data)} does not match mapping length {len(field_mapping)}")
            return None
        
        try:
            # Map fields according to the proper field names
            processed = {
                'lead_id': self._convert_to_integer(record_dict.get('lead_id')),
                'first_name': self._convert_to_string(record_dict.get('first_name')),
                'last_name': self._convert_to_string(record_dict.get('last_name')),
                'email': self._convert_to_string(record_dict.get('email')),
                'phone1': self._convert_to_string(record_dict.get('phone')),  # Maps to phone1
                'address1': self._convert_to_string(record_dict.get('address')),  # Maps to address1
                'city': self._convert_to_string(record_dict.get('city')),
                'state': self._convert_to_string(record_dict.get('state')),
                'zip': self._convert_to_string(record_dict.get('zip_code')),  # Maps to zip
                'source': self._convert_to_integer(record_dict.get('prospect_source_id')),  # Maps to source
                'added_by': self._convert_to_integer(record_dict.get('user_id')),  # Maps to added_by
                'division_id': self._convert_to_integer(record_dict.get('division_id')),
                'notes': self._convert_to_string(record_dict.get('notes')),
                'status': self._convert_to_string(record_dict.get('status')),
                'copied_to_id': self._convert_to_integer(record_dict.get('converted_to_prospect_id')),  # Maps to copied_to_id
                'added_on': self._convert_to_datetime(record_dict.get('created_at')),  # Maps to added_on
                'updated_at': self._convert_to_datetime(record_dict.get('updated_at')),
                'sync_updated_at': self.convert_timezone_aware(datetime.now()),
            }
            
            # Ensure required datetime fields are not None - fallback to timezone.now()
            from django.utils import timezone
            if processed['updated_at'] is None:
                processed['updated_at'] = timezone.now()
            if processed['added_on'] is None:
                processed['added_on'] = timezone.now()
            
            # Validate required fields
            if not processed.get('lead_id'):
                logger.warning("Skipping record with missing lead_id")
                return None
            
            # Track validation issues for batch summary (don't log individual warnings)
            self.validation_stats['processed_count'] += 1
            
            if not processed.get('first_name') and not processed.get('last_name'):
                self.validation_stats['missing_names'] += 1
                # Only log a debug message for the first few occurrences
                if self.validation_stats['missing_names'] <= 5:
                    logger.debug(f"Lead {processed['lead_id']} has no first or last name")
            
            if not processed.get('email') and not processed.get('phone1'):
                self.validation_stats['missing_contact_info'] += 1
                if self.validation_stats['missing_contact_info'] <= 5:
                    logger.debug(f"Lead {processed['lead_id']} has no email or phone")
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing lead record: {e}")
            return None
    
    def process_batch(self, batch_data: List[tuple], field_mapping: List[str], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of leads data using bulk operations"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # Transform batch data to model instances  
            model_instances = []
            for raw_row in batch_data:
                try:
                    # Validate and transform record
                    record_data = self.validate_record(raw_row, field_mapping)
                    
                    if record_data is None:
                        stats['errors'] += 1
                        continue
                    
                    # Create model instance
                    instance = self.model_class(
                        lead_id=record_data['lead_id'],
                        first_name=record_data.get('first_name'),
                        last_name=record_data.get('last_name'),
                        email=record_data.get('email'),
                        phone1=record_data.get('phone1'),
                        address1=record_data.get('address1'),
                        city=record_data.get('city'),
                        state=record_data.get('state'),
                        zip=record_data.get('zip'),
                        source=record_data.get('source'),
                        added_by=record_data.get('added_by'),
                        division_id=record_data.get('division_id'),
                        notes=record_data.get('notes'),
                        status=record_data.get('status'),
                        copied_to_id=record_data.get('copied_to_id'),
                        added_on=record_data.get('added_on'),
                        updated_at=record_data.get('updated_at'),
                        sync_updated_at=record_data.get('sync_updated_at')
                    )
                    
                    model_instances.append(instance)
                    stats['total_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error transforming lead record {raw_row[0] if raw_row else 'unknown'}: {e}")
                    stats['errors'] += 1
            
            if not model_instances:
                logger.warning("No valid model instances to process")
                return stats

            # Handle dry-run mode
            if dry_run:
                logger.info(f"DRY-RUN: Would process {len(model_instances)} lead records")
                stats['created'] = len(model_instances)  # In dry-run, assume all would be created
                return stats

            # Perform bulk upsert using bulk_create with update_conflicts
            def bulk_upsert():
                created_count = 0
                updated_count = 0
                
                try:
                    # Use bulk_create with update_conflicts for efficient upsert
                    results = self.model_class.objects.bulk_create(
                        model_instances,
                        update_conflicts=True,
                        update_fields=[
                            'first_name', 'last_name', 'email', 'phone1', 'address1',
                            'city', 'state', 'zip', 'source', 'added_by', 'division_id',
                            'notes', 'status', 'copied_to_id', 'added_on', 'updated_at',
                            'sync_updated_at'
                        ],
                        unique_fields=['lead_id'],
                        batch_size=500
                    )
                    
                    # Count created vs updated (bulk_create returns created objects)
                    created_count = len([obj for obj in results if obj.pk])
                    updated_count = len(model_instances) - created_count
                    
                except Exception as e:
                    logger.error(f"Bulk upsert failed: {e}")
                    # Fallback: assume all were updates for counting purposes
                    created_count = 0
                    updated_count = len(model_instances)
                    raise
                
                return created_count, updated_count
            
            # Execute bulk operation
            try:
                created_count, updated_count = bulk_upsert()
                stats['created'] = created_count
                stats['updated'] = updated_count
                logger.info(f"Bulk upsert completed - Created: {created_count}, Updated: {updated_count}")
            
            except Exception as e:
                logger.error(f"Bulk operation failed: {e}")
                # For error counting, assume processing failed
                stats['errors'] = len(model_instances)
                stats['total_processed'] = 0
                stats['created'] = 0
                stats['updated'] = 0
        
        except Exception as e:
            logger.error(f"Batch processing failed: {e}", exc_info=True)
            stats['errors'] = len(batch_data)
        
        # Log validation summary at the end
        self.log_validation_summary()
        
        return stats

    def log_validation_summary(self):
        """Log a summary of validation issues instead of individual warnings"""
        if self.validation_stats['processed_count'] > 0:
            logger.info(f"Lead validation summary:")
            logger.info(f"  • Processed: {self.validation_stats['processed_count']} records")
            
            if self.validation_stats['missing_names'] > 0:
                logger.info(f"  • Missing names: {self.validation_stats['missing_names']} records ({self.validation_stats['missing_names']/self.validation_stats['processed_count']*100:.1f}%)")
            
            if self.validation_stats['missing_contact_info'] > 0:
                logger.info(f"  • Missing contact info: {self.validation_stats['missing_contact_info']} records ({self.validation_stats['missing_contact_info']/self.validation_stats['processed_count']*100:.1f}%)")
        
        # Reset stats for next batch
        self.validation_stats = {
            'missing_names': 0,
            'missing_contact_info': 0,
            'processed_count': 0
        }
    
    def _convert_to_string(self, value: Any) -> str:
        """Convert value to string or None"""
        if value is None or value == '':
            return None
            
        return str(value).strip() if str(value).strip() else None
    
    def _convert_to_integer(self, value: Any) -> int:
        """Convert value to integer or None"""
        if value is None or value == '':
            return None
        
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.debug(f"Could not convert '{value}' to integer")
            return None
    
    def _convert_to_datetime(self, value: Any):
        """Convert value to datetime"""
        if value is None:
            return None
        
        # If it's already a datetime, make it timezone-aware
        if isinstance(value, datetime):
            return self.convert_timezone_aware(value)
        
        # Try to parse string datetime
        try:
            from dateutil.parser import parse
            dt = parse(str(value))
            return self.convert_timezone_aware(dt)
        except (ValueError, TypeError):
            logger.debug(f"Could not convert '{value}' to datetime")
            return None
