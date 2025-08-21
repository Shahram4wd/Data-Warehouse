import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_Job, Genius_Prospect, Genius_Division, Genius_Service
from ingestion.models.common import SyncHistory
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time
from typing import Optional

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download jobs directly from the database and update the local database."
    
    def add_arguments(self, parser):
        # Standard CRM sync flags according to sync_crm_guide.md
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force-overwrite',
            action='store_true', 
            help='Completely replace existing records'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging'
        )
        
        # Genius-specific arguments (backward compatibility)
        parser.add_argument(
            '--start-date',
            type=str,
            help='(DEPRECATED) Use --since instead. Start date for sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            "--table",
            type=str,
            default="job",
            help="The name of the table to download data from. Defaults to 'job'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            prospects = self._preload_prospects()
            divisions = self._preload_divisions()
            services = self._preload_services()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, prospects, divisions, services)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_prospects(self):
        """Preload prospects for lookup."""
        return {prospect.id: prospect for prospect in Genius_Prospect.objects.all()}
    
    def _preload_divisions(self):
        """Preload divisions for lookup."""
        return {division.id: division for division in Genius_Division.objects.all()}
    
    def _preload_services(self):
        """Preload services for lookup."""
        return {service.id: service for service in Genius_Service.objects.all()}
    
    def _process_all_records(self, cursor, table_name, prospects, divisions, services):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset, prospects, divisions, services)
    
    def _process_batch_at_offset(self, cursor, table_name, offset, prospects, divisions, services):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records - selecting key fields due to large number of columns
        cursor.execute(f"""
            SELECT id, client_cid, prospect_id, division_id, user_id, production_user_id,
                   project_coordinator_user_id, production_month, subcontractor_id,
                   subcontractor_status_id, subcontractor_confirmed, status, is_in_progress,
                   ready_status, prep_status_id, prep_status_set_date, prep_status_is_reset,
                   prep_status_notes, prep_issue_id, service_id, is_lead_pb, contract_number,
                   contract_date, contract_amount, contract_amount_difference, contract_hours,
                   contract_file_id, job_value, deposit_amount, deposit_type_id, is_financing,
                   sales_tax_rate, is_sales_tax_exempt, commission_payout, accrued_commission_payout,
                   sold_user_id, sold_date, start_request_date, deadline_date, ready_date,
                   jsa_sent, start_date, end_date, add_user_id, add_date, cancel_date,
                   cancel_user_id, cancel_reason_id, is_refund, refund_date, refund_user_id,
                   finish_date, is_earned_not_paid, materials_arrival_date, measure_date,
                   measure_time, measure_user_id, time_format, materials_estimated_arrival_date,
                   materials_ordered, price_level, price_level_goal, price_level_commission,
                   price_level_commission_reduction, is_reviewed, reviewed_by, pp_id_updated,
                   hoa, hoa_approved, install_date, install_time, install_time_format,
                   updated_at
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows, prospects, divisions, services)
    
    def _process_batch(self, rows, prospects, divisions, services):
        """Process a batch of job records."""
        to_create = []
        to_update = []
        existing_records = Genius_Job.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                (id, client_cid, prospect_id, division_id, user_id, production_user_id,
                 project_coordinator_user_id, production_month, subcontractor_id,
                 subcontractor_status_id, subcontractor_confirmed, status, is_in_progress,
                 ready_status, prep_status_id, prep_status_set_date, prep_status_is_reset,
                 prep_status_notes, prep_issue_id, service_id, is_lead_pb, contract_number,
                 contract_date, contract_amount, contract_amount_difference, contract_hours,
                 contract_file_id, job_value, deposit_amount, deposit_type_id, is_financing,
                 sales_tax_rate, is_sales_tax_exempt, commission_payout, accrued_commission_payout,
                 sold_user_id, sold_date, start_request_date, deadline_date, ready_date,
                 jsa_sent, start_date, end_date, add_user_id, add_date, cancel_date,
                 cancel_user_id, cancel_reason_id, is_refund, refund_date, refund_user_id,
                 finish_date, is_earned_not_paid, materials_arrival_date, measure_date,
                 measure_time, measure_user_id, time_format, materials_estimated_arrival_date,
                 materials_ordered, price_level, price_level_goal, price_level_commission,
                 price_level_commission_reduction, is_reviewed, reviewed_by, pp_id_updated,
                 hoa, hoa_approved, install_date, install_time, install_time_format,
                 updated_at) = row

                # Get foreign key objects
                prospect = prospects.get(prospect_id)
                division = divisions.get(division_id)
                service = services.get(service_id)
                
                if not prospect:
                    self.stdout.write(self.style.WARNING(f"Prospect {prospect_id} not found for job {id}"))
                    continue
                if not division:
                    self.stdout.write(self.style.WARNING(f"Division {division_id} not found for job {id}"))
                    continue
                if not service:
                    self.stdout.write(self.style.WARNING(f"Service {service_id} not found for job {id}"))
                    continue

                # Convert date fields
                date_fields = ['contract_date', 'sold_date', 'start_request_date', 'deadline_date',
                              'ready_date', 'start_date', 'end_date', 'cancel_date', 'refund_date',
                              'finish_date', 'materials_arrival_date', 'measure_date',
                              'materials_estimated_arrival_date', 'install_date']
                
                for field_name in date_fields:
                    field_value = locals()[field_name]
                    if field_value and isinstance(field_value, datetime):
                        locals()[field_name] = field_value.date()

                # Convert datetime fields
                datetime_fields = ['prep_status_set_date', 'add_date', 'materials_ordered']
                for field_name in datetime_fields:
                    field_value = locals()[field_name]
                    if field_value:
                        locals()[field_name] = timezone.make_aware(field_value) if timezone.is_naive(field_value) else field_value

                # Convert time fields
                if measure_time and isinstance(measure_time, str):
                    try:
                        measure_time = datetime.strptime(measure_time, '%H:%M:%S').time()
                    except ValueError:
                        measure_time = None
                if install_time and isinstance(install_time, str):
                    try:
                        install_time = datetime.strptime(install_time, '%H:%M:%S').time()
                    except ValueError:
                        install_time = None

                # Convert decimal fields
                decimal_fields = {
                    'contract_amount': Decimal('0.00'),
                    'job_value': Decimal('0.00'),
                    'deposit_amount': Decimal('0.00'),
                    'sales_tax_rate': Decimal('0.00000'),
                    'commission_payout': Decimal('0.00'),
                    'accrued_commission_payout': Decimal('0.00'),
                    'price_level_commission': None
                }
                
                for field_name, default_value in decimal_fields.items():
                    field_value = locals()[field_name]
                    if field_value is not None:
                        locals()[field_name] = Decimal(str(field_value))
                    elif default_value is not None:
                        locals()[field_name] = default_value

                # Convert integer fields with defaults
                int_fields = {
                    'subcontractor_confirmed': 0,
                    'status': 10,
                    'is_in_progress': 0,
                    'prep_status_is_reset': 0,
                    'is_lead_pb': 0,
                    'contract_hours': 0,
                    'is_financing': 0,
                    'is_sales_tax_exempt': 0,
                    'is_refund': 0,
                    'is_earned_not_paid': 0,
                    'is_reviewed': 0,
                    'pp_id_updated': 0
                }
                
                for field_name, default_value in int_fields.items():
                    field_value = locals()[field_name]
                    locals()[field_name] = int(field_value) if field_value is not None else default_value

                if id in existing_records:
                    # Update existing record
                    record_instance = existing_records[id]
                    self._update_job_record(record_instance, locals())
                    to_update.append(record_instance)
                else:
                    # Create new record
                    job_data = self._prepare_job_data(locals())
                    to_create.append(Genius_Job(**job_data))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to process record {id}: {e}"))
                continue

        # Bulk create and update
        if to_create:
            Genius_Job.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS(f"Created {len(to_create)} job records"))
        
        if to_update:
            # Update fields (limited selection due to large number of fields)
            Genius_Job.objects.bulk_update(
                to_update,
                ['client_cid', 'prospect', 'division', 'user_id', 'service', 'status',
                 'contract_date', 'contract_amount', 'job_value', 'deposit_amount',
                 'sold_date', 'start_date', 'end_date', 'updated_at'],
                batch_size=BATCH_SIZE
            )
            self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} job records"))
    
    def _update_job_record(self, record, field_data):
        """Update job record with new field data."""
        record.client_cid = field_data['client_cid']
        record.prospect = field_data['prospect']
        record.division = field_data['division']
        record.service = field_data['service']
        record.user_id = field_data['user_id']
        record.status = field_data['status']
        record.contract_date = field_data['contract_date']
        record.contract_amount = field_data['contract_amount']
        record.job_value = field_data['job_value']
        record.deposit_amount = field_data['deposit_amount']
        record.sold_date = field_data['sold_date']
        record.start_date = field_data['start_date']
        record.end_date = field_data['end_date']
        record.updated_at = field_data['updated_at']
        # Add more field updates as needed
    
    def _prepare_job_data(self, field_data):
        """Prepare job data dictionary for creation."""
        return {
            'id': field_data['id'],
            'client_cid': field_data['client_cid'],
            'prospect': field_data['prospect'],
            'division': field_data['division'],
            'service': field_data['service'],
            'user_id': field_data['user_id'],
            'status': field_data['status'],
            'contract_date': field_data['contract_date'],
            'contract_amount': field_data['contract_amount'],
            'job_value': field_data['job_value'],
            'deposit_amount': field_data['deposit_amount'],
            'sold_date': field_data['sold_date'],
            'start_date': field_data['start_date'],
            'end_date': field_data['end_date'],
            'add_user_id': field_data['add_user_id'],
            'add_date': field_data['add_date'],
            'updated_at': field_data['updated_at']
            # Add more fields as needed
        }
