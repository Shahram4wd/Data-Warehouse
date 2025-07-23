import os
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_UserData, Genius_Division
from ingestion.utils import get_mysql_connection
from ingestion.base.exceptions import ValidationException
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))
logger = logging.getLogger(__name__)


class GeniusUserDataProcessor:
    """Process Genius user data following import_refactoring architecture"""
    
    def __init__(self):
        self.divisions_cache = {}
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from database to model"""
        return {
            'user_id': 'id',
            'division_id': 'division_id',
            'title_id': 'title_id',
            'manager_user_id': 'manager_user_id',
            'first_name': 'first_name',
            'first_name_alt': 'first_name_alt',
            'last_name': 'last_name',
            'email': 'email',
            'personal_email': 'personal_email',
            'birth_date': 'birth_date',
            'gender_id': 'gender_id',
            'marital_status_id': 'marital_status_id',
            'time_zone_name': 'time_zone_name',
            'hired_on': 'hired_on',
            'add_datetime': 'add_datetime',
            'add_user_id': 'add_user_id',
            'start_date': 'start_date',
            'is_inactive': 'is_inactive',
            'inactive_on': 'inactive_on',
            'inactive_reason_id': 'inactive_reason_id',
            'inactive_reason_other': 'inactive_reason_other',
            'primary_user_id': 'primary_user_id',  # From joined table
        }
    
    def get_field_types(self) -> Dict[str, str]:
        """Return field type mappings for validation"""
        return {
            'id': 'integer',
            'division_id': 'integer',
            'title_id': 'integer',
            'manager_user_id': 'integer',
            'first_name': 'string',
            'first_name_alt': 'string',
            'last_name': 'string',
            'email': 'email',
            'personal_email': 'email',
            'birth_date': 'date',
            'gender_id': 'integer',
            'marital_status_id': 'integer',
            'time_zone_name': 'string',
            'hired_on': 'datetime',
            'add_datetime': 'datetime',
            'add_user_id': 'integer',
            'start_date': 'datetime',
            'is_inactive': 'boolean',
            'inactive_on': 'datetime',
            'inactive_reason_id': 'integer',
            'inactive_reason_other': 'string',
            'primary_user_id': 'integer',
        }
    
    def transform_record(self, row: Tuple) -> Dict[str, Any]:
        """Transform database row to model format following architecture"""
        # Map database fields to structured data
        field_names = [
            'user_id', 'division_id', 'title_id', 'manager_user_id', 'first_name',
            'first_name_alt', 'last_name', 'email', 'personal_email', 'birth_date', 'ssn',
            'gender_id', 'marital_status_id', 'time_zone_name', 'lead_radius_zip',
            'lead_radius_distance', 'lead_types', 'lead_views_allowed', 'lead_call_center',
            'google_calendar_channel_id', 'google_calendar_resource_id',
            'google_calendar_sync_token', 'google_calendar_sync_start',
            'google_calendar_last_sync', 'google_calendar_channel_expiration',
            'project_commission_pct', 'hired_on', 'add_datetime', 'add_user_id',
            'is_inactive', 'inactive_on', 'inactive_reason_id', 'inactive_reason_other',
            'salary_account_id', 'advance_account_id', 'inactive_transfer_division_id',
            'override_paychex_department_id', 'override_paychex_department_effective_date',
            'google_user_error', 'google_user_status', 'start_date', 'user_associations_id',
            'google_user_id', 'primary_user_id'  # From joined table
        ]
        
        raw_record = dict(zip(field_names, row))
        field_mappings = self.get_field_mappings()
        field_types = self.get_field_types()
        
        # Apply field mappings
        transformed = {}
        for source_field, target_field in field_mappings.items():
            if source_field in raw_record:
                value = raw_record[source_field]
                if value is not None:
                    try:
                        # Apply field type validation
                        if target_field in field_types:
                            field_type = field_types[target_field]
                            transformed[target_field] = self.validate_field(target_field, value, field_type, raw_record)
                        else:
                            transformed[target_field] = value
                    except ValidationException as e:
                        logger.warning(f"Validation failed for field '{target_field}' with value '{value}' for user {raw_record.get('user_id', 'UNKNOWN')}: {e}")
                        # Keep original value with fallback handling
                        if field_type == 'boolean' and target_field == 'is_inactive':
                            transformed[target_field] = bool(int(value)) if value is not None else False
                        else:
                            transformed[target_field] = value
        
        return transformed
    
    def validate_field(self, field_name: str, value: Any, field_type: str, context: Dict = None) -> Any:
        """Validate field using simplified validation logic"""
        record_id = context.get('user_id', 'UNKNOWN') if context else 'UNKNOWN'
        
        try:
            if field_type == 'integer':
                return int(value) if value is not None else None
            elif field_type == 'boolean':
                if field_name == 'is_inactive':
                    return bool(int(value)) if value is not None else False
                return bool(value) if value is not None else None
            elif field_type == 'datetime':
                return self._parse_datetime(value)
            elif field_type == 'date':
                return self._parse_date(value)
            elif field_type == 'email':
                return str(value).strip() if value else None
            elif field_type == 'string':
                return str(value).strip() if value else None
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to validate {field_type} field '{field_name}' with value '{value}' for user {record_id}: {e}")
            return value
    
    def _parse_datetime(self, value):
        """Helper function to safely parse and make datetime timezone-aware."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value
        
        return value
    
    def _parse_date(self, value):
        """Helper function to safely parse date values."""
        if value is None:
            return None
            
        if isinstance(value, datetime):
            return value.date()
            
        return value
    
    def preload_divisions(self) -> Dict[int, Any]:
        """Preload divisions for lookup following architecture pattern"""
        if not self.divisions_cache:
            self.divisions_cache = {division.id: division for division in Genius_Division.objects.all()}
            logger.info(f"Preloaded {len(self.divisions_cache)} divisions for lookup")
        return self.divisions_cache

