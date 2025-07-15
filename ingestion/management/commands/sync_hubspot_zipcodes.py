
"""
Management command for syncing HubSpot zip codes using modular architecture
Follows import_refactoring.md enterprise architecture standards
"""
import os
import csv
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from ingestion.models.hubspot import Hubspot_ZipCode
from ingestion.sync.hubspot.clients.zipcode_client import HubSpotZipCodeClient
from ingestion.sync.hubspot.processors.zipcode_processor import HubSpotZipCodeProcessor
from ingestion.sync.hubspot.engines.zipcode_engine import HubSpotZipCodeSyncEngine

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class Command(BaseCommand):
    help = "Sync zip codes from GitHub zips.csv into HubSpot ZipCode model using modular architecture."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving to database'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for database updates (default: 500)'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 500)

        # Step 1: Fetch CSV from GitHub
        client = HubSpotZipCodeClient()
        self.stdout.write("Fetching zip codes from GitHub...")
        try:
            csv_content = client.fetch_csv()
        except Exception as e:
            self.stderr.write(f"Failed to fetch CSV: {e}")
            return

        # Step 2: Parse and validate CSV
        processor = HubSpotZipCodeProcessor()
        records = processor.parse_csv(csv_content)
        valid_records = processor.filter_valid(records)
        self.stdout.write(f"Found {len(records)} records, {len(valid_records)} valid zip codes in CSV.")
        if dry_run:
            self.stdout.write(f"Dry run: would import {len(valid_records)} records.")
            return

        # Step 3: Batch sync using engine
        # Step 3: Batch sync using engine (progress handled in engine)
        engine = HubSpotZipCodeSyncEngine(batch_size=batch_size)
        created, updated = engine.sync_zipcodes(valid_records, dry_run=dry_run, show_progress=True, stdout=self.stdout)
        self.stdout.write(f"Imported {created} new zip codes, updated {updated}.")
