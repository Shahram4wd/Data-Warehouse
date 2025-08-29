"""
Genius User Associations Data Processor
"""
import logging
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async
from django.utils import timezone

from ingestion.models import Genius_UserAssociation
from .base import GeniusBaseProcessor

logger = logging.getLogger(__name__)


class GeniusUserAssociationsProcessor(GeniusBaseProcessor):
    """Processor for Genius user associations data"""
    
    def __init__(self):
        super().__init__(Genius_UserAssociation)
        self.field_mapping = {
            0: 'id',  # id
            1: 'user_id',  # primary_user_id -> maps to user_id in our model
            2: 'created_at',  # created_at
            3: 'updated_at',  # updated_at
        }
    
    def transform_record(self, raw_data: tuple) -> Dict[str, Any]:
        """Transform raw database tuple to model data"""
        
        # Convert field mapping dict to list for base class
        field_names = [self.field_mapping[i] for i in range(len(raw_data))]
        record = super().transform_record(raw_data, field_names)
        
        # Convert timezone-naive datetimes to timezone-aware
        if record.get('created_at'):
            record['created_at'] = self.convert_timezone_aware(record['created_at'])
            
        if record.get('updated_at'):
            record['updated_at'] = self.convert_timezone_aware(record['updated_at'])
        
        # Set default values for fields that don't exist in source table
        record['definition_id'] = None  # Not available in source
        record['division_id'] = None    # Not available in source
        record['field_value'] = None    # Not available in source
        
        return record
    
    async def process_batch(self, batch: List[tuple], dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of user associations records"""
        stats = {'processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        for raw_record in batch:
            try:
                # Transform the raw data
                record_data = self.transform_record(raw_record)
                record_id = record_data.get('id')
                
                if dry_run:
                    logger.debug(f"DRY RUN: Would process user association {record_id}")
                    stats['processed'] += 1
                    continue
                
                # Process the record (create or update)
                result = await self.upsert_record(record_data, record_id)
                
                if result == 'created':
                    stats['created'] += 1
                    logger.debug(f"Created user association {record_id}")
                elif result == 'updated':
                    stats['updated'] += 1
                    logger.debug(f"Updated user association {record_id}")
                
                stats['processed'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                error_id = raw_record[0] if raw_record else 'unknown'
                logger.error(f"Error processing user association {error_id}: {str(e)}")
                
        return stats
    
    @sync_to_async
    def upsert_record(self, record_data: Dict[str, Any], record_id: int) -> str:
        """Create or update a user association record"""
        
        # Check if record exists
        try:
            existing_record = Genius_UserAssociation.objects.get(id=record_id)
            
            # Update existing record
            for field, value in record_data.items():
                if field not in ['sync_created_at', 'sync_updated_at']:
                    setattr(existing_record, field, value)
            
            existing_record.save()
            return 'updated'
            
        except Genius_UserAssociation.DoesNotExist:
            # Create new record
            Genius_UserAssociation.objects.create(**record_data)
            return 'created'