class Command(BaseCommand):
    """Download user data from Genius database following import_refactoring architecture"""
    
    help = "Download user data directly from the database and update the local database."
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = GeniusUserDataProcessor()
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="user_data",
            help="The name of the table to download data from. Defaults to 'user_data'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            logger.info(f"Starting Genius user data sync from table '{table_name}'")
            
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data using processor
            divisions = self.processor.preload_divisions()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, divisions)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            logger.info(f"Completed Genius user data sync from table '{table_name}'")
            
        except Exception as e:
            error_msg = f"An error occurred during Genius user data sync: {e}"
            logger.error(error_msg)
            self.stdout.write(self.style.ERROR(error_msg))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _process_all_records(self, cursor, table_name, divisions):
        """Process all records in batches following architecture pattern"""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        logger.info(f"Total records in table '{table_name}': {total_records}")
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset, divisions)
    
    def _process_batch_at_offset(self, cursor, table_name, offset, divisions):
        """Process a batch of records starting at the specified offset with proper JOIN"""
        # Updated query to join with users_userassociations table to get primary_user_id
        cursor.execute(f"""
            SELECT user_data.user_id, user_data.division_id, user_data.title_id, 
                   user_data.manager_user_id, user_data.first_name, user_data.first_name_alt, 
                   user_data.last_name, user_data.email, user_data.personal_email, 
                   user_data.birth_date, user_data.ssn, user_data.gender_id, 
                   user_data.marital_status_id, user_data.time_zone_name, 
                   user_data.lead_radius_zip, user_data.lead_radius_distance, 
                   user_data.lead_types, user_data.lead_views_allowed, 
                   user_data.lead_call_center, user_data.google_calendar_channel_id, 
                   user_data.google_calendar_resource_id, user_data.google_calendar_sync_token, 
                   user_data.google_calendar_sync_start, user_data.google_calendar_last_sync, 
                   user_data.google_calendar_channel_expiration, user_data.project_commission_pct, 
                   user_data.hired_on, user_data.add_datetime, user_data.add_user_id, 
                   user_data.is_inactive, user_data.inactive_on, user_data.inactive_reason_id, 
                   user_data.inactive_reason_other, user_data.salary_account_id, 
                   user_data.advance_account_id, user_data.inactive_transfer_division_id, 
                   user_data.override_paychex_department_id, 
                   user_data.override_paychex_department_effective_date, 
                   user_data.google_user_error, user_data.google_user_status, 
                   user_data.start_date, user_data.user_associations_id, 
                   user_data.google_user_id, users_userassociations.primary_user_id
            FROM {table_name}
            LEFT JOIN users_userassociations ON user_data.user_associations_id = users_userassociations.id
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch using processor
        self._process_batch(rows, divisions)
    
    def _process_batch(self, rows, divisions):
        """Process a batch of user records using processor architecture"""
        to_create = []
        to_update = []
        existing_records = Genius_UserData.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Transform record using processor
                transformed_record = self.processor.transform_record(row)
                user_id = transformed_record.get('id')
                
                if not user_id:
                    logger.warning(f"Skipping record with no user_id: {row[:5]}")
                    continue
                
                # Get division from cache
                division_id = transformed_record.get('division_id')
                division = divisions.get(division_id) if division_id else None
                
                # Create or update record
                if user_id in existing_records:
                    record = self._update_record(existing_records[user_id], transformed_record, division)
                    to_update.append(record)
                else:
                    record = self._create_record(transformed_record, division)
                    to_create.append(record)
                    
            except Exception as e:
                record_id = row[0] if row else 'unknown'
                error_msg = f"Error processing record ID {record_id}: {e}"
                logger.error(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))

        # Save records to database
        self._save_records(to_create, to_update)
    
    def _update_record(self, record, transformed_data: Dict[str, Any], division) -> Genius_UserData:
        """Update an existing user record using transformed data"""
        # Update fields that exist in the model using transformed data
        record.division = division
        record.title_id = transformed_data.get('title_id')
        record.manager_user_id = transformed_data.get('manager_user_id')
        record.first_name = transformed_data.get('first_name')
        record.first_name_alt = transformed_data.get('first_name_alt')
        record.last_name = transformed_data.get('last_name')
        record.email = transformed_data.get('email')
        record.personal_email = transformed_data.get('personal_email')
        record.birth_date = transformed_data.get('birth_date')
        record.gender_id = transformed_data.get('gender_id')
        record.marital_status_id = transformed_data.get('marital_status_id')
        record.time_zone_name = transformed_data.get('time_zone_name')
        record.hired_on = transformed_data.get('hired_on')
        record.add_datetime = transformed_data.get('add_datetime')
        record.add_user_id = transformed_data.get('add_user_id')
        record.start_date = transformed_data.get('start_date')
        record.is_inactive = transformed_data.get('is_inactive', False)
        record.inactive_on = transformed_data.get('inactive_on')
        record.inactive_reason_id = transformed_data.get('inactive_reason_id')
        record.inactive_reason_other = transformed_data.get('inactive_reason_other')
        record.primary_user_id = transformed_data.get('primary_user_id')  # New field from JOIN
        
        return record
    
    def _create_record(self, transformed_data: Dict[str, Any], division) -> Genius_UserData:
        """Create a new user record using transformed data"""
        return Genius_UserData(
            id=transformed_data.get('id'),
            division=division,
            title_id=transformed_data.get('title_id'),
            manager_user_id=transformed_data.get('manager_user_id'),
            first_name=transformed_data.get('first_name'),
            first_name_alt=transformed_data.get('first_name_alt'),
            last_name=transformed_data.get('last_name'),
            email=transformed_data.get('email'),
            personal_email=transformed_data.get('personal_email'),
            birth_date=transformed_data.get('birth_date'),
            gender_id=transformed_data.get('gender_id'),
            marital_status_id=transformed_data.get('marital_status_id'),
            time_zone_name=transformed_data.get('time_zone_name'),
            hired_on=transformed_data.get('hired_on'),
            add_datetime=transformed_data.get('add_datetime'),
            add_user_id=transformed_data.get('add_user_id'),
            start_date=transformed_data.get('start_date'),
            is_inactive=transformed_data.get('is_inactive', False),
            inactive_on=transformed_data.get('inactive_on'),
            inactive_reason_id=transformed_data.get('inactive_reason_id'),
            inactive_reason_other=transformed_data.get('inactive_reason_other'),
            primary_user_id=transformed_data.get('primary_user_id')  # New field from JOIN
        )
    
    def _save_records(self, to_create: List[Genius_UserData], to_update: List[Genius_UserData]):
        """Save records to database with comprehensive error handling"""
        created_count = 0
        updated_count = 0
        failed_count = 0
        
        try:
            if to_create:
                Genius_UserData.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
                created_count = len(to_create)
                logger.info(f"Bulk created {created_count} user records")
            
            if to_update:
                # List fields that exist in the model including new primary_user_id
                fields_to_update = [
                    'division', 'title_id', 'manager_user_id', 'first_name',
                    'first_name_alt', 'last_name', 'email', 'personal_email',
                    'birth_date', 'gender_id', 'marital_status_id', 'time_zone_name',
                    'hired_on', 'add_datetime', 'add_user_id', 'start_date',
                    'is_inactive', 'inactive_on', 'inactive_reason_id', 'inactive_reason_other',
                    'primary_user_id'  # New field from JOIN
                ]
                
                Genius_UserData.objects.bulk_update(to_update, fields_to_update, batch_size=BATCH_SIZE)
                updated_count = len(to_update)
                logger.info(f"Bulk updated {updated_count} user records")
                
        except Exception as e:
            error_msg = f"Error during bulk operations: {e}"
            logger.error(error_msg)
            self.stdout.write(self.style.ERROR(error_msg))
            
            # Fallback to individual saves with detailed error tracking
            for record in to_create + to_update:
                try:
                    record.save()
                    if record.pk:  # Was created/updated successfully
                        if record in to_create:
                            created_count += 1
                        else:
                            updated_count += 1
                except Exception as individual_error:
                    failed_count += 1
                    error_msg = f"Error saving record {record.id}: {individual_error}"
                    logger.error(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))
        
        # Log final results
        result_msg = f"Batch complete: {created_count} created, {updated_count} updated, {failed_count} failed"
        logger.info(result_msg)
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(result_msg))
        else:
            self.stdout.write(self.style.SUCCESS(result_msg))