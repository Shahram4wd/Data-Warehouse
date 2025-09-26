"""
Genius Appointment Services Data Processor
Handles transformation and validation of appointment services data
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

from ingestion.models import Genius_AppointmentService

logger = logging.getLogger(__name__)

class GeniusAppointmentServicesProcessor:
    """Processor for transforming and loading appointment services data"""
    
    def __init__(self, model_class=None):
        self.model_class = model_class or Genius_AppointmentService
        
    def process_batch(self, batch_data: List[tuple], field_mapping: List[str], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """
        Process a batch of appointment services data with bulk operations
        
        Args:
            batch_data: List of tuples containing appointment services data
            field_mapping: List of field names matching data order
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            
        Returns:
            Dictionary containing batch processing statistics
        """
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not batch_data:
            return stats
        
        logger.info(f"Processing batch of {len(batch_data)} appointment services records")
        
        # Track transformation time
        transform_start = timezone.now()
        
        # Transform data to model instances
        transformed_records = []
        skipped_invalid_dates = 0
        
        for raw_data in batch_data:
            try:
                # Convert tuple to dictionary using field mapping
                data_dict = dict(zip(field_mapping, raw_data))
                
                # Transform the record
                transformed = self._transform_record(data_dict)
                if transformed:
                    transformed_records.append(transformed)
                    stats['total_processed'] += 1
                else:
                    # Count records skipped due to invalid dates
                    if data_dict.get('created_at') or data_dict.get('updated_at'):
                        skipped_invalid_dates += 1
                    
            except Exception as e:
                logger.error(f"Error transforming appointment services record {raw_data}: {e}")
                stats['errors'] += 1
        
        transform_duration = (timezone.now() - transform_start).total_seconds()
        
        if skipped_invalid_dates > 0:
            logger.info(f"Skipped {skipped_invalid_dates} records with invalid/epoch dates")
        
        logger.debug(f"Transformation completed in {transform_duration:.2f}s")
        
        if not transformed_records or dry_run:
            if dry_run:
                logger.info(f"DRY RUN: Would process {len(transformed_records)} appointment services records")
                stats['created'] = len(transformed_records)  # Simulate creation for dry run
            return stats
        
        # Bulk create/update operations with performance tracking
        try:
            db_start = timezone.now()
            
            if force_overwrite:
                db_stats = self._bulk_force_update(transformed_records)
            else:
                db_stats = self._bulk_upsert(transformed_records)
            
            db_duration = (timezone.now() - db_start).total_seconds()
            
            stats.update(db_stats)
            
            # Log performance metrics
            total_records = db_stats.get('created', 0) + db_stats.get('updated', 0)
            if total_records > 0 and db_duration > 0:
                records_per_second = total_records / db_duration
                logger.info(f"Database operation completed in {db_duration:.2f}s "
                           f"({records_per_second:.1f} records/second)")
                
        except Exception as e:
            logger.error(f"Error during bulk operation: {e}")
            stats['errors'] += len(transformed_records)
            
        return stats
    
    def _transform_record(self, data_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a single appointment services record
        
        Args:
            data_dict: Dictionary containing appointment services data
            
        Returns:
            Transformed data dictionary or None if invalid
        """
        try:
            # Basic field extraction and validation
            appointment_id = data_dict.get('appointment_id')
            service_id = data_dict.get('service_id')
            
            if not appointment_id or not service_id:
                logger.warning(f"Missing required fields in appointment services record: {data_dict}")
                return None
            
            # Parse datetime fields
            created_at = self._parse_datetime(data_dict.get('created_at'))
            updated_at = self._parse_datetime(data_dict.get('updated_at'))
            
            # Build transformed record with proper defaults for NULL values
            transformed = {
                'appointment_id': int(appointment_id),
                'service_id': int(service_id),
                'created_at': created_at or updated_at or timezone.now(),  # Use updated_at or current time if created_at is None
                'updated_at': updated_at or timezone.now(),  # Use current time if updated_at is None
                'sync_updated_at': timezone.now()
            }
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming appointment services record {data_dict}: {e}")
            return None
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime value from various formats and ensure timezone awareness"""
        if not value:
            return None
            
        if isinstance(value, datetime):
            # If datetime is naive, make it timezone-aware (assume UTC)
            if value.tzinfo is None:
                # Handle special case of epoch/invalid dates
                if value.year == 1970 and value.month == 1 and value.day == 1:
                    return None  # Skip invalid epoch dates
                return timezone.make_aware(value, timezone.utc)
            return value
            
        if isinstance(value, str):
            # Skip empty or invalid strings
            if not value.strip() or value == '0000-00-00 00:00:00':
                return None
                
            try:
                # Try parsing ISO format first
                from django.utils.dateparse import parse_datetime
                parsed = parse_datetime(value)
                if parsed:
                    if parsed.tzinfo is None:
                        parsed = timezone.make_aware(parsed, timezone.utc)
                    return parsed
                    
                # Try other common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(value.strip(), fmt)
                        # Handle special case of epoch/invalid dates
                        if dt.year == 1970 and dt.month == 1 and dt.day == 1:
                            return None
                        return timezone.make_aware(dt, timezone.utc)
                    except ValueError:
                        continue
                        
            except Exception as e:
                logger.debug(f"Failed to parse datetime '{value}': {e}")
                
        return None
    
    def _bulk_upsert(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Perform bulk upsert operation with optimized single-query approach"""
        stats = {'created': 0, 'updated': 0}
        
        if not records:
            return stats
        
        # Use efficient separate bulk create and update operations
        try:
            with transaction.atomic():
                # Group records by unique key (appointment_id, service_id)
                records_dict = {}
                for record in records:
                    key = (record['appointment_id'], record['service_id'])
                    records_dict[key] = record
                
                # Check which records already exist
                existing_records = self.model_class.objects.filter(
                    appointment_id__in=[r['appointment_id'] for r in records],
                    service_id__in=[r['service_id'] for r in records]
                ).values('appointment_id', 'service_id', 'id')
                
                existing_keys = {(r['appointment_id'], r['service_id']): r['id'] for r in existing_records}
                
                # Separate into creates and updates
                creates = []
                updates = []
                
                for key, record in records_dict.items():
                    if key in existing_keys:
                        updates.append(record)
                    else:
                        creates.append(record)
                
                # Perform bulk update using raw SQL for better performance
                if updates:
                    self._bulk_update_records(updates)
                
                # Bulk create new records
                if creates:
                    create_objects = [self.model_class(**record) for record in creates]
                    self.model_class.objects.bulk_create(create_objects, batch_size=500)
                    stats['created'] = len(creates)
                    logger.info(f"Created {len(creates)} new appointment services records")
                
                stats['updated'] = len(updates)
                if stats['updated'] > 0:
                    logger.info(f"Updated {len(updates)} appointment services records")
                    
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            # Use the more efficient fallback method
            stats = self._optimized_fallback_upsert(records)
        
        return stats
    
    def _bulk_update_records(self, updates: List[Dict[str, Any]]):
        """Perform bulk update using efficient raw SQL for maximum performance"""
        from django.db import connection
        
        if not updates:
            return
        
        # Use case-when bulk update for maximum performance
        # This updates all records in a single SQL statement
        appointment_ids = [r['appointment_id'] for r in updates]
        
        # Build CASE-WHEN clauses for each field
        created_at_cases = []
        updated_at_cases = []
        sync_updated_at_cases = []
        
        for record in updates:
            aid = record['appointment_id']
            sid = record['service_id']
            
            created_at_str = record['created_at'].strftime('%Y-%m-%d %H:%M:%S.%f%z') if record['created_at'] else 'NULL'
            updated_at_str = record['updated_at'].strftime('%Y-%m-%d %H:%M:%S.%f%z') if record['updated_at'] else 'NULL'
            sync_updated_at_str = record['sync_updated_at'].strftime('%Y-%m-%d %H:%M:%S.%f%z') if record['sync_updated_at'] else 'NULL'
            
            created_at_cases.append(f"WHEN appointment_id = {aid} AND service_id = {sid} THEN '{created_at_str}'::timestamptz")
            updated_at_cases.append(f"WHEN appointment_id = {aid} AND service_id = {sid} THEN '{updated_at_str}'::timestamptz")
            sync_updated_at_cases.append(f"WHEN appointment_id = {aid} AND service_id = {sid} THEN '{sync_updated_at_str}'::timestamptz")
        
        # Build the bulk update query
        table_name = self.model_class._meta.db_table
        
        update_query = f"""
        UPDATE {table_name} 
        SET 
            created_at = CASE 
                {' '.join(created_at_cases)}
                ELSE created_at 
            END,
            updated_at = CASE 
                {' '.join(updated_at_cases)}
                ELSE updated_at 
            END,
            sync_updated_at = CASE 
                {' '.join(sync_updated_at_cases)}
                ELSE sync_updated_at 
            END
        WHERE appointment_id IN ({','.join(map(str, appointment_ids))})
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(update_query)
                logger.debug(f"Bulk updated {cursor.rowcount} records with raw SQL")
        except Exception as e:
            logger.error(f"Raw SQL bulk update failed: {e}")
            # Fallback to simpler batch update
            self._simple_batch_update(updates)
    
    def _simple_batch_update(self, updates: List[Dict[str, Any]]):
        """Simple batch update fallback"""
        logger.info("Using simple batch update fallback")
        for record in updates:
            try:
                self.model_class.objects.filter(
                    appointment_id=record['appointment_id'],
                    service_id=record['service_id']
                ).update(
                    created_at=record['created_at'],
                    updated_at=record['updated_at'],
                    sync_updated_at=record['sync_updated_at']
                )
            except Exception as e:
                logger.debug(f"Failed to update record {record}: {e}")
    
    def _optimized_fallback_upsert(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Optimized fallback method using bulk operations without constraints"""
        stats = {'created': 0, 'updated': 0}
        
        logger.warning("Using optimized fallback upsert method")
        
        try:
            with transaction.atomic():
                # First, try to just bulk create and ignore conflicts
                create_objects = [self.model_class(**record) for record in records]
                created_objects = self.model_class.objects.bulk_create(
                    create_objects, 
                    ignore_conflicts=True,
                    batch_size=500
                )
                
                # Count successful creates (this is approximate)
                stats['created'] = len(records)
                logger.info(f"Fallback: Processed {len(records)} appointment services records (ignore conflicts)")
                
        except Exception as e:
            logger.error(f"Optimized fallback failed: {e}")
            # Final fallback - but process in batches to be faster
            stats = self._batch_fallback_upsert(records)
                
        return stats
    
    def _batch_fallback_upsert(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Final fallback method using batched individual processing"""
        stats = {'created': 0, 'updated': 0}
        
        logger.warning("Using batch fallback upsert method - this will be slower")
        
        batch_size = 50  # Smaller batches for individual processing
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            for record in batch:
                try:
                    # Check if record exists first
                    existing = self.model_class.objects.filter(
                        appointment_id=record['appointment_id'],
                        service_id=record['service_id']
                    ).first()
                    
                    if existing:
                        # Update existing record
                        for key, value in record.items():
                            setattr(existing, key, value)
                        existing.save()
                        stats['updated'] += 1
                    else:
                        # Create new record
                        self.model_class.objects.create(**record)
                        stats['created'] += 1
                        
                except Exception as e:
                    logger.debug(f"Failed to process record {record}: {e}")
            
            # Log progress every batch
            if i % (batch_size * 5) == 0:  # Every 5 batches
                total_processed = min(i + batch_size, len(records))
                logger.info(f"Processed {total_processed}/{len(records)} records in fallback mode")
                
        return stats
    
    def _bulk_force_update(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Perform bulk force update - delete and recreate all records"""
        stats = {'created': 0, 'updated': 0}
        
        # Get all appointment_ids and service_ids to delete
        appointment_ids = [r['appointment_id'] for r in records]
        service_ids = [r['service_id'] for r in records]
        
        with transaction.atomic():
            # Delete existing records
            deleted_count, _ = self.model_class.objects.filter(
                appointment_id__in=appointment_ids,
                service_id__in=service_ids
            ).delete()
            
            # Bulk create all records as new
            create_objects = [
                self.model_class(**record) for record in records
            ]
            self.model_class.objects.bulk_create(create_objects, batch_size=500)
            
            stats['created'] = len(records)
            logger.info(f"Force update: deleted {deleted_count}, created {len(records)} appointment services records")
        
        return stats
