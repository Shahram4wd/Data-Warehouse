"""
Genius Services Data Processor
"""
import logging
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async
from django.utils import timezone

from ingestion.models import Genius_Service
from .base import GeniusBaseProcessor

logger = logging.getLogger(__name__)


class GeniusServicesProcessor(GeniusBaseProcessor):
    """Processor for Genius service data"""
    
    def __init__(self):
        super().__init__(Genius_Service)
        self.field_mapping = {
            0: 'id',  # id
            1: 'label',  # label
            2: 'is_active',  # is_active
            3: 'is_lead_required',  # is_lead_required
            4: 'order_number',  # order_number
            5: 'created_at',  # created_at
            6: 'updated_at',  # updated_at
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
        record['is_lead_required'] = bool(record.get('is_lead_required', False))
        
        # Ensure integer fields have defaults
        record['order_number'] = record.get('order_number') or 0
        
        return record
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean service record data"""
        # Required fields validation
        if not record_data.get('id'):
            raise ValueError("Service ID is required")
            
        # Clean string fields with length limits
        if record_data.get('label'):
            record_data['label'] = str(record_data['label']).strip()[:100]
        
        # Ensure required datetime fields exist
        if not record_data.get('created_at'):
            record_data['created_at'] = timezone.now()
        if not record_data.get('updated_at'):
            record_data['updated_at'] = timezone.now()
        
        return record_data
    
    def create_model_instance(self, record_data: Dict[str, Any]) -> Genius_Service:
        """Create new Genius_Service model instance"""
        return Genius_Service(
            id=record_data['id'],
            label=record_data.get('label'),
            is_active=record_data.get('is_active', True),
            is_lead_required=record_data.get('is_lead_required', False),
            order_number=record_data.get('order_number', 0),
            created_at=record_data.get('created_at'),
            updated_at=record_data.get('updated_at')
        )
    
    def update_model_instance(self, instance: Genius_Service, record_data: Dict[str, Any]) -> Genius_Service:
        """Update existing Genius_Service model instance"""
        instance.label = record_data.get('label')
        instance.is_active = record_data.get('is_active', True)
        instance.is_lead_required = record_data.get('is_lead_required', False)
        instance.order_number = record_data.get('order_number', 0)
        instance.created_at = record_data.get('created_at')
        instance.updated_at = record_data.get('updated_at')
        return instance
    
    async def process_batch(self, batch_data: List[tuple], dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of service records"""
        stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        to_create = []
        to_update = []
        
        # Get IDs for existence check
        record_ids = [row[0] for row in batch_data]
        
        @sync_to_async
        def get_existing_records():
            return {obj.id: obj for obj in Genius_Service.objects.filter(id__in=record_ids)}
        
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
                logger.error(f"Error processing service record {raw_row[0] if raw_row else 'unknown'}: {e}")
                stats['errors'] += 1
        
        # Save to database (unless dry run)
        if not dry_run:
            try:
                @sync_to_async
                def bulk_save():
                    if to_create:
                        Genius_Service.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
                    
                    if to_update:
                        Genius_Service.objects.bulk_update(
                            to_update,
                            ['label', 'is_active', 'is_lead_required', 'order_number', 'created_at', 'updated_at'],
                            batch_size=500
                        )
                
                await bulk_save()
            except Exception as e:
                logger.error(f"Bulk save operation failed: {e}")
                # Fallback to individual saves
                await self._individual_save(to_create, to_update, stats)
        else:
            logger.info(f"DRY RUN: Would create {len(to_create)} and update {len(to_update)} service records")
        
        return stats
    
    async def _individual_save(self, to_create: List[Genius_Service], to_update: List[Genius_Service], 
                              stats: Dict[str, int]):
        """Fallback individual save when bulk operations fail"""
        @sync_to_async
        def save_record(record):
            record.save()
        
        for record in to_create:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to save new service {record.id}: {e}")
                stats['errors'] += 1
                stats['created'] -= 1
        
        for record in to_update:
            try:
                await save_record(record)
            except Exception as e:
                logger.error(f"Failed to update service {record.id}: {e}")
                stats['errors'] += 1
                stats['updated'] -= 1
