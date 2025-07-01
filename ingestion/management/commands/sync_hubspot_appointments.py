from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, Any
from tqdm import tqdm
from asgiref.sync import sync_to_async

from ingestion.hubspot.hubspot_client import HubspotClient
from ingestion.models.hubspot import Hubspot_Appointment, Hubspot_SyncHistory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync appointments from HubSpot custom object 0-421"

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform a full sync instead of incremental'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Show debug output'
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=0,
            help='Maximum number of pages to process (0 for unlimited)'
        )
        parser.add_argument(
            '--checkpoint',
            type=int,
            default=5,
            help='Save progress to database after every N pages (default 5)'
        )
        parser.add_argument(
            '--lastmodifieddate',
            type=str,
            help='Filter appointments modified after this date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving to database'
        )

    def handle(self, *args, **options):
        if options['debug']:
            logging.getLogger('ingestion.hubspot').setLevel(logging.DEBUG)
        
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        # Run the async sync
        try:
            asyncio.run(self.sync_appointments(options))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Sync failed: {str(e)}'))
            logger.error(f"HubSpot appointments sync failed: {str(e)}")

    async def sync_appointments(self, options):
        """Main sync logic"""
        self.stdout.write('Starting HubSpot appointments sync...')
        
        # Initialize client
        client = HubspotClient()
        
        # Determine last sync time
        last_sync = self._get_last_sync_time(options)
        
        if last_sync:
            self.stdout.write(f'Incremental sync from: {last_sync}')
        else:
            self.stdout.write('Full sync (no previous sync found)')
        
        # Sync appointments
        total_processed = await self._sync_appointments_chunked(client, last_sync, options)
          # Update sync history
        if not self.dry_run and total_processed > 0:
            await self._update_sync_history()
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Sync completed. Processed {total_processed} appointments.')
        )

    def _get_last_sync_time(self, options):
        """Get the last sync time"""
        if options['full']:
            return None
        
        if options['lastmodifieddate']:
            try:
                return datetime.strptime(options['lastmodifieddate'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                self.stdout.write(self.style.WARNING('Invalid date format. Using full sync.'))
                return None
        
        # Get last sync from history - use sync method
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT last_synced_at FROM ingestion_hubspot_synchistory WHERE endpoint = %s",
                    ['appointments']
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
                return None
        except Exception:
            return None

    async def _sync_appointments_chunked(self, client, last_sync, options):
        """Sync appointments using adaptive chunking to handle API limits and errors"""
        # Determine date range for full history
        start_date = last_sync or datetime(2018, 1, 1, tzinfo=timezone.utc)
        end_date = timezone.now()
        self.stdout.write(f"Syncing appointments from {start_date} to {end_date} using adaptive chunked fetch...")
        
        # Use adaptive chunking instead of fixed 30-day chunks
        all_appointments = await self._fetch_appointments_adaptive(client, start_date, end_date)
        
        # Process and save all fetched appointments
        processed_count = await self._process_appointments(all_appointments)
        return processed_count

    async def _process_appointments(self, appointments):
        """Process appointments with improved batch processing"""
        processed_count = 0
        batch_size = 25  # Smaller, manageable batches
        
        if self.dry_run:
            # Dry run - just show what would be processed
            with tqdm(total=len(appointments), desc="Processing appointments (dry run)") as pbar:
                for appointment_data in appointments:
                    appointment_name = appointment_data.get('properties', {}).get('hs_appointment_name', 'N/A')
                    first_name = appointment_data.get('properties', {}).get('first_name', '')
                    last_name = appointment_data.get('properties', {}).get('last_name', '')
                    self.stdout.write(
                        self.style.SUCCESS(f"Would process: {appointment_name} - {first_name} {last_name}")
                    )
                    processed_count += 1
                    pbar.update(1)
        else:
            # Process in batches for better performance
            for i in range(0, len(appointments), batch_size):
                batch = appointments[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                self.stdout.write(f"Processing batch {batch_num} ({len(batch)} appointments)...")
                  # Process batch using bulk save
                try:
                    self.stdout.write(f"📦 Attempting bulk processing for batch {batch_num}...")
                    batch_processed = await self._process_batch_bulk(batch)
                    processed_count += batch_processed
                    self.stdout.write(f"✅ Batch {batch_num}: {batch_processed} appointments processed via BULK operations")
                except Exception as e:
                    logger.error(f"Batch {batch_num} bulk processing failed: {str(e)}")
                    # Fallback to individual processing
                    self.stdout.write(f"⚠️ Batch {batch_num}: Bulk failed, falling back to INDIVIDUAL processing...")
                    batch_processed = await self._process_batch_individual(batch)
                    processed_count += batch_processed
                    self.stdout.write(f"✅ Batch {batch_num}: {batch_processed} appointments processed via INDIVIDUAL operations")
        
        return processed_count

    async def _save_appointment(self, appointment_data):
        """Save a single appointment to the database"""
        appointment_id = appointment_data['id']
        properties = appointment_data.get('properties', {})
        
        # Parse datetime fields
        def parse_datetime(date_str):
            if not date_str:
                return None
            try:
                # HubSpot timestamps are usually in milliseconds
                if date_str.isdigit():
                    timestamp = int(date_str) / 1000
                    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
                else:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return None
        
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None
        
        def parse_time(time_str):
            if not time_str:
                return None
            try:
                return datetime.strptime(time_str, '%H:%M:%S').time()
            except (ValueError, TypeError):
                return None
        
        def parse_boolean(bool_str):
            if bool_str is None or bool_str == '':
                return None
            return str(bool_str).lower() in ['true', '1', 'yes']
        
        def parse_boolean_not_null(bool_str):
            """Parse boolean for NOT NULL fields - returns False instead of None for empty values"""
            if bool_str is None or bool_str == '':
                return False
            return str(bool_str).lower() in ['true', '1', 'yes']
        
        def parse_decimal(decimal_str):
            if not decimal_str:
                return None
            try:
                return float(decimal_str)
            except (ValueError, TypeError):
                return None
        
        def parse_int(int_str):
            if not int_str:
                return None
            try:
                return int(int_str)
            except (ValueError, TypeError):
                return None
        
        # Map HubSpot properties to model fields
        appointment_fields = {
            'id': appointment_id,
            'appointment_id': properties.get('appointment_id'),
            'genius_appointment_id': properties.get('genius_appointment_id'),
            'marketsharp_id': properties.get('marketsharp_id'),
              # HubSpot specific fields
            'hs_appointment_name': properties.get('hs_appointment_name'),
            'hs_appointment_start': parse_datetime(properties.get('hs_appointment_start')),
            'hs_appointment_end': parse_datetime(properties.get('hs_appointment_end')),
            'hs_duration': parse_int(properties.get('hs_duration')),
            'hs_object_id': properties.get('hs_object_id'),
            'hs_createdate': parse_datetime(properties.get('hs_createdate')),
            'hs_lastmodifieddate': parse_datetime(properties.get('hs_lastmodifieddate')),
            'hs_pipeline': properties.get('hs_pipeline'),
            'hs_pipeline_stage': properties.get('hs_pipeline_stage'),
            
            # HubSpot system fields
            'hs_all_accessible_team_ids': properties.get('hs_all_accessible_team_ids'),
            'hs_all_assigned_business_unit_ids': properties.get('hs_all_assigned_business_unit_ids'),
            'hs_all_owner_ids': properties.get('hs_all_owner_ids'),
            'hs_all_team_ids': properties.get('hs_all_team_ids'),
            'hs_created_by_user_id': properties.get('hs_created_by_user_id'),
            'hs_merged_object_ids': properties.get('hs_merged_object_ids'),
            'hs_object_source': properties.get('hs_object_source'),
            'hs_object_source_detail_1': properties.get('hs_object_source_detail_1'),
            'hs_object_source_detail_2': properties.get('hs_object_source_detail_2'),
            'hs_object_source_detail_3': properties.get('hs_object_source_detail_3'),
            'hs_object_source_id': properties.get('hs_object_source_id'),
            'hs_object_source_label': properties.get('hs_object_source_label'),
            'hs_object_source_user_id': properties.get('hs_object_source_user_id'),
            'hs_owning_teams': properties.get('hs_owning_teams'),
            'hs_read_only': parse_boolean(properties.get('hs_read_only')),
            'hs_shared_team_ids': properties.get('hs_shared_team_ids'),
            'hs_shared_user_ids': properties.get('hs_shared_user_ids'),
            'hs_unique_creation_key': properties.get('hs_unique_creation_key'),
            'hs_updated_by_user_id': properties.get('hs_updated_by_user_id'),
            'hs_user_ids_of_all_notification_followers': properties.get('hs_user_ids_of_all_notification_followers'),
            'hs_user_ids_of_all_notification_unfollowers': properties.get('hs_user_ids_of_all_notification_unfollowers'),
            'hs_user_ids_of_all_owners': properties.get('hs_user_ids_of_all_owners'),
            'hs_was_imported': parse_boolean(properties.get('hs_was_imported')),
            
            # Contact information
            'first_name': properties.get('first_name'),
            'last_name': properties.get('last_name'),
            'email': properties.get('email'),
            'phone1': properties.get('phone1'),
            'phone2': properties.get('phone2'),
            
            # Address information
            'address1': properties.get('address1'),
            'address2': properties.get('address2'),
            'city': properties.get('city'),
            'state': properties.get('state'),
            'zip': properties.get('zip'),
            
            # Appointment scheduling
            'date': parse_date(properties.get('date')),
            'time': parse_time(properties.get('time')),
            'duration': parse_int(properties.get('duration')),
            
            # Appointment status
            'appointment_status': properties.get('appointment_status'),
            'appointment_response': properties.get('appointment_response'),
            'is_complete': parse_boolean_not_null(properties.get('is_complete')),
            
            # Services and interests
            'appointment_services': properties.get('appointment_services'),
            'lead_services': properties.get('lead_services'),
            'product_interest_primary': properties.get('product_interest_primary'),
            'product_interest_secondary': properties.get('product_interest_secondary'),
            
            # User and assignment info
            'user_id': properties.get('user_id'),
            'canvasser': properties.get('canvasser'),
            'canvasser_id': properties.get('canvasser_id'),
            'canvasser_email': properties.get('canvasser_email'),
            'hubspot_owner_id': properties.get('hubspot_owner_id'),
            'hubspot_owner_assigneddate': parse_datetime(properties.get('hubspot_owner_assigneddate')),
            'hubspot_team_id': properties.get('hubspot_team_id'),
            
            # Division info
            'division_id': properties.get('division_id'),
            
            # Source tracking
            'primary_source': properties.get('primary_source'),
            'secondary_source': properties.get('secondary_source'),
            'prospect_id': properties.get('prospect_id'),
            'prospect_source_id': properties.get('prospect_source_id'),
            'hscontact_id': properties.get('hscontact_id'),
            
            # Appointment type
            'type_id': properties.get('type_id'),
            'type_id_text': properties.get('type_id_text'),
            'marketsharp_appt_type': properties.get('marketsharp_appt_type'),
            
            # Completion details
            'complete_date': parse_datetime(properties.get('complete_date')),
            'complete_outcome_id': properties.get('complete_outcome_id'),
            'complete_outcome_id_text': properties.get('complete_outcome_id_text'),
            'complete_user_id': properties.get('complete_user_id'),
            
            # Confirmation details
            'confirm_date': parse_datetime(properties.get('confirm_date')),
            'confirm_user_id': properties.get('confirm_user_id'),
            'confirm_with': properties.get('confirm_with'),
            
            # Assignment details
            'assign_date': parse_datetime(properties.get('assign_date')),
            'add_date': parse_datetime(properties.get('add_date')),
            'add_user_id': properties.get('add_user_id'),
            
            # Arrivy integration
            'arrivy_appt_date': parse_datetime(properties.get('arrivy_appt_date')),
            'arrivy_confirm_date': parse_datetime(properties.get('arrivy_confirm_date')),
            'arrivy_confirm_user': properties.get('arrivy_confirm_user'),
            'arrivy_created_by': properties.get('arrivy_created_by'),
            'arrivy_object_id': properties.get('arrivy_object_id'),
            'arrivy_status': properties.get('arrivy_status'),
            'arrivy_user': properties.get('arrivy_user'),
            'arrivy_user_divison_id': properties.get('arrivy_user_divison_id'),
            'arrivy_user_external_id': properties.get('arrivy_user_external_id'),
            'arrivy_username': properties.get('arrivy_username'),
            
            # SalesPro integration
            'salespro_both_homeowners': parse_boolean(properties.get('salespro_both_homeowners')),
            'salespro_deadline': parse_date(properties.get('salespro_deadline')),
            'salespro_deposit_type': properties.get('salespro_deposit_type'),
            'salespro_fileurl_contract': properties.get('salespro_fileurl_contract'),
            'salespro_fileurl_estimate': properties.get('salespro_fileurl_estimate'),
            'salespro_financing': properties.get('salespro_financing'),
            'salespro_job_size': properties.get('salespro_job_size'),
            'salespro_job_type': properties.get('salespro_job_type'),
            'salespro_last_price_offered': parse_decimal(properties.get('salespro_last_price_offered')),
            'salespro_notes': properties.get('salespro_notes'),
            'salespro_one_year_price': parse_decimal(properties.get('salespro_one_year_price')),
            'salespro_preferred_payment': properties.get('salespro_preferred_payment'),
            'salespro_requested_start': parse_date(properties.get('salespro_requested_start')),
            'salespro_result': properties.get('salespro_result'),
            'salespro_result_notes': properties.get('salespro_result_notes'),
            'salespro_result_reason_demo': properties.get('salespro_result_reason_demo'),
            'salespro_result_reason_no_demo': properties.get('salespro_result_reason_no_demo'),
            
            # Additional fields
            'notes': properties.get('notes'),
            'log': properties.get('log'),
            'title': properties.get('title'),
            'marketing_task_id': properties.get('marketing_task_id'),
            'leap_estimate_id': properties.get('leap_estimate_id'),
            'spouses_present': parse_boolean(properties.get('spouses_present')),
            'year_built': parse_int(properties.get('year_built')),
            'error_details': properties.get('error_details'),
            'tester_test': properties.get('tester_test'),
        }
        
        # Save to database using sync_to_async
        await self._save_appointment_sync(appointment_id, appointment_fields)

    @sync_to_async
    def _save_appointment_sync(self, appointment_id, appointment_fields):
        """Synchronous database save wrapped for async"""
        with transaction.atomic():
            appointment, created = Hubspot_Appointment.objects.update_or_create(
                id=appointment_id,
                defaults=appointment_fields
            )
            
            if created:
                logger.info(f"Created new appointment: {appointment_id}")
            else:
                logger.info(f"Updated appointment: {appointment_id}")

    @sync_to_async  
    def _update_sync_history(self):
        """Update the sync history record"""
        sync_history, created = Hubspot_SyncHistory.objects.update_or_create(
            endpoint='appointments',
            defaults={'last_synced_at': timezone.now()}
        )
        
        if created:
            logger.info("Created new sync history record for appointments")
        else:
            logger.info("Updated sync history for appointments")
    
    async def _process_batch_bulk(self, batch):
        """Process a batch using bulk database operations"""
        appointment_data_list = []
        appointment_ids = []
        
        # Prepare data for all appointments in batch
        for appointment_data in batch:
            try:
                appointment_id = appointment_data['id']
                appointment_ids.append(appointment_id)
                fields = self._prepare_appointment_fields(appointment_id, appointment_data)
                appointment_data_list.append(fields)
            except Exception as e:
                logger.error(f"Failed to prepare appointment {appointment_data.get('id', 'unknown')}: {str(e)}")
                continue
        
        if not appointment_data_list:
            return 0
        
        # Bulk save to database
        return await self._bulk_save_appointments(appointment_data_list, appointment_ids)
    
    async def _process_batch_individual(self, batch):
        """Fallback: process batch with individual saves"""
        processed_count = 0
        
        with tqdm(total=len(batch), desc="Individual processing") as pbar:
            for appointment_data in batch:
                try:
                    await self._save_appointment(appointment_data)
                    processed_count += 1
                except Exception as e:
                    appointment_id = appointment_data.get('id', 'unknown')
                    logger.error(f"Failed to process appointment {appointment_id}: {str(e)}")
                finally:
                    pbar.update(1)        
        return processed_count
    
    def _prepare_appointment_fields(self, appointment_id, appointment_data):
        """Prepare appointment fields for bulk operations"""
        properties = appointment_data.get('properties', {})
        
        # Parse datetime fields
        def parse_datetime(date_str):
            if not date_str:
                return None
            try:
                if date_str.isdigit():
                    timestamp = int(date_str) / 1000
                    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
                else:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return None
        
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None
        
        def parse_time(time_str):
            if not time_str:
                return None
            try:
                return datetime.strptime(time_str, '%H:%M:%S').time()
            except (ValueError, TypeError):
                return None
        
        def parse_boolean(bool_str):
            if bool_str is None or bool_str == '':
                return None
            return str(bool_str).lower() in ['true', '1', 'yes']
        
        def parse_boolean_not_null(bool_str):
            """Parse boolean for NOT NULL fields - returns False instead of None for empty values"""
            if bool_str is None or bool_str == '':
                return False
            return str(bool_str).lower() in ['true', '1', 'yes']
        
        def parse_decimal(decimal_str):
            if not decimal_str:
                return None
            try:
                return float(decimal_str)
            except (ValueError, TypeError):
                return None
        
        def parse_int(int_str):
            if not int_str:
                return None
            try:
                return int(int_str)
            except (ValueError, TypeError):
                return None
          # Return the same field mapping used in the individual save method
        return {
            'id': appointment_id,
            'appointment_id': properties.get('appointment_id'),
            'genius_appointment_id': properties.get('genius_appointment_id'),
            'marketsharp_id': properties.get('marketsharp_id'),
            
            # HubSpot specific fields
            'hs_appointment_name': properties.get('hs_appointment_name'),
            'hs_appointment_start': parse_datetime(properties.get('hs_appointment_start')),
            'hs_appointment_end': parse_datetime(properties.get('hs_appointment_end')),
            'hs_duration': parse_int(properties.get('hs_duration')),
            'hs_object_id': properties.get('hs_object_id'),
            'hs_createdate': parse_datetime(properties.get('hs_createdate')),
            'hs_lastmodifieddate': parse_datetime(properties.get('hs_lastmodifieddate')),
            'hs_pipeline': properties.get('hs_pipeline'),
            'hs_pipeline_stage': properties.get('hs_pipeline_stage'),
            
            # HubSpot system fields
            'hs_all_accessible_team_ids': properties.get('hs_all_accessible_team_ids'),
            'hs_all_assigned_business_unit_ids': properties.get('hs_all_assigned_business_unit_ids'),
            'hs_all_owner_ids': properties.get('hs_all_owner_ids'),
            'hs_all_team_ids': properties.get('hs_all_team_ids'),
            'hs_created_by_user_id': properties.get('hs_created_by_user_id'),
            'hs_merged_object_ids': properties.get('hs_merged_object_ids'),
            'hs_object_source': properties.get('hs_object_source'),
            'hs_object_source_detail_1': properties.get('hs_object_source_detail_1'),
            'hs_object_source_detail_2': properties.get('hs_object_source_detail_2'),
            'hs_object_source_detail_3': properties.get('hs_object_source_detail_3'),
            'hs_object_source_id': properties.get('hs_object_source_id'),
            'hs_object_source_label': properties.get('hs_object_source_label'),
            'hs_object_source_user_id': properties.get('hs_object_source_user_id'),
            'hs_owning_teams': properties.get('hs_owning_teams'),
            'hs_read_only': parse_boolean(properties.get('hs_read_only')),
            'hs_shared_team_ids': properties.get('hs_shared_team_ids'),
            'hs_shared_user_ids': properties.get('hs_shared_user_ids'),
            'hs_unique_creation_key': properties.get('hs_unique_creation_key'),
            'hs_updated_by_user_id': properties.get('hs_updated_by_user_id'),
            'hs_user_ids_of_all_notification_followers': properties.get('hs_user_ids_of_all_notification_followers'),
            'hs_user_ids_of_all_notification_unfollowers': properties.get('hs_user_ids_of_all_notification_unfollowers'),
            'hs_user_ids_of_all_owners': properties.get('hs_user_ids_of_all_owners'),
            'hs_was_imported': parse_boolean(properties.get('hs_was_imported')),
            
            # Contact information
            'first_name': properties.get('first_name'),
            'last_name': properties.get('last_name'),
            'email': properties.get('email'),
            'phone1': properties.get('phone1'),
            'phone2': properties.get('phone2'),
            
            # Address information
            'address1': properties.get('address1'),
            'address2': properties.get('address2'),
            'city': properties.get('city'),
            'state': properties.get('state'),
            'zip': properties.get('zip'),
            
            # Appointment scheduling
            'date': parse_date(properties.get('date')),
            'time': parse_time(properties.get('time')),
            'duration': parse_int(properties.get('duration')),
            
            # Appointment status
            'appointment_status': properties.get('appointment_status'),
            'appointment_response': properties.get('appointment_response'),
            'is_complete': parse_boolean_not_null(properties.get('is_complete')),
            
            # Services and interests
            'appointment_services': properties.get('appointment_services'),
            'lead_services': properties.get('lead_services'),
            'product_interest_primary': properties.get('product_interest_primary'),
            'product_interest_secondary': properties.get('product_interest_secondary'),
            
            # User and assignment info
            'user_id': properties.get('user_id'),
            'canvasser': properties.get('canvasser'),
            'canvasser_id': properties.get('canvasser_id'),
            'canvasser_email': properties.get('canvasser_email'),
            'hubspot_owner_id': properties.get('hubspot_owner_id'),
            'hubspot_owner_assigneddate': parse_datetime(properties.get('hubspot_owner_assigneddate')),
            'hubspot_team_id': properties.get('hubspot_team_id'),
            
            # Division info
            'division_id': properties.get('division_id'),
            
            # Source tracking
            'primary_source': properties.get('primary_source'),
            'secondary_source': properties.get('secondary_source'),
            'prospect_id': properties.get('prospect_id'),
            'prospect_source_id': properties.get('prospect_source_id'),
            'hscontact_id': properties.get('hscontact_id'),
            
            # Appointment type
            'type_id': properties.get('type_id'),
            'type_id_text': properties.get('type_id_text'),
            'marketsharp_appt_type': properties.get('marketsharp_appt_type'),
            
            # Completion details
            'complete_date': parse_datetime(properties.get('complete_date')),
            'complete_outcome_id': properties.get('complete_outcome_id'),
            'complete_outcome_id_text': properties.get('complete_outcome_id_text'),
            'complete_user_id': properties.get('complete_user_id'),
            
            # Confirmation details
            'confirm_date': parse_datetime(properties.get('confirm_date')),
            'confirm_user_id': properties.get('confirm_user_id'),
            'confirm_with': properties.get('confirm_with'),
            
            # Assignment details
            'assign_date': parse_datetime(properties.get('assign_date')),
            'add_date': parse_datetime(properties.get('add_date')),
            'add_user_id': properties.get('add_user_id'),
            
            # Arrivy integration
            'arrivy_appt_date': parse_datetime(properties.get('arrivy_appt_date')),
            'arrivy_confirm_date': parse_datetime(properties.get('arrivy_confirm_date')),
            'arrivy_confirm_user': properties.get('arrivy_confirm_user'),
            'arrivy_created_by': properties.get('arrivy_created_by'),
            'arrivy_object_id': properties.get('arrivy_object_id'),
            'arrivy_status': properties.get('arrivy_status'),
            'arrivy_user': properties.get('arrivy_user'),
            'arrivy_user_divison_id': properties.get('arrivy_user_divison_id'),
            'arrivy_user_external_id': properties.get('arrivy_user_external_id'),
            'arrivy_username': properties.get('arrivy_username'),
            
            # SalesPro integration
            'salespro_both_homeowners': parse_boolean(properties.get('salespro_both_homeowners')),
            'salespro_deadline': parse_date(properties.get('salespro_deadline')),
            'salespro_deposit_type': properties.get('salespro_deposit_type'),
            'salespro_fileurl_contract': properties.get('salespro_fileurl_contract'),
            'salespro_fileurl_estimate': properties.get('salespro_fileurl_estimate'),
            'salespro_financing': properties.get('salespro_financing'),
            'salespro_job_size': properties.get('salespro_job_size'),
            'salespro_job_type': properties.get('salespro_job_type'),
            'salespro_last_price_offered': parse_decimal(properties.get('salespro_last_price_offered')),
            'salespro_notes': properties.get('salespro_notes'),
            'salespro_one_year_price': parse_decimal(properties.get('salespro_one_year_price')),
            'salespro_preferred_payment': properties.get('salespro_preferred_payment'),
            'salespro_requested_start': parse_date(properties.get('salespro_requested_start')),
            'salespro_result': properties.get('salespro_result'),
            'salespro_result_notes': properties.get('salespro_result_notes'),
            'salespro_result_reason_demo': properties.get('salespro_result_reason_demo'),
            'salespro_result_reason_no_demo': properties.get('salespro_result_reason_no_demo'),
            
            # Additional fields
            'notes': properties.get('notes'),
            'log': properties.get('log'),
            'title': properties.get('title'),
            'marketing_task_id': properties.get('marketing_task_id'),
            'leap_estimate_id': properties.get('leap_estimate_id'),
            'spouses_present': parse_boolean(properties.get('spouses_present')),
            'year_built': parse_int(properties.get('year_built')),
            'error_details': properties.get('error_details'),
            'tester_test': properties.get('tester_test'),
        }
    
    @sync_to_async
    def _bulk_save_appointments(self, appointment_fields_list, appointment_ids):
        """Bulk save appointments to database"""
        with transaction.atomic():
            # Check existing appointments
            existing_ids = set(
                Hubspot_Appointment.objects.filter(
                    id__in=appointment_ids
                ).values_list('id', flat=True)
            )
            
            # Split into create/update
            to_create = []
            to_update = []
            
            for fields in appointment_fields_list:
                if fields['id'] in existing_ids:
                    to_update.append(Hubspot_Appointment(**fields))
                else:
                    to_create.append(Hubspot_Appointment(**fields))
            
            created_count = 0
            updated_count = 0
            
            # Bulk create new appointments
            if to_create:
                Hubspot_Appointment.objects.bulk_create(to_create, ignore_conflicts=True)
                created_count = len(to_create)
                logger.info(f"Bulk created {created_count} appointments")
            
            # Bulk update existing appointments (simplified field list)
            if to_update:
                key_fields = [
                    'hs_appointment_name', 'hs_appointment_start', 'hs_appointment_end',
                    'hs_lastmodifieddate', 'first_name', 'last_name', 'email',
                    'appointment_status', 'is_complete', 'hubspot_owner_id'
                ]
                Hubspot_Appointment.objects.bulk_update(to_update, key_fields)
                updated_count = len(to_update)
                logger.info(f"Bulk updated {updated_count} appointments")
            
            return created_count + updated_count

    async def _fetch_appointments_adaptive(self, client, start_date, end_date, max_results_per_chunk=8000):
        """
        Adaptively fetch appointments by breaking down time ranges when errors occur or too many results are returned.
        
        Args:
            client: HubspotClient instance
            start_date: Start datetime for the range
            end_date: End datetime for the range
            max_results_per_chunk: Maximum number of results per chunk before subdividing
        
        Returns:
            List of all appointments fetched
        """
        all_appointments = []
        
        # Create initial time ranges to process
        pending_ranges = [(start_date, end_date)]
        
        while pending_ranges:
            current_start, current_end = pending_ranges.pop(0)
            
            # Calculate time span
            time_span = current_end - current_start
            self.stdout.write(f"Processing range: {current_start} to {current_end} (span: {time_span})")
            
            try:
                # Try to fetch appointments for this time range
                chunk_appointments = await self._fetch_single_chunk(client, current_start, current_end)
                
                # Check if we got too many results (approaching API limits)
                if len(chunk_appointments) >= max_results_per_chunk:
                    self.stdout.write(f"⚠️ Large result set ({len(chunk_appointments)} appointments), subdividing range...")
                    
                    # Subdivide this range into smaller chunks
                    sub_ranges = self._subdivide_time_range(current_start, current_end, 10)
                    pending_ranges.extend(sub_ranges)
                    continue
                
                # Success - add these appointments to our collection
                all_appointments.extend(chunk_appointments)
                self.stdout.write(f"✅ Successfully fetched {len(chunk_appointments)} appointments for range")
                
            except Exception as e:
                error_msg = str(e)
                self.stdout.write(f"❌ Error fetching range {current_start} to {current_end}: {error_msg}")
                
                # Check if the time range is too small to subdivide further
                if time_span.total_seconds() < 3600:  # Less than 1 hour
                    self.stdout.write(f"⚠️ Cannot subdivide further (range < 1 hour), skipping...")
                    logger.error(f"Skipping problematic range {current_start} to {current_end}: {error_msg}")
                    continue
                
                # Subdivide this range into smaller chunks
                self.stdout.write(f"🔄 Subdividing problematic range into smaller chunks...")
                sub_ranges = self._subdivide_time_range(current_start, current_end, 10)
                pending_ranges.extend(sub_ranges)
        
        self.stdout.write(f"✅ Adaptive fetch complete: {len(all_appointments)} total appointments")
        return all_appointments
    
    async def _fetch_single_chunk(self, client, start_date, end_date):
        """
        Fetch a single chunk of appointments for the given date range.
        
        Args:
            client: HubspotClient instance
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            List of appointments for this range
        """
        # Use the client's internal method to fetch appointments for a specific date range
        # without additional chunking
        return await client._get_appointments_for_date_range(start_date, end_date)
    
    def _subdivide_time_range(self, start_date, end_date, num_subdivisions=10):
        """
        Subdivide a time range into smaller equal chunks.
        
        Args:
            start_date: Start datetime
            end_date: End datetime
            num_subdivisions: Number of equal subdivisions to create
            
        Returns:
            List of (start, end) tuples for each subdivision
        """
        total_seconds = (end_date - start_date).total_seconds()
        chunk_seconds = total_seconds / num_subdivisions
        
        subdivisions = []
        current_start = start_date
        
        for i in range(num_subdivisions):
            if i == num_subdivisions - 1:
                # Last chunk - use the original end_date to avoid rounding errors
                current_end = end_date
            else:
                current_end = current_start + timedelta(seconds=chunk_seconds)
            
            subdivisions.append((current_start, current_end))
            current_start = current_end
        
        self.stdout.write(f"📋 Created {len(subdivisions)} subdivisions of {timedelta(seconds=chunk_seconds)} each")
        return subdivisions
