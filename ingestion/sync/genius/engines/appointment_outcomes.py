"""
appointment outcomes sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base import GeniusBaseSyncEngine

logger = logging.getLogger(__name__)


class GeniusAppointmentOutcomesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius appointment outcomes data"""
    
    def __init__(self):
        super().__init__('appointment_outcomes')
    
    async def execute_sync(self, 
                          full: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False,
                          **kwargs) -> Dict[str, Any]:
        """Execute sync operation"""
        
        logger.info(f"Starting {self.entity_type} sync (full={full}, dry_run={dry_run})")
        
        # Import at runtime to avoid circular imports
        from ingestion.sync.genius.clients.appointment_outcomes import GeniusAppointmentOutcomeClient
        from ingestion.sync.genius.processors.appointment_outcomes import GeniusAppointmentOutcomeProcessor
        from ingestion.models.genius import Genius_AppointmentOutcome
        
        # Initialize stats
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
        }
        
        # Create sync record
        configuration = {
            'full': full,
            'since': since.isoformat() if since else None,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'max_records': max_records,
            'dry_run': dry_run
        }
        sync_record = await self.create_sync_record(configuration)
        
        try:
            # Initialize client and processor
            client = GeniusAppointmentOutcomeClient()
            processor = GeniusAppointmentOutcomeProcessor(Genius_AppointmentOutcome)
            
            # Determine sync timestamp
            sync_start = start_date or since
            if not sync_start and not full:
                sync_start = await self.get_last_sync_timestamp()
            
            if debug:
                logger.info(f"Sync parameters: full={full}, sync_start={sync_start}")
            
            # Fetch data from Genius database
            logger.info("Fetching appointment outcomes from Genius database...")
            raw_records = client.get_appointment_outcomes(
                since_date=sync_start,
                limit=max_records or 0
            )
            
            if debug:
                logger.info(f"Retrieved {len(raw_records)} raw records")
            
            # Convert tuples to dictionaries using field mapping
            field_mapping = client.get_field_mapping()
            records = []
            for raw_record in raw_records:
                if len(raw_record) != len(field_mapping):
                    logger.warning(f"Field count mismatch: got {len(raw_record)} fields, expected {len(field_mapping)}")
                    continue
                
                record_dict = dict(zip(field_mapping, raw_record))
                records.append(record_dict)
            
            if debug:
                logger.info(f"Converted to {len(records)} dictionary records")
            
            # Process records in batches
            batch_size = 100
            objects_to_create = []
            objects_to_update = []
            
            for i, record in enumerate(records):
                try:
                    # Transform and validate record
                    if not processor.validate_record(record):
                        stats['errors'] += 1
                        continue
                    
                    transformed_record = processor.transform_record(record)
                    
                    if debug and i < 3:  # Show first few records in debug mode
                        logger.info(f"Transformed record {i+1}: {transformed_record}")
                    
                    # Prepare for bulk operation
                    record_id = transformed_record.get('id')
                    if record_id:
                        # Check if record exists
                        try:
                            existing = await self._async_get_or_none(Genius_AppointmentOutcome, id=record_id)
                            if existing:
                                # Update existing record
                                for field, value in transformed_record.items():
                                    if hasattr(existing, field):
                                        setattr(existing, field, value)
                                objects_to_update.append(existing)
                            else:
                                # Create new record
                                objects_to_create.append(Genius_AppointmentOutcome(**transformed_record))
                        except Exception as e:
                            logger.error(f"Error checking existing record {record_id}: {e}")
                            stats['errors'] += 1
                            continue
                    
                    stats['processed'] += 1
                    
                    # Process batch when it reaches batch_size
                    if len(objects_to_create) + len(objects_to_update) >= batch_size:
                        batch_stats = await self._process_batch(objects_to_create, objects_to_update, dry_run, debug)
                        stats['created'] += batch_stats['created']
                        stats['updated'] += batch_stats['updated']
                        stats['errors'] += batch_stats['errors']
                        objects_to_create = []
                        objects_to_update = []
                
                except Exception as e:
                    logger.error(f"Error processing record {i+1}: {e}")
                    stats['errors'] += 1
                    continue
            
            # Process remaining records
            if objects_to_create or objects_to_update:
                batch_stats = await self._process_batch(objects_to_create, objects_to_update, dry_run, debug)
                stats['created'] += batch_stats['created']
                stats['updated'] += batch_stats['updated']
                stats['errors'] += batch_stats['errors']
            
            # Complete sync record with success
            await self.complete_sync_record(sync_record, stats)
            
            logger.info(f"Completed {self.entity_type} sync: {stats['processed']} processed, "
                       f"{stats['created']} created, {stats['updated']} updated, {stats['errors']} errors")
            
            return {
                'stats': stats,
                'sync_id': sync_record.id,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            await self.fail_sync_record(sync_record, str(e))
            raise
    
    async def _async_get_or_none(self, model_class, **kwargs):
        """Async wrapper for get_or_create operations"""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_or_none():
            try:
                return model_class.objects.get(**kwargs)
            except model_class.DoesNotExist:
                return None
        
        return await get_or_none()
    
    async def _process_batch(self, objects_to_create, objects_to_update, dry_run, debug):
        """Process a batch of objects for creation/update"""
        from asgiref.sync import sync_to_async
        
        batch_stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        if dry_run:
            # In dry-run mode, just count what would be processed
            batch_stats['created'] = len(objects_to_create)
            batch_stats['updated'] = len(objects_to_update)
            if debug:
                logger.info(f"DRY-RUN: Would create {len(objects_to_create)} and update {len(objects_to_update)} records")
            return batch_stats
        
        # Create new records
        if objects_to_create:
            try:
                @sync_to_async
                def bulk_create():
                    from ingestion.models.genius import Genius_AppointmentOutcome
                    return Genius_AppointmentOutcome.objects.bulk_create(
                        objects_to_create, 
                        ignore_conflicts=True
                    )
                
                created_objects = await bulk_create()
                batch_stats['created'] = len(created_objects)
                if debug:
                    logger.info(f"Created {len(created_objects)} new appointment outcome records")
                    
            except Exception as e:
                logger.error(f"Error creating appointment outcome records: {e}")
                batch_stats['errors'] += len(objects_to_create)
        
        # Update existing records
        if objects_to_update:
            try:
                @sync_to_async
                def bulk_save():
                    count = 0
                    for obj in objects_to_update:
                        obj.save()
                        count += 1
                    return count
                
                updated_count = await bulk_save()
                batch_stats['updated'] = updated_count
                if debug:
                    logger.info(f"Updated {updated_count} existing appointment outcome records")
                    
            except Exception as e:
                logger.error(f"Error updating appointment outcome records: {e}")
                batch_stats['errors'] += len(objects_to_update)
        
        return batch_stats

