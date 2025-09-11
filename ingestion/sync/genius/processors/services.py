"""
Services processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

class GeniusServicesProcessor:
    """Processor for Genius services data with bulk operations"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def convert_timezone_aware(self, dt):
        """Convert timezone-naive datetime to timezone-aware"""
        if dt and isinstance(dt, datetime) and dt.tzinfo is None:
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw database tuple to record dict"""
        
        if len(raw_data) != len(field_mapping):
            logger.error(f"Field mapping length ({len(field_mapping)}) doesn't match data length ({len(raw_data)})")
            raise ValueError("Field mapping mismatch")
        
        # Create record dict from tuple and field mapping
        record = dict(zip(field_mapping, raw_data))
        
        # Convert timezone-naive datetimes to timezone-aware
        if record.get('created_at'):
            record['created_at'] = self.convert_timezone_aware(record['created_at'])
        
        if record.get('updated_at'):
            record['updated_at'] = self.convert_timezone_aware(record['updated_at'])
        
        # Ensure boolean fields are properly converted
        record['is_active'] = bool(record.get('is_active', True))
        record['is_lead_required'] = bool(record.get('is_lead_required', False))
        
        # Ensure integer fields have defaults
        record['order_number'] = record.get('order_number') or 0
        
        return record
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate service record data"""
        
        # Check for required ID field (allow ID = 0, but not None or empty)
        if record_data.get('id') is None or record_data.get('id') == '':
            logger.error(f"Service record missing required ID field")
            raise ValueError("Missing required ID field")
        
        # Clean string fields with length limits  
        if record_data.get('label'):
            record_data['label'] = str(record_data['label']).strip()[:100]
        
        # Validate datetime fields
        if not record_data.get('created_at'):
            logger.warning(f"Service {record_data.get('id')} missing created_at timestamp")
        
        if not record_data.get('updated_at'):
            logger.warning(f"Service {record_data.get('id')} missing updated_at timestamp")
        
        return record_data
    
    def bulk_upsert_services(self, batch_data: List[tuple], field_mapping: List[str], 
                            force_overwrite: bool = False) -> Dict[str, int]:
        """Bulk upsert services using Django bulk_create with update_conflicts"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not batch_data:
            return stats
        
        model_instances = []
        
        for i, raw_row in enumerate(batch_data):
            try:
                # Transform and validate record
                record_data = self.transform_record(raw_row, field_mapping)
                record_data = self.validate_record(record_data)
                
                # Create model instance
                instance = self.model_class(
                    id=record_data['id'],
                    label=record_data.get('label'),
                    is_active=record_data.get('is_active', True),
                    is_lead_required=record_data.get('is_lead_required', False),
                    order_number=record_data.get('order_number', 0),
                    created_at=record_data.get('created_at'),
                    updated_at=record_data.get('updated_at')
                )
                
                model_instances.append(instance)
                stats['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error transforming service record {i}: {e}")
                stats['errors'] += 1
        
        if not model_instances:
            logger.warning("No valid model instances to process")
            return stats
        
        try:
            # Use bulk_create with update_conflicts for efficient upsert
            results = self.model_class.objects.bulk_create(
                model_instances,
                update_conflicts=True,
                update_fields=[
                    'label', 'is_active', 'is_lead_required', 'order_number', 
                    'created_at', 'updated_at'
                ],
                unique_fields=['id'],
                batch_size=500
            )
            
            # Count created vs updated (bulk_create returns created objects)
            created_count = len([obj for obj in results if obj.pk])
            updated_count = len(model_instances) - created_count
            
            stats['created'] = created_count
            stats['updated'] = updated_count
            
            logger.info(f"Bulk upsert completed - Created: {created_count}, Updated: {updated_count}")
            
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            # For error counting, assume all failed
            stats['errors'] = len(model_instances)
            stats['total_processed'] = 0
            stats['created'] = 0
            stats['updated'] = 0
            raise
        
        return stats
    
    def process_batch(self, batch_data: List[tuple], field_mapping: List[str], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of services data"""
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(batch_data)} service records")
            return {
                'total_processed': len(batch_data), 
                'created': len(batch_data), 
                'updated': 0, 
                'errors': 0
            }
        
        return self.bulk_upsert_services(batch_data, field_mapping, force_overwrite)
