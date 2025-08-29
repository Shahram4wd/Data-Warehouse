"""
Prospects processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async

from ingestion.models import Genius_Prospect, Genius_Division
from ingestion.sync.genius.processors.base import GeniusBaseProcessor

logger = logging.getLogger(__name__)

class GeniusProspectsProcessor(GeniusBaseProcessor):
    """Processor for Genius prospects data"""
    
    def __init__(self):
        super().__init__(Genius_Prospect)
        self.field_mapping = [
            'id', 'division_id', 'user_id', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
            'address1', 'address2', 'city', 'county', 'state', 'zip', 'year_built', 'phone1', 'phone2', 
            'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id', 
            'third_party_source_id', 'updated_at', 'hubspot_contact_id'
        ]
        self.divisions_cache = None
    
    @sync_to_async
    def _preload_divisions(self) -> Dict[int, Genius_Division]:
        """Preload divisions for foreign key lookups"""
        return {division.id: division for division in Genius_Division.objects.all()}
    
    async def ensure_divisions_loaded(self):
        """Ensure divisions cache is loaded"""
        if self.divisions_cache is None:
            self.divisions_cache = await self._preload_divisions()
    
    async def transform_record(self, raw_data: tuple) -> Dict[str, Any]:
        """Transform raw database tuple to model data"""
        await self.ensure_divisions_loaded()
        
        record = super().transform_record(raw_data, self.field_mapping)
        
        # Convert timezone-naive datetimes to timezone-aware
        if record.get('add_date'):
            record['add_date'] = self.convert_timezone_aware(record['add_date'])
        
        if record.get('updated_at'):
            record['updated_at'] = self.convert_timezone_aware(record['updated_at'])
        
        # Get division object for foreign key
        division_id = record.get('division_id')
        if division_id and division_id in self.divisions_cache:
            # Store division object for logging/validation but don't pass to model
            record['_division_obj'] = self.divisions_cache[division_id]
        else:
            logger.warning(f"Division ID {division_id} not found in cache for prospect {record.get('id')}")
            record['_division_obj'] = None
        
        return record
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prospect record data"""
        # Ensure required fields
        if not record_data.get('_division_obj'):
            logger.warning(f"Prospect {record_data.get('id')} missing division")
        
        if not record_data.get('updated_at'):
            logger.warning(f"Prospect {record_data.get('id')} missing updated_at timestamp")
        
        return record_data
    
    def create_model_instance(self, record_data: Dict[str, Any]) -> Genius_Prospect:
        """Create Genius_Prospect model instance"""
        return Genius_Prospect(
            id=record_data['id'],
            division_id=record_data['division_id'],
            user_id=record_data.get('user_id'),
            first_name=record_data.get('first_name'),
            last_name=record_data.get('last_name'),
            alt_first_name=record_data.get('alt_first_name'),
            alt_last_name=record_data.get('alt_last_name'),
            address1=record_data.get('address1'),
            address2=record_data.get('address2'),
            city=record_data.get('city'),
            county=record_data.get('county'),
            state=record_data.get('state'),
            zip=record_data.get('zip'),
            year_built=record_data.get('year_built'),
            phone1=record_data.get('phone1'),
            phone2=record_data.get('phone2'),
            email=record_data.get('email'),
            notes=record_data.get('notes'),
            add_user_id=record_data.get('add_user_id'),
            add_date=record_data.get('add_date'),
            marketsharp_id=record_data.get('marketsharp_id'),
            leap_customer_id=record_data.get('leap_customer_id'),
            updated_at=record_data.get('updated_at'),
            hubspot_contact_id=record_data.get('hubspot_contact_id')
        )
    
    def update_model_instance(self, instance: Genius_Prospect, record_data: Dict[str, Any]) -> Genius_Prospect:
        """Update existing Genius_Prospect model instance"""
        instance.division = record_data['division']
        instance.user_id = record_data.get('user_id')
        instance.first_name = record_data.get('first_name')
        instance.last_name = record_data.get('last_name')
        instance.alt_first_name = record_data.get('alt_first_name')
        instance.alt_last_name = record_data.get('alt_last_name')
        instance.address1 = record_data.get('address1')
        instance.address2 = record_data.get('address2')
        instance.city = record_data.get('city')
        instance.county = record_data.get('county')
        instance.state = record_data.get('state')
        instance.zip = record_data.get('zip')
        instance.year_built = record_data.get('year_built')
        instance.phone1 = record_data.get('phone1')
        instance.phone2 = record_data.get('phone2')
        instance.email = record_data.get('email')
        instance.notes = record_data.get('notes')
        instance.add_user_id = record_data.get('add_user_id')
        instance.add_date = record_data.get('add_date')
        instance.marketsharp_id = record_data.get('marketsharp_id')
        instance.leap_customer_id = record_data.get('leap_customer_id')
        instance.updated_at = record_data.get('updated_at')
        instance.hubspot_contact_id = record_data.get('hubspot_contact_id')
        return instance
    
    async def process_batch(self, batch_data: List[tuple], force_overwrite: bool = False, 
                           dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of prospect records"""
        
        stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        to_create = []
        to_update = []
        
        # Get existing records for this batch using sync_to_async
        record_ids = [row[0] for row in batch_data]  # First column is always ID
        
        @sync_to_async
        def get_existing_records():
            return {obj.id: obj for obj in Genius_Prospect.objects.filter(id__in=record_ids)}
        
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
                logger.error(f"Error processing prospect record {raw_row[0] if raw_row else 'unknown'}: {e}")
                stats['errors'] += 1
        
        # Save to database (unless dry run)
        if not dry_run:
            try:
                @sync_to_async
                def bulk_save():
                    if to_create:
                        Genius_Prospect.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
                    
                    if to_update:
                        Genius_Prospect.objects.bulk_update(
                            to_update,
                            [
                                'division', 'user_id', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
                                'address1', 'address2', 'city', 'county', 'state', 'zip', 'year_built', 'phone1', 'phone2',
                                'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id',
                                'updated_at', 'hubspot_contact_id'
                            ],
                            batch_size=500
                        )
                
                await bulk_save()
            except Exception as e:
                logger.error(f"Bulk save operation failed: {e}")
                # Fallback to individual saves
                await self._individual_save(to_create, to_update, stats)
        else:
            logger.info(f"DRY RUN: Would create {len(to_create)} and update {len(to_update)} prospect records")
        
        return stats
    
    async def _individual_save(self, to_create: List[Genius_Prospect], to_update: List[Genius_Prospect], 
                              stats: Dict[str, int]):
        """Fallback individual save when bulk operations fail"""
        @sync_to_async
        def save_record(record):
            record.save()
        
        for record in to_create:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to save new prospect {record.id}: {e}")
                stats['errors'] += 1
                stats['created'] -= 1
        
        for record in to_update:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to update prospect {record.id}: {e}")
                stats['errors'] += 1
                stats['updated'] -= 1
