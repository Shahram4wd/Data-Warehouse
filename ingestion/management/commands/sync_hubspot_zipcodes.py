"""
New HubSpot zipcodes sync command using the unified architecture
"""
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.zipcode_engine import HubSpotZipCodeSyncEngine
from ingestion.sync.hubspot.clients.zipcode_client import HubSpotZipCodeClient
from ingestion.sync.hubspot.processors.zipcode_processor import HubSpotZipCodeProcessor

class Command(BaseHubSpotSyncCommand):
    """Sync zipcodes from GitHub CSV using new architecture
    
    Examples:
        # Standard sync (always full since zipcodes are static)
        python manage.py sync_hubspot_zipcodes
        
        # Force overwrite ALL records
        python manage.py sync_hubspot_zipcodes --force
        
        # Test without saving
        python manage.py sync_hubspot_zipcodes --dry-run
    """
    
    help = """Sync zipcodes from GitHub CSV into HubSpot ZipCode model using unified architecture.
    
Use --force to completely overwrite existing records, ignoring timestamps.
This ensures all data is replaced with the latest from the CSV source."""
    
    def get_sync_engine(self, **options):
        """Get the zipcode sync engine"""
        return HubSpotZipCodeSyncEngine(
            batch_size=options.get('batch_size', 500),
            force_overwrite=options.get('force_overwrite', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "zipcodes"

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 500)
        force_overwrite = options.get('force_overwrite', False)

        # Step 1: Fetch CSV from GitHub
        client = HubSpotZipCodeClient()
        self.stdout.write("Fetching zip codes from GitHub...")
        try:
            csv_content = client.fetch_csv()
        except Exception as e:
            self.stderr.write(f"Failed to fetch CSV: {e}")
            
            # Check existing zipcode data in database
            try:
                from ingestion.models.hubspot import Hubspot_ZipCode
                existing_count = Hubspot_ZipCode.objects.count()
                if existing_count > 0:
                    self.stdout.write(f"✓ GitHub data unavailable, but database contains {existing_count:,} existing zipcodes")
                    self.stdout.write("ℹ️  Zipcode sync skipped - existing data is being preserved")
                    return
                else:
                    self.stderr.write("⚠️  No existing zipcode data found and GitHub source unavailable")
                    return
            except Exception as db_error:
                self.stderr.write(f"Error checking existing zipcode data: {db_error}")
                return

        # Step 2: Parse and validate CSV
        processor = HubSpotZipCodeProcessor()
        records = processor.parse_csv(csv_content)
        valid_records = processor.filter_valid(records)
        self.stdout.write(f"Found {len(records)} records, {len(valid_records)} valid zip codes in CSV.")
        if dry_run:
            self.stdout.write(f"Dry run: would import {len(valid_records)} records.")
            return

        # Step 3: Batch sync using engine from get_sync_engine (unified architecture)
        engine = self.get_sync_engine(**options)
        created, updated = engine.sync_zipcodes(valid_records, dry_run=dry_run, show_progress=True, stdout=self.stdout)
        self.stdout.write(f"Imported {created} new zip codes, updated {updated}.")
