"""
Sync All Google Sheets
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Sync all configured Google Sheets"""
    
    help = "Sync all configured Google Sheets to database"
    
    def add_arguments(self, parser):
        """Add command arguments"""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run all syncs without saving data to database"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force sync all sheets even if not modified"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for all sync operations"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug logging"
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress output except errors"
        )
        parser.add_argument(
            "--skip-marketing-leads",
            action="store_true",
            help="Skip marketing leads sync"
        )
        parser.add_argument(
            "--test-connections",
            action="store_true",
            help="Test all Google Sheets API connections only"
        )
        parser.add_argument(
            "--show-summary",
            action="store_true",
            help="Show sync summary for all sheets and exit"
        )
    
    def handle(self, *args, **options):
        """Execute the sync command"""
        
        # Configure logging level
        if options['debug']:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.DEBUG)
        elif options['quiet']:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.ERROR)
        else:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.INFO)
        
        try:
            # Test connections only
            if options['test_connections']:
                self._test_all_connections(options)
                return
            
            # Show summary only
            if options['show_summary']:
                self._show_all_summaries(options)
                return
            
            # Run all syncs
            self.stdout.write("Starting Google Sheets sync for all configured sheets...")
            self.stdout.write(f"Configuration:")
            self.stdout.write(f"  - Dry run: {options['dry_run']}")
            self.stdout.write(f"  - Force sync: {options['force']}")
            self.stdout.write(f"  - Batch size: {options['batch_size']}")
            
            results = {}
            total_start_time = timezone.now()
            
            # Available sheet sync commands
            sheet_commands = [
                ('Marketing Leads', 'sync_gsheet_marketing_leads', options.get('skip_marketing_leads', False))
            ]
            
            for sheet_name, command_name, skip in sheet_commands:
                if skip:
                    self.stdout.write(f"\nSkipping {sheet_name} sync (--skip-{sheet_name.lower().replace(' ', '-')} specified)")
                    continue
                
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"Syncing {sheet_name}...")
                self.stdout.write(f"{'='*60}")
                
                try:
                    start_time = timezone.now()
                    
                    # Build command arguments
                    cmd_args = []
                    cmd_options = {
                        'dry_run': options['dry_run'],
                        'force': options['force'],
                        'batch_size': options['batch_size'],
                        'quiet': options['quiet'],
                        'debug': options['debug']
                    }
                    
                    # Run the sync command
                    call_command(command_name, *cmd_args, **cmd_options)
                    
                    end_time = timezone.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    results[sheet_name] = {
                        'status': 'success',
                        'duration': duration
                    }
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {sheet_name} sync completed in {duration:.1f} seconds")
                    )
                
                except Exception as e:
                    logger.error(f"{sheet_name} sync failed: {e}")
                    results[sheet_name] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    self.stdout.write(
                        self.style.ERROR(f"✗ {sheet_name} sync failed: {e}")
                    )
                    
                    # Continue with other syncs unless it's a critical error
                    if "authentication" in str(e).lower() or "credentials" in str(e).lower():
                        self.stdout.write(
                            self.style.ERROR("Authentication error - stopping all syncs")
                        )
                        break
            
            # Display final summary
            total_duration = (timezone.now() - total_start_time).total_seconds()
            self._display_final_summary(results, total_duration, options)
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nSync interrupted by user")
            )
        except Exception as e:
            logger.error(f"All sync command failed: {e}")
            self.stdout.write(
                self.style.ERROR(f"All sync failed: {e}")
            )
            raise
    
    def _test_all_connections(self, options):
        """Test connections to all Google Sheets"""
        self.stdout.write("Testing Google Sheets API connections...")
        
        # Test marketing leads connection
        try:
            from ingestion.sync.gsheet.engines import MarketingLeadsSyncEngine
            
            engine = MarketingLeadsSyncEngine()
            if engine.client.test_connection():
                self.stdout.write(
                    self.style.SUCCESS("✓ Marketing Leads sheet connection successful")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("✗ Marketing Leads sheet connection failed")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Marketing Leads connection error: {e}")
            )
        
        # Add other sheet connections here as they're implemented
    
    def _show_all_summaries(self, options):
        """Show sync summaries for all sheets"""
        self.stdout.write("Google Sheets Sync Summary")
        self.stdout.write("=" * 50)
        
        # Marketing leads summary
        try:
            from ingestion.sync.gsheet.engines import MarketingLeadsSyncEngine
            
            engine = MarketingLeadsSyncEngine()
            summary = engine.get_sync_summary()
            
            self.stdout.write("\nMarketing Leads:")
            self.stdout.write("-" * 20)
            self._display_sheet_summary(summary)
            
        except Exception as e:
            self.stdout.write(f"\nMarketing Leads: Error - {e}")
        
        # Add other sheet summaries here as they're implemented
    
    def _display_sheet_summary(self, summary):
        """Display summary for a single sheet"""
        status = summary.get('status', 'unknown')
        
        if status == 'never_synced':
            self.stdout.write("  Status: Never synced")
            return
        
        if status == 'error':
            self.stdout.write(f"  Status: Error - {summary.get('error')}")
            return
        
        # Basic info
        last_sync = summary.get('last_sync_time')
        if last_sync:
            self.stdout.write(f"  Last sync: {last_sync}")
            self.stdout.write(f"  Status: {status}")
        
        # Data counts
        db_count = summary.get('records_in_database', 0)
        sheet_count = summary.get('records_in_sheet', 0)
        self.stdout.write(f"  Database records: {db_count:,}")
        self.stdout.write(f"  Sheet rows: {sheet_count:,}")
    
    def _display_final_summary(self, results, total_duration, options):
        """Display final summary of all syncs"""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("GOOGLE SHEETS SYNC SUMMARY")
        self.stdout.write(f"{'='*60}")
        
        successful = sum(1 for r in results.values() if r['status'] == 'success')
        failed = sum(1 for r in results.values() if r['status'] == 'failed')
        total = len(results)
        
        self.stdout.write(f"Total sheets processed: {total}")
        self.stdout.write(f"Successful: {successful}")
        self.stdout.write(f"Failed: {failed}")
        self.stdout.write(f"Total duration: {total_duration:.1f} seconds")
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("\n⚠ DRY RUN: No data was actually saved to the database")
            )
        
        # Detail results
        if results:
            self.stdout.write(f"\nDetailed Results:")
            for sheet_name, result in results.items():
                status = result['status']
                if status == 'success':
                    duration = result.get('duration', 0)
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {sheet_name}: {status} ({duration:.1f}s)")
                    )
                else:
                    error = result.get('error', 'Unknown error')
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {sheet_name}: {status} - {error}")
                    )
        
        # Overall status
        if failed == 0:
            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 All Google Sheets syncs completed successfully!")
            )
        elif successful > 0:
            self.stdout.write(
                self.style.WARNING(f"\n⚠ Partial success: {successful}/{total} sheets synced")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"\n❌ All syncs failed")
            )
