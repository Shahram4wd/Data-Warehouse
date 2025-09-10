"""
appointment outcome types sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.appointment_outcome_types import GeniusAppointmentOutcomeTypeClient
from ..processors.appointment_outcome_types import GeniusAppointmentOutcomeTypeProcessor
from ingestion.models import Genius_AppointmentOutcomeType

logger = logging.getLogger(__name__)


class GeniusAppointmentOutcomeTypesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius appointment outcome types data"""
    
    def __init__(self):
        super().__init__('appointment_outcome_types')
        self.client = GeniusAppointmentOutcomeTypeClient()
        self.processor = GeniusAppointmentOutcomeTypeProcessor(Genius_AppointmentOutcomeType)
    
    async def execute_sync(self, 
                          full: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False,
                          **kwargs) -> Dict[str, Any]:
        """Execute the appointment outcome types sync process - adapter for standard sync interface"""
        
        # Convert parameters to match existing method signature
        since_date = since
        force_overwrite = full
        
        return await self.sync_appointment_outcome_types(
            since_date=since_date, 
            force_overwrite=force_overwrite,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
    async def sync_appointment_outcome_types(self, since_date=None, force_overwrite=False, 
                                           dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for appointment outcome types"""
        
        # Get last sync timestamp if no since_date provided and not force_overwrite
        if since_date is None and not force_overwrite:
            since_date = await self.get_last_sync_timestamp()
            if since_date:
                logger.info(f"Using last sync timestamp for incremental sync: {since_date}")
            else:
                logger.info("No previous sync found, performing full sync")
        elif force_overwrite:
            logger.info("Force overwrite requested, performing full sync")
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Create sync record
        configuration = {
            'full': force_overwrite,
            'since_date': since_date.isoformat() if since_date else None,
            'max_records': max_records,
            'dry_run': dry_run
        }
        sync_record = await self.create_sync_record(configuration)
        
        try:
            # Connect to database
            await sync_to_async(self.client.connect)()
            
            # Get appointment outcome types from source
            raw_appointment_outcome_types = await sync_to_async(self.client.get_appointment_outcome_types)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_appointment_outcome_types)} appointment outcome types from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process appointment outcome types but making no changes")
                stats['total_processed'] = len(raw_appointment_outcome_types)
                await self.complete_sync_record(sync_record, stats)
                return {
                    'stats': {
                        'processed': stats['total_processed'],
                        'created': stats['created'],
                        'updated': stats['updated'],
                        'errors': stats['errors']
                    },
                    'sync_id': sync_record.id,
                    'status': 'success'
                }
            
            # Process appointment outcome types in batches (smaller batch for lookup tables)
            batch_size = 100
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_appointment_outcome_types), batch_size):
                batch = raw_appointment_outcome_types[i:i + batch_size]
                batch_stats = await self._process_appointment_outcome_type_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Appointment outcome type sync completed. Total stats: {stats}")
            
            # Complete sync record
            await self.complete_sync_record(sync_record, stats)
            
            return {
                'stats': {
                    'processed': stats['total_processed'],
                    'created': stats['created'],
                    'updated': stats['updated'],
                    'errors': stats['errors']
                },
                'sync_id': sync_record.id,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Appointment outcome type sync failed: {str(e)}")
            await self.complete_sync_record(sync_record, stats, str(e))
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_appointment_outcome_type_batch(self, batch: List[tuple], field_mapping: List[str], 
                                              force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of appointment outcome type records"""
        
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
                    if not validated_data.get('id'):
                        logger.warning("Skipping appointment outcome type with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Get or create appointment outcome type
                    appointment_outcome_type, created = Genius_AppointmentOutcomeType.objects.get_or_create(
                        id=validated_data['id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created appointment outcome type {appointment_outcome_type.id}: {appointment_outcome_type.label}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_appointment_outcome_type(appointment_outcome_type, validated_data):
                            for field, value in validated_data.items():
                                if field != 'id':  # Don't update primary key
                                    setattr(appointment_outcome_type, field, value)
                            appointment_outcome_type.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated appointment outcome type {appointment_outcome_type.id}: {appointment_outcome_type.label}")
                        else:
                            stats['skipped'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing appointment outcome type record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_appointment_outcome_type(self, existing: Genius_AppointmentOutcomeType, new_data: Dict[str, Any]) -> bool:
        """Check if appointment outcome type should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['label', 'sort_idx', 'is_active']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False

