"""
Prospects processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from django.db import IntegrityError, transaction
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class GeniusProspectsProcessor:
    """Processor for Genius prospects data with bulk operations"""
    
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
        if record.get('add_date'):
            record['add_date'] = self.convert_timezone_aware(record['add_date'])
        
        if record.get('updated_at'):
            record['updated_at'] = self.convert_timezone_aware(record['updated_at'])
        
        return record
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prospect record data"""
        
        # Check for required ID field (allow ID = 0, but not None or empty)
        if record_data.get('id') is None or record_data.get('id') == '':
            logger.error(f"Prospect record missing required ID field")
            raise ValueError("Missing required ID field")
        
        # Validate division_id exists 
        if not record_data.get('division_id'):
            logger.warning(f"Prospect {record_data.get('id')} missing division_id")
        
        # Validate updated_at timestamp
        if not record_data.get('updated_at'):
            logger.warning(f"Prospect {record_data.get('id')} missing updated_at timestamp")
        
        return record_data
    
    async def process_batch(self, batch_data: List[tuple], field_mapping: List[str], 
                           force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of prospects data using bulk operations"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        try:
            # Transform batch data to model instances  
            model_instances = []
            for raw_row in batch_data:
                try:
                    # Transform and validate record
                    record_data = self.transform_record(raw_row, field_mapping)
                    record_data = self.validate_record(record_data)
                    
                    # Create model instance (excluding third_party_source_id which isn't in the model)
                    instance = self.model_class(
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
                    
                    model_instances.append(instance)
                    stats['total_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error transforming prospect record {raw_row[0] if raw_row else 'unknown'}: {e}")
                    stats['errors'] += 1
            
            if not model_instances:
                logger.warning("No valid model instances to process")
                return stats
            
            # Perform bulk upsert using bulk_create with update_conflicts
            @sync_to_async
            def bulk_upsert():
                created_count = 0
                updated_count = 0
                
                try:
                    # Use bulk_create with update_conflicts for efficient upsert
                    results = self.model_class.objects.bulk_create(
                        model_instances,
                        update_conflicts=True,
                        update_fields=[
                            'division_id', 'user_id', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
                            'address1', 'address2', 'city', 'county', 'state', 'zip', 'year_built', 'phone1', 'phone2',
                            'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id',
                            'updated_at', 'hubspot_contact_id'
                        ],
                        unique_fields=['id'],
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
                created_count, updated_count = await bulk_upsert()
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
        
        return stats
