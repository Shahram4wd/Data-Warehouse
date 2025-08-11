"""
Django management command to clear and re-import Google Sheets data

Usage:
    pytho        try:
            # Initialize the sync engine
            engine = MarketingLeadsSyncEngine()
            
            # Run the sync
            result = engine.sync_sync()
            
            self.stdout.write(
                self.style.SUCCESS('   ✅ Import completed successfully')
            )
            
            return resultclear_and_reimport
    
Or with Docker:
    docker-compose exec web python manage.py clear_and_reimport
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from ingestion.models.gsheet import GoogleSheetMarketingLead
from ingestion.sync.gsheet.engines.marketing_leads import MarketingLeadsSyncEngine


class Command(BaseCommand):
    help = 'Clear all existing data and re-import fresh from Google Sheets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--skip-import',
            action='store_true',
            help='Only clear data, skip the import step',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting Clear and Re-import Process')
        )
        self.stdout.write('=' * 50)

        try:
            # Step 1: Clear existing data
            self.clear_existing_data(dry_run=options['dry_run'])
            
            # Step 2: Run fresh import (unless skipped)
            if not options['skip_import'] and not options['dry_run']:
                self.run_fresh_import()
            elif options['skip_import']:
                self.stdout.write(
                    self.style.WARNING('⏭️  Skipping import step as requested')
                )
            elif options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('⏭️  Skipping import step (dry run mode)')
                )
            
            self.show_final_statistics()
            
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(
                self.style.SUCCESS('✅ Process completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Process failed: {str(e)}')
            )
            raise

    def clear_existing_data(self, dry_run=False):
        """Delete all existing marketing lead records"""
        self.stdout.write('🗑️  Clearing existing data...')
        
        count = GoogleSheetMarketingLead.objects.count()
        self.stdout.write(f'   Found {count:,} existing records')
        
        if count > 0:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'   [DRY RUN] Would delete {count:,} records')
                )
            else:
                with transaction.atomic():
                    GoogleSheetMarketingLead.objects.all().delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'   ✅ Deleted {count:,} records')
                    )
        else:
            self.stdout.write(
                self.style.SUCCESS('   ✅ No existing records to delete')
            )

    def run_fresh_import(self):
        """Run a fresh import from Google Sheets"""
        self.stdout.write('\n📥 Starting fresh import...')
        
        try:
            # Initialize the sync processor
            processor = MarketingLeadsProcessor()
            
            # Run the sync
            result = processor.sync()
            
            self.stdout.write(
                self.style.SUCCESS('   ✅ Import completed successfully')
            )
            
            return result
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Import failed: {str(e)}')
            )
            raise

    def show_final_statistics(self):
        """Show final database statistics"""
        final_count = GoogleSheetMarketingLead.objects.count()
        unique_rows = GoogleSheetMarketingLead.objects.values('sheet_row_number').distinct().count()
        
        self.stdout.write(f'\n📊 Final Statistics:')
        self.stdout.write(f'   Total records: {final_count:,}')
        self.stdout.write(f'   Unique row numbers: {unique_rows:,}')
        
        if final_count == unique_rows:
            self.stdout.write(
                self.style.SUCCESS('   Data integrity: ✅ Perfect')
            )
        else:
            self.stdout.write(
                self.style.ERROR('   Data integrity: ❌ Has duplicates')
            )
