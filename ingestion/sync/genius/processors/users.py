"""
Genius Users Data Processor
"""
import logging
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async
from django.utils import timezone

from ingestion.models import Genius_UserData, Genius_Division
from .base import GeniusBaseProcessor

logger = logging.getLogger(__name__)


class GeniusUsersProcessor(GeniusBaseProcessor):
    """Processor for Genius user data"""
    
    def __init__(self):
        super().__init__(Genius_UserData)
        self.divisions_cache: Optional[Dict[int, Genius_Division]] = None
        self.field_mapping = {
            0: 'id',  # user_id
            1: 'division_id',  # division_id  
            2: 'title_id',  # title_id
            3: 'manager_user_id',  # manager_user_id
            4: 'first_name',  # first_name
            5: 'first_name_alt',  # first_name_alt
            6: 'last_name',  # last_name
            7: 'email',  # email
            8: 'personal_email',  # personal_email
            9: 'birth_date',  # birth_date
            10: 'gender_id',  # gender_id
            11: 'marital_status_id',  # marital_status_id
            12: 'time_zone_name',  # time_zone_name
            13: 'hired_on',  # hired_on
            14: 'start_date',  # start_date
            15: 'add_user_id',  # add_user_id
            16: 'add_datetime',  # add_datetime
            17: 'is_inactive',  # is_inactive
            18: 'inactive_on',  # inactive_on
            19: 'inactive_reason_id',  # inactive_reason_id
            20: 'inactive_reason_other',  # inactive_reason_other
            21: 'inactive_transfer_division_id',  # inactive_transfer_division_id
        }
    
    async def _preload_divisions(self) -> Dict[int, Genius_Division]:
        """Preload all divisions for foreign key lookups"""
        @sync_to_async
        def get_divisions():
            return {div.id: div for div in Genius_Division.objects.all()}
        
        divisions = await get_divisions()
        logger.info(f"Preloaded {len(divisions)} divisions for user processing")
        return divisions
    
    async def ensure_divisions_loaded(self):
        """Ensure divisions are loaded for processing"""
        if self.divisions_cache is None:
            self.divisions_cache = await self._preload_divisions()
    
    async def transform_record(self, raw_data: tuple) -> Dict[str, Any]:
        """Transform raw database tuple to model data"""
        await self.ensure_divisions_loaded()
        
        # Convert field mapping dict to list for base class
        field_names = [self.field_mapping[i] for i in range(len(raw_data))]
        record = super().transform_record(raw_data, field_names)
        
        # Convert timezone-naive datetimes to timezone-aware
        if record.get('hired_on'):
            record['hired_on'] = self.convert_timezone_aware(record['hired_on'])
        
        if record.get('start_date'):
            record['start_date'] = self.convert_timezone_aware(record['start_date'])
            
        if record.get('add_datetime'):
            record['add_datetime'] = self.convert_timezone_aware(record['add_datetime'])
            
        if record.get('inactive_on'):
            record['inactive_on'] = self.convert_timezone_aware(record['inactive_on'])
            
        # Set updated_at to current time for sync tracking
        record['updated_at'] = timezone.now()
        
        # Get division object for foreign key
        division_id = record.get('division_id')
        if division_id and division_id in self.divisions_cache:
            record['division'] = self.divisions_cache[division_id]
        else:
            logger.warning(f"Division ID {division_id} not found in cache for user {record.get('id')}")
            record['division'] = None
        
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
    
    def create_model_instance(self, record_data: Dict[str, Any]) -> Genius_UserData:
        """Create new Genius_UserData model instance"""
        return Genius_UserData(
            id=record_data['id'],
            division=record_data.get('division'),
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
    
    def update_model_instance(self, instance: Genius_UserData, record_data: Dict[str, Any]) -> Genius_UserData:
        """Update existing Genius_UserData model instance"""
        instance.division = record_data.get('division')
        instance.title_id = record_data.get('title_id')
        instance.manager_user_id = record_data.get('manager_user_id')
        instance.first_name = record_data.get('first_name')
        instance.first_name_alt = record_data.get('first_name_alt')
        instance.last_name = record_data.get('last_name')
        instance.email = record_data.get('email')
        instance.personal_email = record_data.get('personal_email')
        instance.birth_date = record_data.get('birth_date')
        instance.gender_id = record_data.get('gender_id')
        instance.marital_status_id = record_data.get('marital_status_id')
        instance.time_zone_name = record_data.get('time_zone_name', '')
        instance.hired_on = record_data.get('hired_on')
        instance.start_date = record_data.get('start_date')
        instance.add_user_id = record_data.get('add_user_id')
        instance.add_datetime = record_data.get('add_datetime')
        instance.is_inactive = record_data.get('is_inactive', False)
        instance.inactive_on = record_data.get('inactive_on')
        instance.inactive_reason_id = record_data.get('inactive_reason_id')
        instance.inactive_reason_other = record_data.get('inactive_reason_other')
        instance.inactive_transfer_division_id = record_data.get('inactive_transfer_division_id')
        instance.updated_at = record_data.get('updated_at')
        return instance
    
    async def process_batch(self, batch_data: List[tuple], dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of user records"""
        stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        to_create = []
        to_update = []
        
        # Get IDs for existence check
        record_ids = [row[0] for row in batch_data]
        
        @sync_to_async
        def get_existing_records():
            return {obj.id: obj for obj in Genius_UserData.objects.filter(id__in=record_ids)}
        
        existing_records = await get_existing_records()
        
        for raw_row in batch_data:
            try:
                # Transform raw data to record dict
                record_data = await self.transform_record(raw_row)
                record_id = record_data['id']
                
                # Validate record
                record_data = self.validate_record(record_data)
                
                # Create or update
                if record_id in existing_records:
                    # Update existing record
                    existing_instance = existing_records[record_id]
                    updated_instance = self.update_model_instance(existing_instance, record_data)
                    to_update.append(updated_instance)
                    stats['updated'] += 1
                else:
                    # Create new record
                    new_instance = self.create_model_instance(record_data)
                    to_create.append(new_instance)
                    stats['created'] += 1
                
                stats['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing user record {raw_row[0] if raw_row else 'unknown'}: {e}")
                stats['errors'] += 1
        
        # Save to database (unless dry run)
        if not dry_run:
            try:
                @sync_to_async
                def bulk_save():
                    if to_create:
                        Genius_UserData.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
                    
                    if to_update:
                        Genius_UserData.objects.bulk_update(
                            to_update,
                            [
                                'division', 'title_id', 'manager_user_id', 'first_name', 'first_name_alt', 'last_name',
                                'email', 'personal_email', 'birth_date', 'gender_id', 'marital_status_id', 'time_zone_name',
                                'hired_on', 'start_date', 'add_user_id', 'add_datetime', 'is_inactive', 'inactive_on',
                                'inactive_reason_id', 'inactive_reason_other', 'inactive_transfer_division_id', 'updated_at'
                            ],
                            batch_size=500
                        )
                
                await bulk_save()
            except Exception as e:
                logger.error(f"Bulk save operation failed: {e}")
                # Fallback to individual saves
                await self._individual_save(to_create, to_update, stats)
        else:
            logger.info(f"DRY RUN: Would create {len(to_create)} and update {len(to_update)} user records")
        
        return stats
    
    async def _individual_save(self, to_create: List[Genius_UserData], to_update: List[Genius_UserData], 
                              stats: Dict[str, int]):
        """Fallback individual save when bulk operations fail"""
        @sync_to_async
        def save_record(record):
            record.save()
        
        for record in to_create:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to save new user {record.id}: {e}")
                stats['errors'] += 1
                stats['created'] -= 1
        
        for record in to_update:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to update user {record.id}: {e}")
                stats['errors'] += 1
                stats['updated'] -= 1
