import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from ingestion.models.hubspot import Hubspot_ZipCode
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import zip codes from a CSV file into HubSpot ZipCode model. Default CSV path: ingestion/csv/zips.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            nargs="?",
            default=os.path.join(settings.BASE_DIR, 'ingestion', 'csv', 'zips.csv'),
            help="Path to the ZIP codes CSV file. Defaults to BASE_DIR/ingestion/csv/zips.csv"
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving to database'
        )
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh of existing zip codes'
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

        self.stdout.write(self.style.SUCCESS(f"Processing {len(rows)} zip codes from {file_path}..."))

        # Print CSV headers for debugging
        headers = list(rows[0].keys()) if rows else []
        self.stdout.write(self.style.SUCCESS(f"CSV Headers: {', '.join(headers)}"))

        # Process all rows
        total_processed = 0
        total_created = 0
        total_updated = 0
        total_skipped = 0

        processed, created, updated, skipped = self._process_zip_codes(
            rows, dry_run, force_refresh
        )
        
        total_processed += processed
        total_created += created
        total_updated += updated
        total_skipped += skipped

        self.stdout.write(self.style.SUCCESS(
            f"HubSpot zip code import completed: {total_processed} processed, "
            f"{total_created} created, {total_updated} updated, {total_skipped} skipped"
        ))

    @transaction.atomic
    def _process_zip_codes(self, rows, dry_run=False, force_refresh=False):
        """Process zip code records with database transaction."""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        
        # Get zip codes from the batch
        zip_codes = []
        for row in rows:
            zipcode = row.get('zipcode', '').strip()
            if zipcode:
                zip_codes.append(zipcode)
        
        # Get existing records in one query
        existing_records = {}
        if not dry_run:
            existing_records = Hubspot_ZipCode.objects.in_bulk(zip_codes)

        to_create = []
        to_update = []

        for row in tqdm(rows, desc="Processing zip codes"):
            try:
                zipcode_data = self._map_csv_row_to_zipcode(row)
                zipcode = zipcode_data.get('zipcode')
                
                if not zipcode:
                    self.stdout.write(self.style.WARNING(f"Skipping row with missing zipcode: {row}"))
                    skipped += 1
                    continue
                
                processed += 1
                
                if dry_run:
                    self.stdout.write(f"Would process zipcode: {zipcode} - {zipcode_data.get('city', '')}, {zipcode_data.get('state', '')}")
                    continue
                
                existing_zipcode = existing_records.get(zipcode)
                
                if existing_zipcode:
                    if force_refresh:
                        # Update existing zipcode
                        for field, value in zipcode_data.items():
                            if field != 'zipcode':  # Don't update the primary key
                                setattr(existing_zipcode, field, value)
                        to_update.append(existing_zipcode)
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Create new zipcode
                    zipcode_obj = Hubspot_ZipCode(**zipcode_data)
                    to_create.append(zipcode_obj)
                    created += 1
                    
            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
                self.stdout.write(self.style.ERROR(f"Error processing row: {e}"))
                continue

        # Bulk operations
        if not dry_run:
            if to_create:
                self.stdout.write(self.style.SUCCESS(f"Creating {len(to_create)} new zip codes..."))
                Hubspot_ZipCode.objects.bulk_create(to_create, ignore_conflicts=True)
            if to_update:
                self.stdout.write(self.style.SUCCESS(f"Updating {len(to_update)} existing zip codes..."))
                Hubspot_ZipCode.objects.bulk_update(to_update, ['division', 'city', 'county', 'state'])

        return processed, created, updated, skipped

    def _map_csv_row_to_zipcode(self, row):
        """Map CSV row to zipcode model fields."""
        zipcode = row.get('zipcode', '').strip()
        
        # Remove leading apostrophe if present (common in CSV exports)
        if zipcode.startswith("'"):
            zipcode = zipcode[1:]
        
        # Skip empty zipcodes
        if not zipcode:
            raise ValueError(f"Empty zipcode")
        
        # Validate zipcode format (should be numeric and reasonable length)
        if not zipcode.isdigit() or len(zipcode) < 5 or len(zipcode) > 10:
            raise ValueError(f"Invalid zipcode format: {zipcode}")
        
        return {
            'zipcode': zipcode,
            'division': row.get('division', '').strip() or None,
            'city': row.get('city', '').strip() or None,
            'county': row.get('county', '').strip() or None,
            'state': row.get('state', '').strip() or None,
        }
