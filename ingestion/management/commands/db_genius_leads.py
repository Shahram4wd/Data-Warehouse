import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from ingestion.models import Genius_Lead, Genius_Division
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import datetime, timezone as dt_timezone
import logging

# Optimize batch sizes for better performance
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 2000))  # Increased from 500
MYSQL_FETCH_SIZE = int(os.getenv("MYSQL_FETCH_SIZE", 5000))  # Smaller chunks for better progress visibility

class Command(BaseCommand):
    help = "Download leads directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="lead",
            help="The name of the table to download data from. Defaults to 'lead'."
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of records to process. Useful for testing."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        limit = options["limit"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            divisions = self._preload_divisions()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, divisions, limit)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_divisions(self):
        """Preload divisions for lookup."""
        return {division.id: division for division in Genius_Division.objects.all()}
    
    def _process_all_records(self, cursor, table_name, divisions, limit=None):
        """Process all records in optimized batches with real progress tracking."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        total_records = cursor.fetchone()[0]
        
        # Apply limit if specified
        if limit is not None:
            total_records = min(total_records, limit)
            self.stdout.write(self.style.WARNING(f"Limiting processing to {total_records} records."))
        
        self.stdout.write(self.style.SUCCESS(f"Total records to process from table '{table_name}': {total_records}"))
        
        # Process records in chunks to show real progress
        processed = 0
        with tqdm(total=total_records, desc="Processing records", unit="records") as pbar:
            while processed < total_records:
                # Calculate chunk size for this iteration
                remaining = total_records - processed
                chunk_size = min(MYSQL_FETCH_SIZE, remaining)
                
                # Fetch next chunk using LIMIT and OFFSET
                cursor.execute(f"""
                    SELECT lead_id, contact, division, first_name, last_name, address1, address2, city, state, zip,
                           cdyne_county, is_valid_address, email, phone1, type1, phone2, type2, phone3, type3, phone4, type4,
                           source, source_notes, sourced_on, job_type, rating, year_built, is_year_built_verified,
                           is_zillow, is_express_consent, express_consent_set_by, express_consent_set_on, express_consent_source,
                           express_consent_upload_file_id, is_express_consent_being_reviewed, express_consent_being_reviewed_by,
                           notes, status, substatus, substatus_reason, alternate_id, added_by, added_on, viewed_on,
                           is_estimate_set, estimate_set_by, estimate_set_on, dead_on, dead_by, dead_note,
                           is_credit_request, credit_request_by, credit_request_on, credit_request_reason, credit_request_status,
                           credit_request_update_on, credit_request_update_by, credit_request_note, lead_cost, import_source,
                           call_screen_viewed_on, call_screen_viewed_by, copied_to_id, copied_to_on, copied_from_id, copied_from_on,
                           cwp_client, cwp_referral, rc_paid_to, rc_paid_on, with_dm, voicemail_file, agent_id, agent_name,
                           invalid_address, is_valid_email, is_high_potential, is_mobile_lead, is_dnc, is_dummy,
                           lead_central_estimate_date, do_not_call_before, is_estimate_confirmed, estimate_confirmed_by, estimate_confirmed_on,
                           added_by_latitude, added_by_longitude, is_carpentry_followup, carpentry_followup_notes,
                           marketing_source, prospect_id, added_by_supervisor, salesrabbit_lead_id, third_party_source_id
                    FROM `{table_name}`
                    ORDER BY lead_id
                    LIMIT {chunk_size} OFFSET {processed}
                """)
                
                rows = cursor.fetchall()
                if not rows:
                    break
                
                # Process this chunk
                self._process_optimized_batch(rows, divisions)
                processed += len(rows)
                pbar.update(len(rows))
                
                # Update progress description with current stats
                pbar.set_postfix({
                    'processed': f"{processed:,}",
                    'remaining': f"{total_records - processed:,}"
                })
    
    def _process_optimized_batch(self, rows, divisions):
        """Optimized batch processing with fewer database queries."""
        if not rows:
            return
            
        # Extract all lead_ids from this batch
        lead_ids = [row[0] for row in rows]
        
        # Single query to get all existing records
        existing_records = {
            record.lead_id: record 
            for record in Genius_Lead.objects.filter(lead_id__in=lead_ids).only('lead_id')
        }
        
        to_create = []
        to_update = []
        
        # Process records in memory - much faster than individual processing
        for row in rows:
            try:
                lead_id = row[0]
                processed_data = self._process_row_data(row, divisions)
                
                if lead_id in existing_records:
                    # Update existing record
                    record = existing_records[lead_id]
                    self._update_record_fields(record, processed_data)
                    to_update.append(record)
                else:
                    # Create new record
                    record = Genius_Lead(**processed_data)
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))
        
        # Single bulk operation for all records
        self._bulk_save_optimized(to_create, to_update)
    
    def _process_row_data(self, row, divisions):
        """Process a single row into a data dictionary."""
        # Extract fields from row (matching the SELECT statement order)
        (
            lead_id, contact, division_id, first_name, last_name, address1, address2, city, state, zip,
            cdyne_county, is_valid_address, email, phone1, type1, phone2, type2, phone3, type3, phone4, type4,
            source, source_notes, sourced_on, job_type, rating, year_built, is_year_built_verified,
            is_zillow, is_express_consent, express_consent_set_by, express_consent_set_on, express_consent_source,
            express_consent_upload_file_id, is_express_consent_being_reviewed, express_consent_being_reviewed_by,
            notes, status, substatus, substatus_reason, alternate_id, added_by, added_on, viewed_on,
            is_estimate_set, estimate_set_by, estimate_set_on, dead_on, dead_by, dead_note,
            is_credit_request, credit_request_by, credit_request_on, credit_request_reason, credit_request_status,
            credit_request_update_on, credit_request_update_by, credit_request_note, lead_cost, import_source,
            call_screen_viewed_on, call_screen_viewed_by, copied_to_id, copied_to_on, copied_from_id, copied_from_on,
            cwp_client, cwp_referral, rc_paid_to, rc_paid_on, with_dm, voicemail_file, agent_id, agent_name,
            invalid_address, is_valid_email, is_high_potential, is_mobile_lead, is_dnc, is_dummy,
            lead_central_estimate_date, do_not_call_before, is_estimate_confirmed, estimate_confirmed_by, estimate_confirmed_on,
            added_by_latitude, added_by_longitude, is_carpentry_followup, carpentry_followup_notes,
            marketing_source, prospect_id, added_by_supervisor, salesrabbit_lead_id, third_party_source_id
        ) = row
        
        # Get division (single lookup)
        division = divisions.get(division_id)
        
        # Batch process datetime fields
        datetime_fields = {
            'sourced_on': sourced_on,
            'express_consent_set_on': express_consent_set_on,
            'added_on': added_on,
            'viewed_on': viewed_on,
            'estimate_set_on': estimate_set_on,
            'dead_on': dead_on,
            'credit_request_on': credit_request_on,
            'credit_request_update_on': credit_request_update_on,
            'call_screen_viewed_on': call_screen_viewed_on,
            'copied_to_on': copied_to_on,
            'copied_from_on': copied_from_on,
            'rc_paid_on': rc_paid_on,
            'lead_central_estimate_date': lead_central_estimate_date,
            'do_not_call_before': do_not_call_before,
            'estimate_confirmed_on': estimate_confirmed_on,
        }
        
        # Process datetime fields in batch
        for field_name, value in datetime_fields.items():
            datetime_fields[field_name] = self._parse_datetime(value)
        
        # Return complete data dictionary
        return {
            'lead_id': lead_id,
            'contact': contact,
            'division': division,
            'first_name': first_name,
            'last_name': last_name,
            'address1': address1,
            'address2': address2,
            'city': city,
            'state': state,
            'zip': zip,
            'cdyne_county': cdyne_county,
            'is_valid_address': is_valid_address,
            'email': email,
            'phone1': phone1,
            'type1': type1,
            'phone2': phone2,
            'type2': type2,
            'phone3': phone3,
            'type3': type3,
            'phone4': phone4,
            'type4': type4,
            'source': source,
            'source_notes': source_notes,
            'job_type': job_type,
            'rating': rating,
            'year_built': year_built,
            'is_year_built_verified': is_year_built_verified,
            'is_zillow': is_zillow,
            'is_express_consent': is_express_consent,
            'express_consent_set_by': express_consent_set_by,
            'express_consent_source': express_consent_source,
            'express_consent_upload_file_id': express_consent_upload_file_id,
            'is_express_consent_being_reviewed': is_express_consent_being_reviewed,
            'express_consent_being_reviewed_by': express_consent_being_reviewed_by,
            'notes': notes,
            'status': status,
            'substatus': substatus,
            'substatus_reason': substatus_reason,
            'alternate_id': alternate_id,
            'added_by': added_by,
            'viewed_on': datetime_fields['viewed_on'],
            'is_estimate_set': is_estimate_set,
            'estimate_set_by': estimate_set_by,
            'dead_on': datetime_fields['dead_on'],
            'dead_by': dead_by,
            'dead_note': dead_note,
            'is_credit_request': is_credit_request,
            'credit_request_by': credit_request_by,
            'credit_request_reason': credit_request_reason,
            'credit_request_status': credit_request_status,
            'credit_request_update_by': credit_request_update_by,
            'credit_request_note': credit_request_note,
            'lead_cost': lead_cost,
            'import_source': import_source,
            'call_screen_viewed_by': call_screen_viewed_by,
            'copied_to_id': copied_to_id,
            'copied_from_id': copied_from_id,
            'cwp_client': cwp_client,
            'cwp_referral': cwp_referral,
            'rc_paid_to': rc_paid_to,
            'with_dm': with_dm,
            'voicemail_file': voicemail_file,
            'agent_id': agent_id,
            'agent_name': agent_name,
            'invalid_address': invalid_address,
            'is_valid_email': is_valid_email,
            'is_high_potential': is_high_potential,
            'is_mobile_lead': is_mobile_lead,
            'is_dnc': is_dnc,
            'is_dummy': is_dummy,
            'is_estimate_confirmed': is_estimate_confirmed,
            'estimate_confirmed_by': estimate_confirmed_by,
            'added_by_latitude': added_by_latitude,
            'added_by_longitude': added_by_longitude,
            'is_carpentry_followup': is_carpentry_followup,
            'carpentry_followup_notes': carpentry_followup_notes,
            'marketing_source': marketing_source,
            'prospect_id': prospect_id,
            'added_by_supervisor': added_by_supervisor,
            'salesrabbit_lead_id': salesrabbit_lead_id,
            'third_party_source_id': third_party_source_id,
            **datetime_fields  # Add all datetime fields
        }
    
    def _update_record_fields(self, record, data):
        """Update record fields from data dictionary."""
        for field, value in data.items():
            if field != 'lead_id':  # Don't update the primary key
                setattr(record, field, value)
    
    def _bulk_save_optimized(self, to_create, to_update):
        """Optimized bulk save with transaction and better error handling."""
        if not to_create and not to_update:
            return
            
        try:
            with transaction.atomic():
                if to_create:
                    Genius_Lead.objects.bulk_create(to_create, batch_size=BATCH_SIZE, ignore_conflicts=True)
                
                if to_update:
                    # Get all field names dynamically for bulk_update
                    update_fields = [f.name for f in Genius_Lead._meta.fields if f.name != 'lead_id']
                    Genius_Lead.objects.bulk_update(to_update, update_fields, batch_size=BATCH_SIZE)
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            # Fallback to individual saves only if needed
            self._fallback_individual_saves(to_create + to_update)
    
    def _fallback_individual_saves(self, records):
        """Fallback to individual saves when bulk operations fail."""
        for record in records:
            try:
                record.save()
            except Exception as e:
                lead_id = getattr(record, 'lead_id', 'unknown')
                self.stdout.write(self.style.ERROR(f"Error saving record {lead_id}: {e}"))
    
    def _parse_datetime(self, value):
        """Helper function to safely parse and make datetime timezone-aware."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value
        
        return value
