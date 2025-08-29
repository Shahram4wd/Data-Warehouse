"""
Appointment Type sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.appointment_types import GeniusAppointmentTypeClient
from ..processors.appointment_types import GeniusAppointmentTypeProcessor
from ingestion.models import Genius_AppointmentType

logger = logging.getLogger(__name__)


class GeniusAppointmentTypesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius appointment type data"""
    
    def __init__(self):
        super().__init__('appointment_types')
        self.client = GeniusAppointmentTypeClient()
        self.processor = GeniusAppointmentTypeProcessor(Genius_AppointmentType)
    
    async def execute_sync(self, 
                          full: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the appointment types sync process - adapter for standard sync interface"""
        
        # Convert parameters to match existing method signature
        since_date = since
        force_overwrite = full
        
        return await self.sync_appointment_types(
            since_date=since_date, 
            force_overwrite=force_overwrite,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
    async def sync_appointment_types(self, since_date=None, force_overwrite=False, 
                                   dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for appointment types"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get appointment types from source
            raw_appointment_types = await sync_to_async(self.client.get_appointment_types)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_appointment_types)} appointment types from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process appointment types but making no changes")
                return {
                    'success': True,
                    'sync_id': None,  # No sync record created in dry run
                    'stats': {
                        'processed': stats['total_processed'],
                        'created': stats['created'],
                        'updated': stats['updated'],
                        'errors': stats['errors'],
                        'skipped': stats['skipped']
                    }
                }
            
            # Process appointment types in batches (smaller batch for lookup tables)
            batch_size = 100
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_appointment_types), batch_size):
                batch = raw_appointment_types[i:i + batch_size]
                batch_stats = await self._process_appointment_type_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Appointment type sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Appointment type sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_appointment_type_batch(self, batch: List[tuple], field_mapping: List[str], 
                                      force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of appointment type records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        with transaction.atomic():
            for raw_record in batch:
                try:
                    stats['total_processed'] += 1
                    
                    # Transform raw data to dict
                    record_data = self.processor.transform_record(raw_record, field_mapping)
                    
                    # Validate record
                    validated_data = self.processor.validate_record(record_data)
                    
                    # Skip if required data missing
                    if not validated_data.get('genius_id'):
                        logger.warning("Skipping appointment type with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Get or create appointment type
                    appointment_type, created = Genius_AppointmentType.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created appointment type {appointment_type.genius_id}: {appointment_type.name}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_appointment_type(appointment_type, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(appointment_type, field, value)
                            appointment_type.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated appointment type {appointment_type.genius_id}: {appointment_type.name}")
                        else:
                            stats['skipped'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing appointment type record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return {
            'success': True,
            'sync_id': None,  # Add sync record ID when implemented
            'stats': {
                'processed': stats['total_processed'],
                'created': stats['created'],
                'updated': stats['updated'],
                'errors': stats['errors'],
                'skipped': stats['skipped']
            }
        }
    
    def _should_update_appointment_type(self, existing: Genius_AppointmentType, new_data: Dict[str, Any]) -> bool:
        """Check if appointment type should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['name', 'code', 'description', 'duration_minutes', 'color', 'active', 'sort_order']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
