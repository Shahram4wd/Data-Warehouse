"""
Genius Appointments Data Processor
Handles transformation and validation of appointments data
"""
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from ingestion.models import Genius_Appointment, Genius_Prospect, Genius_ProspectSource, Genius_AppointmentType, Genius_AppointmentOutcome

logger = logging.getLogger(__name__)


class GeniusAppointmentsProcessor:
    """Processor for transforming and loading appointments data"""
    
    def __init__(self):
        self.batch_size = 500
    
    async def process_batch(self, records: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
        """
        Process a batch of appointment records
        
        Args:
            records: List of raw appointment records from Genius database
            dry_run: If True, don't actually save to database
            
        Returns:
            Dictionary with counts of created, updated, errors
        """
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        if not records:
            return stats
        
        logger.info(f"Processing batch of {len(records)} appointment records")
        
        # Process records in smaller batches for memory management
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            batch_stats = await self._process_single_batch(batch, dry_run)
            
            # Aggregate stats
            for key in stats:
                stats[key] += batch_stats[key]
            
            logger.info(f"Processed batch: {len(batch)} records, Total: {i + len(batch)}/{len(records)}")
        
        return stats
    
    @sync_to_async
    def _process_single_batch(self, records: List[Dict[str, Any]], dry_run: bool) -> Dict[str, int]:
        """Process a single batch of records synchronously using bulk operations for performance"""
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        if dry_run:
            # For dry run, just validate transformations
            for record in records:
                try:
                    transformed = self.transform_record(record)
                    if transformed:
                        # Check if record exists for dry run stats
                        exists = Genius_Appointment.objects.filter(id=record['id']).exists()
                        if exists:
                            stats['updated'] += 1
                        else:
                            stats['created'] += 1
                except Exception as e:
                    stats['errors'] += 1
            return stats
        
        # Transform all records first
        appointment_instances = []
        for record in records:
            try:
                transformed = self.transform_record(record)
                if transformed:
                    appointment_instances.append(Genius_Appointment(**transformed))
                else:
                    stats['errors'] += 1
            except Exception as e:
                record_id = record.get('id', 'Unknown')
                logger.error(f"Error transforming appointment record ID {record_id}: {e}")
                stats['errors'] += 1
        
        if not appointment_instances:
            return stats
        
        # Bulk upsert using Django's bulk_create with update_conflicts
        try:
            with transaction.atomic():
                logger.info(f"Bulk upserting {len(appointment_instances)} appointment records")
                
                # Define fields to update on conflict
                update_fields = [
                    'prospect_id', 'prospect_source_id', 'user_id', 'type_id',
                    'date', 'time', 'duration', 'address1', 'address2', 'city', 
                    'state', 'zip', 'email', 'notes', 'add_user_id', 'add_date',
                    'assign_date', 'confirm_user_id', 'confirm_date', 'confirm_with',
                    'spouses_present', 'is_complete', 'complete_outcome_id',
                    'complete_user_id', 'complete_date', 'marketsharp_id',
                    'marketsharp_appt_type', 'leap_estimate_id', 'hubspot_appointment_id',
                    'updated_at'
                ]
                
                created_appointments = Genius_Appointment.objects.bulk_create(
                    appointment_instances,
                    update_conflicts=True,
                    update_fields=update_fields,
                    unique_fields=['id']
                )
                
                # Count results - bulk_create returns all instances but _state.adding indicates new records
                batch_created = sum(1 for appt in created_appointments if appt._state.adding)
                stats['created'] = batch_created
                stats['updated'] = len(appointment_instances) - batch_created
                
                logger.info(f"Bulk upsert completed - Created: {stats['created']}, Updated: {stats['updated']}")
                
        except Exception as e:
            logger.error(f"Error in bulk upsert: {e}")
            stats['errors'] += len(appointment_instances)
        
        return stats
    
    def transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform raw database record to model-compatible format"""
        record_id = record.get('id', 'Unknown')
        try:
            # Handle date and time fields with individual error handling
            try:
                appointment_date = self._convert_date(record.get('date'))
            except Exception as e:
                logger.error(f"Error converting date field for appointment ID {record_id}: {e}, value: {record.get('date')}")
                appointment_date = None
                
            try:
                appointment_time = self._convert_time(record.get('time'))
            except Exception as e:
                logger.error(f"Error converting time field for appointment ID {record_id}: {e}, value: {record.get('time')}")
                appointment_time = None
                
            try:
                add_date = self._convert_datetime(record.get('add_date'))
                # If add_date is null or empty, use the appointment date as fallback
                if add_date is None and appointment_date is not None:
                    logger.debug(f"Using appointment date as add_date fallback for appointment ID {record_id}")
                    add_date = datetime.combine(appointment_date, time.min)
                    add_date = timezone.make_aware(add_date) if not timezone.is_aware(add_date) else add_date
            except Exception as e:
                logger.error(f"Error converting add_date field for appointment ID {record_id}: {e}, value: {record.get('add_date')}")
                # Use appointment date as fallback when add_date conversion fails
                if appointment_date is not None:
                    logger.debug(f"Using appointment date as add_date fallback after conversion error for appointment ID {record_id}")
                    add_date = datetime.combine(appointment_date, time.min)
                    add_date = timezone.make_aware(add_date) if not timezone.is_aware(add_date) else add_date
                else:
                    add_date = None
                
            try:
                assign_date = self._convert_datetime(record.get('assign_date'))
            except Exception as e:
                logger.error(f"Error converting assign_date field for appointment ID {record_id}: {e}, value: {record.get('assign_date')}")
                assign_date = None
                
            try:
                confirm_date = self._convert_datetime(record.get('confirm_date'))
            except Exception as e:
                logger.error(f"Error converting confirm_date field for appointment ID {record_id}: {e}, value: {record.get('confirm_date')}")
                confirm_date = None
                
            try:
                complete_date = self._convert_datetime(record.get('complete_date'))
            except Exception as e:
                logger.error(f"Error converting complete_date field for appointment ID {record_id}: {e}, value: {record.get('complete_date')}")
                complete_date = None
                
            try:
                updated_at = self._convert_datetime(record.get('updated_at'))
            except Exception as e:
                logger.error(f"Error converting updated_at field for appointment ID {record_id}: {e}, value: {record.get('updated_at')}")
                updated_at = None
            
            # Transform the record
            transformed = {
                'id': record.get('id'),
                'prospect_id': record.get('prospect_id'),
                'prospect_source_id': record.get('prospect_source_id'),
                'user_id': record.get('user_id'),
                'type_id': record.get('type_id'),
                'date': appointment_date,
                'time': appointment_time,
                'duration': self._convert_duration(record.get('duration')),
                'address1': record.get('address1'),
                'address2': record.get('address2'),
                'city': record.get('city'),
                'state': record.get('state'),
                'zip': record.get('zip'),
                'email': record.get('email'),
                'notes': record.get('notes'),
                'add_user_id': record.get('add_user_id'),
                'add_date': add_date,
                'assign_date': assign_date,
                'confirm_user_id': record.get('confirm_user_id'),
                'confirm_date': confirm_date,
                'confirm_with': record.get('confirm_with'),
                'spouses_present': self._convert_boolean(record.get('spouses_present')),
                'is_complete': self._convert_boolean(record.get('is_complete')),
                'complete_outcome_id': record.get('complete_outcome_id'),
                'complete_user_id': record.get('complete_user_id'),
                'complete_date': complete_date,
                'marketsharp_id': record.get('marketsharp_id'),
                'marketsharp_appt_type': record.get('marketsharp_appt_type'),
                'leap_estimate_id': record.get('leap_estimate_id'),
                'hubspot_appointment_id': record.get('hubspot_appointment_id'),
                'updated_at': updated_at,
            }
            
            return transformed
            
        except Exception as e:
            record_id = record.get('id', 'Unknown')
            error_msg = str(e)
            
            # Enhanced transformation error logging
            if 'fromisoformat' in error_msg:
                logger.error(f"Error transforming appointment record ID {record_id}: Date/time format error - {error_msg}")
                logger.error(f"Problematic date/time fields: date={record.get('date')}, time={record.get('time')}, add_date={record.get('add_date')}")
            else:
                logger.error(f"Error transforming appointment record ID {record_id}: {error_msg}")
                logger.error(f"Record sample fields: {dict(list(record.items())[:5])}")  # Show first 5 fields for context
            return None
    
    def transform_and_save_record(self, record: Dict[str, Any]) -> Optional[Genius_Appointment]:
        """Transform and save a single appointment record"""
        record_id = record.get('id', 'Unknown')
        try:
            transformed = self.transform_record(record)
            if not transformed:
                return None
            
            # Get or create the appointment
            appointment, created = Genius_Appointment.objects.update_or_create(
                id=transformed['id'],
                defaults=transformed
            )
            
            # Store creation flag for stats tracking
            appointment._created = created
            return appointment
            
        except Exception as e:
            # Enhanced error logging with field information
            error_msg = str(e)
            if 'Invalid field name' in error_msg:
                # Extract field name from Django error message
                field_name = error_msg.split("'")[1] if "'" in error_msg else "unknown field"
                logger.error(f"Error saving appointment record ID {record_id}: Invalid field '{field_name}' - {error_msg}")
            elif hasattr(e, 'message_dict'):
                # Django validation errors with field-specific messages
                field_errors = []
                for field, messages in e.message_dict.items():
                    field_errors.append(f"{field}: {', '.join(messages)}")
                logger.error(f"Error saving appointment record ID {record_id}: Field validation errors - {'; '.join(field_errors)}")
            else:
                # Generic error with more context
                logger.error(f"Error saving appointment record ID {record_id}: {error_msg}")
                logger.error(f"Record data keys: {list(record.keys())}")
                if transformed:
                    logger.error(f"Transformed data keys: {list(transformed.keys())}")
            return None
    
    def _convert_date(self, value) -> Optional[datetime]:
        """Convert various date formats to datetime.date"""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value.date()
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    logger.warning(f"Could not parse date: {value}")
                    return None
        
        return value
    
    def _convert_time(self, value) -> Optional[time]:
        """Convert various time formats to datetime.time"""
        if value is None:
            return None
        
        if isinstance(value, time):
            return value
        elif isinstance(value, timedelta):
            # Convert timedelta to time (seconds since midnight)
            total_seconds = int(value.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return time(hours % 24, minutes, seconds)  # Ensure hours are within 0-23
        elif isinstance(value, str):
            try:
                # Handle HH:MM:SS format
                return datetime.strptime(value, '%H:%M:%S').time()
            except ValueError:
                try:
                    # Handle HH:MM format
                    return datetime.strptime(value, '%H:%M').time()
                except ValueError:
                    logger.warning(f"Could not parse time: {value}")
                    return None
        
        return value
    
    def _convert_datetime(self, value) -> Optional[datetime]:
        """Convert various datetime formats to timezone-aware datetime (UTC)"""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            # If already timezone-aware, return as is; otherwise make it UTC
            if value.tzinfo is None:
                return timezone.make_aware(value, timezone=timezone.utc)
            return value
        elif isinstance(value, str):
            try:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                return timezone.make_aware(dt, timezone=timezone.utc)
            except ValueError:
                try:
                    dt = datetime.strptime(value, '%Y-%m-%d')
                    return timezone.make_aware(dt, timezone=timezone.utc)
                except ValueError:
                    logger.warning(f"Could not parse datetime: {value}")
                    return None
        
        return value
    
    def _convert_duration(self, value) -> Optional[timedelta]:
        """Convert various duration formats to timedelta"""
        if value is None:
            return None
        
        if isinstance(value, timedelta):
            return value
        elif isinstance(value, (int, float)):
            # Assume seconds if it's a number
            return timedelta(seconds=value)
        elif isinstance(value, str):
            try:
                # Try to parse as seconds
                seconds = float(value)
                return timedelta(seconds=seconds)
            except ValueError:
                logger.warning(f"Could not parse duration: {value}")
                return None
        
        return value
    
    def _convert_boolean(self, value) -> bool:
        """Convert various boolean representations to bool"""
        if value is None:
            return False
        
        if isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return bool(value)
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        
        return bool(value)
