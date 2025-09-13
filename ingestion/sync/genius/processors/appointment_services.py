"""
Genius Appointment Services Data Processor
Handles transformation and validation of appointment services data
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

from ingestion.models import Genius_AppointmentService

logger = logging.getLogger(__name__)

class GeniusAppointmentServicesProcessor:
    """Processor for transforming and loading appointment services data"""
    
    def __init__(self, model_class=None):
        self.model_class = model_class or Genius_AppointmentService
        
    def process_batch(self, batch_data: List[tuple], field_mapping: List[str], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """
        Process a batch of appointment services data with bulk operations
        
        Args:
            batch_data: List of tuples containing appointment services data
            field_mapping: List of field names matching data order
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            
        Returns:
            Dictionary containing batch processing statistics
        """
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not batch_data:
            return stats
        
        logger.info(f"Processing batch of {len(batch_data)} appointment services records")
        
        # Transform data to model instances
        transformed_records = []
        
        for raw_data in batch_data:
            try:
                # Convert tuple to dictionary using field mapping
                data_dict = dict(zip(field_mapping, raw_data))
                
                # Transform the record
                transformed = self._transform_record(data_dict)
                if transformed:
                    transformed_records.append(transformed)
                    stats['total_processed'] += 1
                    
            except Exception as e:
                logger.error(f"Error transforming appointment services record {raw_data}: {e}")
                stats['errors'] += 1
        
        if not transformed_records or dry_run:
            if dry_run:
                logger.info(f"DRY RUN: Would process {len(transformed_records)} appointment services records")
                stats['created'] = len(transformed_records)  # Simulate creation for dry run
            return stats
        
        # Bulk create/update operations
        try:
            if force_overwrite:
                stats.update(self._bulk_force_update(transformed_records))
            else:
                stats.update(self._bulk_upsert(transformed_records))
                
        except Exception as e:
            logger.error(f"Error during bulk operation: {e}")
            stats['errors'] += len(transformed_records)
            
        return stats
    
    def _transform_record(self, data_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a single appointment services record
        
        Args:
            data_dict: Dictionary containing appointment services data
            
        Returns:
            Transformed data dictionary or None if invalid
        """
        try:
            # Basic field extraction and validation
            appointment_id = data_dict.get('appointment_id')
            service_id = data_dict.get('service_id')
            
            if not appointment_id or not service_id:
                logger.warning(f"Missing required fields in appointment services record: {data_dict}")
                return None
            
            # Parse datetime fields
            created_at = self._parse_datetime(data_dict.get('created_at'))
            updated_at = self._parse_datetime(data_dict.get('updated_at'))
            
            # Build transformed record
            transformed = {
                'appointment_id': int(appointment_id),
                'service_id': int(service_id),
                'created_at': created_at,
                'updated_at': updated_at,
                'sync_updated_at': timezone.now()
            }
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming appointment services record {data_dict}: {e}")
            return None
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime value from various formats"""
        if not value:
            return None
            
        if isinstance(value, datetime):
            return value
            
        if isinstance(value, str):
            try:
                # Try parsing ISO format
                from django.utils.dateparse import parse_datetime
                parsed = parse_datetime(value)
                if parsed:
                    return parsed
                    
                # Try other common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                        
            except Exception:
                pass
                
        return None
    
    def _bulk_upsert(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Perform bulk upsert operation"""
        stats = {'created': 0, 'updated': 0}
        
        # Group records by unique key (appointment_id, service_id)
        records_dict = {}
        for record in records:
            key = (record['appointment_id'], record['service_id'])
            records_dict[key] = record
        
        # Check which records already exist
        existing_keys = set(
            self.model_class.objects.filter(
                appointment_id__in=[r['appointment_id'] for r in records],
                service_id__in=[r['service_id'] for r in records]
            ).values_list('appointment_id', 'service_id')
        )
        
        # Separate into creates and updates
        creates = []
        updates = []
        
        for key, record in records_dict.items():
            if key in existing_keys:
                updates.append(record)
            else:
                creates.append(record)
        
        # Bulk create new records
        if creates:
            with transaction.atomic():
                create_objects = [
                    self.model_class(**record) for record in creates
                ]
                self.model_class.objects.bulk_create(create_objects, batch_size=500)
                stats['created'] = len(creates)
                logger.info(f"Created {len(creates)} new appointment services records")
        
        # Bulk update existing records
        if updates:
            with transaction.atomic():
                for record in updates:
                    self.model_class.objects.filter(
                        appointment_id=record['appointment_id'],
                        service_id=record['service_id']
                    ).update(**record)
                stats['updated'] = len(updates)
                logger.info(f"Updated {len(updates)} appointment services records")
        
        return stats
    
    def _bulk_force_update(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Perform bulk force update - delete and recreate all records"""
        stats = {'created': 0, 'updated': 0}
        
        # Get all appointment_ids and service_ids to delete
        appointment_ids = [r['appointment_id'] for r in records]
        service_ids = [r['service_id'] for r in records]
        
        with transaction.atomic():
            # Delete existing records
            deleted_count, _ = self.model_class.objects.filter(
                appointment_id__in=appointment_ids,
                service_id__in=service_ids
            ).delete()
            
            # Bulk create all records as new
            create_objects = [
                self.model_class(**record) for record in records
            ]
            self.model_class.objects.bulk_create(create_objects, batch_size=500)
            
            stats['created'] = len(records)
            logger.info(f"Force update: deleted {deleted_count}, created {len(records)} appointment services records")
        
        return stats
