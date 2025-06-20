import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from ingestion.models.leadconduit import LeadConduit_Lead
from ingestion.utils import parse_datetime_obj
from tqdm import tqdm
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))  # Default to 500 if not set

class Command(BaseCommand):
    help = "Import leads from a LeadConduit-exported CSV file. Default CSV path: ingestion/csv/leadconduit_leads.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            nargs="?",
            default=os.path.join(settings.BASE_DIR, 'ingestion', 'csv', 'leadconduit_leads.csv'),
            help="Path to the CSV file. Defaults to BASE_DIR/ingestion/csv/leadconduit_leads.csv"
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving to database'
        )
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh of existing leads'
        )

    def handle(self, *args, **options):
        file_path = options["csv_file"]
        dry_run = options['dry_run']
        force_refresh = options['force_refresh']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at {file_path}"))
            return

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

        if not rows:
            self.stdout.write(self.style.WARNING("CSV file is empty."))
            return

        self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} leads from {file_path}..."))

        # Print CSV headers for debugging
        headers = list(rows[0].keys()) if rows else []
        self.stdout.write(self.style.SUCCESS(f"CSV Headers: {', '.join(headers)}"))

        # Process rows in batches
        total_processed = 0
        total_created = 0
        total_updated = 0
        total_skipped = 0

        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            processed, created, updated, skipped = self._process_batch(
                batch, dry_run, force_refresh
            )
            total_processed += processed
            total_created += created
            total_updated += updated
            total_skipped += skipped

        self.stdout.write(self.style.SUCCESS(
            f"Import completed: {total_processed} processed, "
            f"{total_created} created, {total_updated} updated, {total_skipped} skipped"
        ))

    @transaction.atomic
    def _process_batch(self, rows, dry_run=False, force_refresh=False):
        """Process a single batch of records with database transaction."""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        
        # Get lead IDs from the batch
        lead_ids = []
        for row in rows:
            lead_id = self._extract_lead_id(row)
            if lead_id:
                lead_ids.append(lead_id)
        
        # Get existing records in one query
        existing_records = {}
        if not dry_run:
            existing_records = LeadConduit_Lead.objects.in_bulk(lead_ids)

        to_create = []
        to_update = []

        for row in tqdm(rows, desc="Processing batch"):
            try:
                lead_data = self._map_csv_row_to_lead(row)
                lead_id = lead_data.get('lead_id')
                
                if not lead_id:
                    self.stdout.write(self.style.WARNING(f"Skipping row with missing lead_id: {row}"))
                    skipped += 1
                    continue
                
                processed += 1
                
                if dry_run:
                    self.stdout.write(f"Would process lead: {lead_id} - {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}")
                    continue
                
                existing_lead = existing_records.get(lead_id)
                
                if existing_lead:
                    if force_refresh:
                        # Update existing lead
                        for field, value in lead_data.items():
                            if field != 'lead_id':  # Don't update the primary key
                                setattr(existing_lead, field, value)
                        to_update.append(existing_lead)
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Create new lead
                    lead = LeadConduit_Lead(**lead_data)
                    to_create.append(lead)
                    created += 1
                    
            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
                self.stdout.write(self.style.ERROR(f"Error processing row: {e}"))
                continue        # Bulk operations
        if not dry_run:
            if to_create:
                LeadConduit_Lead.objects.bulk_create(to_create, ignore_conflicts=True)
            if to_update:
                LeadConduit_Lead.objects.bulk_update(to_update, [
                    'flow_id', 'flow_name', 'source_id', 'source_name',
                    'first_name', 'last_name', 'email', 'phone_1', 'phone_2',
                    'address_1', 'address_2', 'city', 'state', 'postal_code', 'country',
                    'reference', 'submission_timestamp', 'full_data',
                    'latest_event_id', 'latest_outcome',
                    'campaign', 'ad_group', 'keyword', 'utm_source', 'utm_medium',
                    'utm_campaign', 'utm_content', 'utm_term',
                    'quality_score', 'lead_score', 'is_duplicate',
                    'ip_address', 'user_agent', 'referring_url', 'landing_page',
                    'status', 'disposition', 'import_source',
                    'hs_createdate', 'hs_lastmodifieddate', 'hs_object_id',
                    'hs_lead_status', 'hs_lifecyclestage', 'hs_analytics_source',
                    'hs_analytics_source_data_1', 'hs_analytics_source_data_2',
                    'salesrabbit_lead_id', 'salesrabbit_rep_id', 'salesrabbit_rep_name',
                    'salesrabbit_area_id', 'salesrabbit_area_name', 'salesrabbit_status',
                    'salesrabbit_disposition', 'salesrabbit_notes', 'salesrabbit_created_at',
                    'salesrabbit_updated_at', 'salesrabbit_appointment_date',
                    'salesrabbit_sale_amount', 'salesrabbit_commission'
                ])

        return processed, created, updated, skipped

    def _extract_lead_id(self, row):
        """Extract lead ID from CSV row - try multiple possible field names"""
        possible_fields = ['lead_id', 'id', 'leadId', 'Lead ID', 'Lead Id', '_id']
        
        for field in possible_fields:
            if field in row and row[field]:
                return str(row[field]).strip()
        
        return None

    def _map_csv_row_to_lead(self, row):
        """Map CSV row to LeadConduit_Lead model fields"""
        
        # Clean and normalize field names
        normalized_row = {}
        for key, value in row.items():
            # Convert to lowercase and replace spaces/special chars with underscores
            clean_key = key.lower().replace(' ', '_').replace('-', '_').replace('.', '_')
            normalized_row[clean_key] = value.strip() if isinstance(value, str) else value        # Field mapping dictionary - maps CSV headers to model fields
        field_mapping = {
            # Lead identification
            'lead_id': 'lead_id',
            'id': 'lead_id',
            'leadid': 'lead_id',
            'lead_id_': 'lead_id',
            '_id': 'lead_id',
            
            # Flow information
            'flow_id': 'flow_id',
            'flowid': 'flow_id',
            'flow_name': 'flow_name',
            'flowname': 'flow_name',
            
            # Source information
            'source_id': 'source_id',
            'sourceid': 'source_id',
            'source_name': 'source_name',
            'sourcename': 'source_name',
            'source': 'source_name',
            
            # Contact information
            'first_name': 'first_name',
            'firstname': 'first_name',
            'fname': 'first_name',
            'last_name': 'last_name',
            'lastname': 'last_name',
            'lname': 'last_name',
            'email': 'email',
            'email_address': 'email',
            'phone_1': 'phone_1',
            'phone1': 'phone_1',
            'phone': 'phone_1',
            'primary_phone': 'phone_1',
            'phone_number': 'phone_1',
            'phone_2': 'phone_2',
            'phone2': 'phone_2',
            'secondary_phone': 'phone_2',
            'alternate_phone': 'phone_2',
            
            # Address information
            'address_1': 'address_1',
            'address1': 'address_1',
            'address': 'address_1',
            'street_address': 'address_1',
            'address_2': 'address_2',
            'address2': 'address_2',
            'address_line_2': 'address_2',
            'city': 'city',
            'state': 'state',
            'state_province': 'state',
            'postal_code': 'postal_code',
            'postalcode': 'postal_code',
            'zip': 'postal_code',
            'zip_code': 'postal_code',
            'country': 'country',
            
            # Marketing and campaign information
            'campaign': 'campaign',
            'campaign_name': 'campaign',
            'ad_group': 'ad_group',
            'adgroup': 'ad_group',
            'ad_group_name': 'ad_group',
            'keyword': 'keyword',
            'kw': 'keyword',
            'search_term': 'keyword',
            'utm_source': 'utm_source',
            'utmsource': 'utm_source',
            'utm_medium': 'utm_medium',
            'utmmedium': 'utm_medium',
            'utm_campaign': 'utm_campaign',
            'utmcampaign': 'utm_campaign',
            'utm_content': 'utm_content',
            'utmcontent': 'utm_content',
            'utm_term': 'utm_term',
            'utmterm': 'utm_term',
            
            # Lead quality and scoring
            'quality_score': 'quality_score',
            'qualityscore': 'quality_score',
            'score': 'quality_score',
            'lead_score': 'lead_score',
            'leadscore': 'lead_score',
            'is_duplicate': 'is_duplicate',
            'duplicate': 'is_duplicate',
            'dup': 'is_duplicate',
            
            # Geographic and technical data
            'ip_address': 'ip_address',
            'ip': 'ip_address',
            'user_agent': 'user_agent',
            'useragent': 'user_agent',
            'ua': 'user_agent',
            'referring_url': 'referring_url',
            'referrer': 'referring_url',
            'ref_url': 'referring_url',
            'landing_page': 'landing_page',
            'landingpage': 'landing_page',
            'lp': 'landing_page',
            'page_url': 'landing_page',
            
            # Lead status and disposition
            'status': 'status',
            'lead_status': 'status',
            'disposition': 'disposition',
            'outcome': 'disposition',
            
            # Additional fields
            'reference': 'reference',
            'ref': 'reference',
            'submission_timestamp': 'submission_timestamp',
            'submission_time': 'submission_timestamp',
            'submit_time': 'submission_timestamp',
            'created_at': 'submission_timestamp',
            'timestamp': 'submission_timestamp',
            'date_created': 'submission_timestamp',
            'date_submitted': 'submission_timestamp',
              # Latest event info
            'latest_event_id': 'latest_event_id',
            'event_id': 'latest_event_id',
            'latest_outcome': 'latest_outcome',
            'outcome': 'latest_outcome',
            
            # HubSpot properties (when included in LeadConduit exports)
            'createdate': 'hs_createdate',
            'hs_createdate': 'hs_createdate',
            'lastmodifieddate': 'hs_lastmodifieddate',
            'hs_lastmodifieddate': 'hs_lastmodifieddate',
            'hs_object_id': 'hs_object_id',
            'hubspot_object_id': 'hs_object_id',
            'hs_lead_status': 'hs_lead_status',
            'lead_status': 'hs_lead_status',
            'hs_lifecyclestage': 'hs_lifecyclestage',
            'lifecyclestage': 'hs_lifecyclestage',
            'lifecycle_stage': 'hs_lifecyclestage',            'hs_analytics_source': 'hs_analytics_source',
            'analytics_source': 'hs_analytics_source',
            'hs_analytics_source_data_1': 'hs_analytics_source_data_1',
            'hs_analytics_source_data_2': 'hs_analytics_source_data_2',
            
            # SalesRabbit properties (when included in LeadConduit exports)
            'salesrabbit_lead_id': 'salesrabbit_lead_id',
            'lead_salesrabbit_lead_id': 'salesrabbit_lead_id',
            'sr_lead_id': 'salesrabbit_lead_id',
            'salesrabbit_rep_id': 'salesrabbit_rep_id',
            'sr_rep_id': 'salesrabbit_rep_id',
            'rep_id': 'salesrabbit_rep_id',
            'salesrabbit_rep_name': 'salesrabbit_rep_name',
            'sr_rep_name': 'salesrabbit_rep_name',
            'rep_name': 'salesrabbit_rep_name',
            'salesrabbit_area_id': 'salesrabbit_area_id',
            'sr_area_id': 'salesrabbit_area_id',
            'area_id': 'salesrabbit_area_id',
            'salesrabbit_area_name': 'salesrabbit_area_name',
            'sr_area_name': 'salesrabbit_area_name',
            'area_name': 'salesrabbit_area_name',
            'salesrabbit_status': 'salesrabbit_status',
            'sr_status': 'salesrabbit_status',
            'salesrabbit_disposition': 'salesrabbit_disposition',
            'sr_disposition': 'salesrabbit_disposition',
            'salesrabbit_notes': 'salesrabbit_notes',
            'sr_notes': 'salesrabbit_notes',
            'salesrabbit_created_at': 'salesrabbit_created_at',
            'sr_created_at': 'salesrabbit_created_at',
            'salesrabbit_updated_at': 'salesrabbit_updated_at',
            'sr_updated_at': 'salesrabbit_updated_at',
            'salesrabbit_appointment_date': 'salesrabbit_appointment_date',
            'sr_appointment_date': 'salesrabbit_appointment_date',
            'appointment_date': 'salesrabbit_appointment_date',
            'salesrabbit_sale_amount': 'salesrabbit_sale_amount',
            'sr_sale_amount': 'salesrabbit_sale_amount',
            'sale_amount': 'salesrabbit_sale_amount',
            'salesrabbit_commission': 'salesrabbit_commission',
            'sr_commission': 'salesrabbit_commission',
            'commission': 'salesrabbit_commission',
        }

        # Map the row data
        lead_data = {}
        
        # Extract lead_id first (required field)
        lead_id = self._extract_lead_id(row)
        if lead_id:
            lead_data['lead_id'] = lead_id        # Map other fields
        for csv_field, model_field in field_mapping.items():
            if csv_field in normalized_row and normalized_row[csv_field]:
                value = normalized_row[csv_field]                # Special handling for specific fields
                if model_field in ['submission_timestamp', 'hs_createdate', 'hs_lastmodifieddate', 
                                 'salesrabbit_created_at', 'salesrabbit_updated_at', 'salesrabbit_appointment_date'] and value:
                    try:
                        # Try to parse various datetime formats
                        parsed_dt = parse_datetime_obj(value)
                        if parsed_dt:
                            # Make timezone-aware if it's naive
                            if parsed_dt.tzinfo is None:
                                parsed_dt = timezone.make_aware(parsed_dt, timezone.utc)
                            lead_data[model_field] = parsed_dt
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse timestamp: {value}")
                        continue
                elif model_field in ['phone_1', 'phone_2'] and value:
                    # Clean phone numbers
                    clean_phone = ''.join(filter(str.isdigit, value))
                    if len(clean_phone) >= 10:
                        lead_data[model_field] = clean_phone
                elif model_field == 'email' and value:
                    # Basic email validation
                    if '@' in value and '.' in value:
                        lead_data[model_field] = value.lower()
                elif model_field == 'is_duplicate' and value:
                    # Convert to boolean
                    lead_data[model_field] = value.lower() in ('true', '1', 'yes', 'y', 'duplicate')
                elif model_field in ['quality_score', 'lead_score', 'salesrabbit_sale_amount', 'salesrabbit_commission'] and value:
                    # Convert to numeric
                    try:
                        if model_field in ['salesrabbit_sale_amount', 'salesrabbit_commission']:
                            # Remove currency symbols and convert to decimal
                            clean_value = value.replace('$', '').replace(',', '').strip()
                            lead_data[model_field] = float(clean_value) if clean_value else None
                        elif model_field == 'quality_score':
                            lead_data[model_field] = float(value)
                        else:
                            lead_data[model_field] = int(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse {model_field}: {value}")
                        continue
                else:
                    lead_data[model_field] = value

        # Store full CSV row data as JSON for reference
        lead_data['full_data'] = dict(row)
        
        # Set import source
        lead_data['import_source'] = 'csv'

        return lead_data
