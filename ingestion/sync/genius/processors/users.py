"""
Genius Users Data Processor
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone
from django.db import IntegrityError

from ingestion.models import Genius_UserData, Genius_Division

logger = logging.getLogger(__name__)


class GeniusUsersProcessor:
    """Processor for Genius user data with bulk operations"""
    
    def __init__(self, model_class):
        self.model = model_class
        self.divisions_cache: Optional[Dict[int, Genius_Division]] = None
    
    def _preload_divisions(self) -> Dict[int, Genius_Division]:
        """Preload all divisions for foreign key lookups"""
        divisions = {div.id: div for div in Genius_Division.objects.all()}
        logger.info(f"Preloaded {len(divisions)} divisions for user processing")
        return divisions
    
    def ensure_divisions_loaded(self):
        """Ensure divisions are loaded for processing"""
        if self.divisions_cache is None:
            self.divisions_cache = self._preload_divisions()
    
    def convert_timezone_aware(self, dt):
        """Convert timezone-naive datetime to timezone-aware"""
        if dt and not timezone.is_aware(dt):
            return timezone.make_aware(dt)
        return dt
    
    def transform_record(self, raw_data: Tuple, field_mapping: Dict[str, int]) -> Dict[str, Any]:
        """Transform raw database tuple to model data"""
        record = {}
        
        # Map fields using field mapping
        for field_name, column_index in field_mapping.items():
            if column_index < len(raw_data):
                record[field_name] = raw_data[column_index]
        
        # Convert timezone-naive datetimes to timezone-aware
        for date_field in ['hired_on', 'start_date', 'add_datetime', 'inactive_on']:
            if record.get(date_field):
                record[date_field] = self.convert_timezone_aware(record[date_field])
            
        # Set updated_at to current time for sync tracking
        record['updated_at'] = timezone.now()
        
        return record
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean user record data"""
        # Required fields validation
        if not record_data.get('id'):
            raise ValueError("User ID is required")
            
        # Clean string fields
        for field in ['first_name', 'first_name_alt', 'last_name', 'email', 'personal_email', 'time_zone_name', 'inactive_reason_other']:
            if record_data.get(field):
                record_data[field] = str(record_data[field]).strip()[:255]
        
        # Boolean fields
        record_data['is_inactive'] = bool(record_data.get('is_inactive', False))
        
        # Ensure time_zone_name has a default value
        if not record_data.get('time_zone_name'):
            record_data['time_zone_name'] = ''
        
        return record_data
    
    def process_batch(self, batch_data: List[tuple], field_mapping: Dict[str, int], force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of user records using bulk upsert"""
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        instances_to_create = []
        for raw_row in batch_data:
            try:
                record_data = self.transform_record(raw_row, field_mapping)
                record_data = self.validate_record(record_data)
                instance = self.model(
                    id=record_data['id'],
                    division_id=record_data.get('division_id'),
                    title_id=record_data.get('title_id'),
                    manager_user_id=record_data.get('manager_user_id'),
                    first_name=record_data.get('first_name'),
                    first_name_alt=record_data.get('first_name_alt'),
                    last_name=record_data.get('last_name'),
                    email=record_data.get('email'),
                    personal_email=record_data.get('personal_email'),
                    birth_date=record_data.get('birth_date'),
                    gender_id=record_data.get('gender_id'),
                    marital_status_id=record_data.get('marital_status_id'),
                    time_zone_name=record_data.get('time_zone_name', ''),
                    hired_on=record_data.get('hired_on'),
                    start_date=record_data.get('start_date'),
                    add_user_id=record_data.get('add_user_id'),
                    add_datetime=record_data.get('add_datetime'),
                    is_inactive=record_data.get('is_inactive', False),
                    inactive_on=record_data.get('inactive_on'),
                    inactive_reason_id=record_data.get('inactive_reason_id'),
                    inactive_reason_other=record_data.get('inactive_reason_other'),
                    inactive_transfer_division_id=record_data.get('inactive_transfer_division_id'),
                    updated_at=record_data.get('updated_at')
                )
                instances_to_create.append(instance)
                stats['total_processed'] += 1
            except Exception as e:
                logger.error(f"Error processing user record {raw_row[0] if raw_row else 'unknown'}: {e}")
                stats['errors'] += 1
        if not dry_run and instances_to_create:
            try:
                if force_overwrite:
                    result = self.model.objects.bulk_create(
                        instances_to_create,
                        update_conflicts=True,
                        update_fields=[
                            'division_id', 'title_id', 'manager_user_id', 'first_name', 'first_name_alt', 'last_name',
                            'email', 'personal_email', 'birth_date', 'gender_id', 'marital_status_id', 'time_zone_name',
                            'hired_on', 'start_date', 'add_user_id', 'add_datetime', 'is_inactive', 'inactive_on',
                            'inactive_reason_id', 'inactive_reason_other', 'inactive_transfer_division_id', 'updated_at'
                        ],
                        unique_fields=['id']
                    )
                else:
                    result = self.model.objects.bulk_create(
                        instances_to_create,
                        ignore_conflicts=True
                    )
                stats['created'] = len(instances_to_create)
            except Exception as e:
                logger.error(f"Bulk create operation failed: {e}")
                stats['errors'] += len(instances_to_create)
        elif dry_run:
            logger.info(f"DRY RUN: Would process {len(instances_to_create)} user records")
            stats['created'] = len(instances_to_create)
        return stats
