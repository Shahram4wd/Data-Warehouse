"""
Genius User Titles Data Processor
"""
import logging
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async
from django.utils import timezone

from ingestion.models import Genius_UserTitle
from .base import GeniusBaseProcessor

logger = logging.getLogger(__name__)


class GeniusUserTitlesProcessor(GeniusBaseProcessor):
    """Processor for Genius user title data"""
    
    def __init__(self):
        super().__init__(Genius_UserTitle)
        self.field_mapping = {
            0: 'id',  # id
            1: 'title',  # title
            2: 'abbreviation',  # abbreviation
            3: 'roles',  # roles
            4: 'type_id',  # type_id
            5: 'section_id',  # section_id
            6: 'sort',  # sort
            7: 'pay_component_group_id',  # pay_component_group_id
            8: 'is_active',  # is_active
            9: 'is_unique_per_division',  # is_unique_per_division
            10: 'created_at',  # created_at
            11: 'updated_at',  # updated_at
        }
    
    async def transform_record(self, raw_data: tuple) -> Dict[str, Any]:
        """Transform raw database tuple to model data"""
        # Convert field mapping dict to list for base class
        field_names = [self.field_mapping[i] for i in range(len(raw_data))]
        record = super().transform_record(raw_data, field_names)
        
        # Convert timezone-naive datetimes to timezone-aware
        if record.get('created_at'):
            record['created_at'] = self.convert_timezone_aware(record['created_at'])
        
        if record.get('updated_at'):
            record['updated_at'] = self.convert_timezone_aware(record['updated_at'])
        
        # Ensure boolean fields are properly converted
        record['is_active'] = bool(record.get('is_active', True))
        record['is_unique_per_division'] = bool(record.get('is_unique_per_division', False))
        
        # Ensure integer fields have defaults
        record['type_id'] = record.get('type_id') or 0
        record['sort'] = record.get('sort') or 0
        
        return record
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean user title record data"""
        # Required fields validation
        if not record_data.get('id'):
            raise ValueError("User Title ID is required")
            
        # Clean string fields with length limits
        if record_data.get('title'):
            record_data['title'] = str(record_data['title']).strip()[:100]
        if record_data.get('abbreviation'):
            record_data['abbreviation'] = str(record_data['abbreviation']).strip()[:10]
        if record_data.get('roles'):
            record_data['roles'] = str(record_data['roles']).strip()[:256]
        
        # Ensure required datetime fields exist
        if not record_data.get('created_at'):
            record_data['created_at'] = timezone.now()
        if not record_data.get('updated_at'):
            record_data['updated_at'] = timezone.now()
        
        return record_data
    
    def create_model_instance(self, record_data: Dict[str, Any]) -> Genius_UserTitle:
        """Create new Genius_UserTitle model instance"""
        return Genius_UserTitle(
            id=record_data['id'],
            title=record_data.get('title'),
            abbreviation=record_data.get('abbreviation'),
            roles=record_data.get('roles'),
            type_id=record_data.get('type_id', 0),
            section_id=record_data.get('section_id'),
            sort=record_data.get('sort', 0),
            pay_component_group_id=record_data.get('pay_component_group_id'),
            is_active=record_data.get('is_active', True),
            is_unique_per_division=record_data.get('is_unique_per_division', False),
            created_at=record_data.get('created_at'),
            updated_at=record_data.get('updated_at')
        )
    
    def update_model_instance(self, instance: Genius_UserTitle, record_data: Dict[str, Any]) -> Genius_UserTitle:
        """Update existing Genius_UserTitle model instance"""
        instance.title = record_data.get('title')
        instance.abbreviation = record_data.get('abbreviation')
        instance.roles = record_data.get('roles')
        instance.type_id = record_data.get('type_id', 0)
        instance.section_id = record_data.get('section_id')
        instance.sort = record_data.get('sort', 0)
        instance.pay_component_group_id = record_data.get('pay_component_group_id')
        instance.is_active = record_data.get('is_active', True)
        instance.is_unique_per_division = record_data.get('is_unique_per_division', False)
        instance.created_at = record_data.get('created_at')
        instance.updated_at = record_data.get('updated_at')
        return instance
    
    async def process_batch(self, batch_data: List[tuple], dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of user title records"""
        stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        to_create = []
        to_update = []
        
        # Get IDs for existence check
        record_ids = [row[0] for row in batch_data]
        
        @sync_to_async
        def get_existing_records():
            return {obj.id: obj for obj in Genius_UserTitle.objects.filter(id__in=record_ids)}
        
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
                logger.error(f"Error processing user title record {raw_row[0] if raw_row else 'unknown'}: {e}")
                stats['errors'] += 1
        
        # Save to database (unless dry run)
        if not dry_run:
            try:
                @sync_to_async
                def bulk_save():
                    if to_create:
                        Genius_UserTitle.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
                    
                    if to_update:
                        Genius_UserTitle.objects.bulk_update(
                            to_update,
                            [
                                'title', 'abbreviation', 'roles', 'type_id', 'section_id', 'sort',
                                'pay_component_group_id', 'is_active', 'is_unique_per_division',
                                'created_at', 'updated_at'
                            ],
                            batch_size=500
                        )
                
                await bulk_save()
            except Exception as e:
                logger.error(f"Bulk save operation failed: {e}")
                # Fallback to individual saves
                await self._individual_save(to_create, to_update, stats)
        else:
            logger.info(f"DRY RUN: Would create {len(to_create)} and update {len(to_update)} user title records")
        
        return stats
    
    async def _individual_save(self, to_create: List[Genius_UserTitle], to_update: List[Genius_UserTitle], 
                              stats: Dict[str, int]):
        """Fallback individual save when bulk operations fail"""
        @sync_to_async
        def save_record(record):
            record.save()
        
        for record in to_create:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to save new user title {record.id}: {e}")
                stats['errors'] += 1
                stats['created'] -= 1
        
        for record in to_update:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to update user title {record.id}: {e}")
                stats['errors'] += 1
                stats['updated'] -= 1
