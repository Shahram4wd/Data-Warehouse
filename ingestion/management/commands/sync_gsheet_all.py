"""
Sync All Google Sheets
"""
import asyncio
import logging
from django.core.management.base import CommandError
from django.core.management import call_command
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    """Sync all configured Google Sheets"""
    
    help = "Sync all configured Google Sheets to database"
    crm_name = 'gsheet'
    entity_name = 'all'
    
    def add_arguments(self, parser):
        """Add command arguments"""
        # Add standard BaseSyncCommand arguments
        super().add_arguments(parser)
        
        # Add GSheet-specific arguments for controlling which sheets to sync
        parser.add_argument(
            "--skip-marketing-leads",
            action="store_true",
            help="Skip marketing leads sync"
        )
        parser.add_argument(
            "--skip-marketing-spends",
            action="store_true", 
            help="Skip marketing spends sync"
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
        """Execute the sync command following standardized patterns"""
        
        # Setup debug logging if requested
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.DEBUG)
        elif options.get('quiet'):
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.ERROR)
        else:
            logging.getLogger('ingestion.sync.gsheet').setLevel(logging.INFO)
        
        self.stdout.write(
            self.style.SUCCESS('Starting GSheet all data sync...')
        )
        
        
        try:
            # Get standardized options
            dry_run = options.get('dry_run', False)
            force_overwrite = options.get('force', False)
            batch_size = options.get('batch_size', 500)
            max_records = options.get('max_records', 0)
            quiet = options.get('quiet', False)
            debug = options.get('debug', False)
            
            # Handle special operations first
            if options.get('test_connections'):
                self.stdout.write("Testing all Google Sheets API connections...")
                self._test_all_connections()
                return
            
            if options.get('show_summary'):
                self.stdout.write("Getting sync summary for all sheets...")
                self._show_all_summaries()
                return
            
            # Display configuration
            dry_mode = "DRY RUN: " if dry_run else ""
            self.stdout.write(f"{dry_mode}Starting Google Sheets sync for all configured sheets...")
            self.stdout.write(f"Configuration:")
            self.stdout.write(f"  - Dry run: {dry_run}")
            self.stdout.write(f"  - Force sync: {force_overwrite}")
            self.stdout.write(f"  - Batch size: {batch_size}")
            if max_records > 0:
                self.stdout.write(f"  - Max records: {max_records}")
            
            results = {}
            total_start_time = timezone.now()
            
            # Available sheet sync commands
            sheet_commands = [
                ('Marketing Leads', 'sync_gsheet_marketing_leads', options.get('skip_marketing_leads', False)),
                ('Marketing Spends', 'sync_gsheet_marketing_spends', options.get('skip_marketing_spends', False))
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
                    
                    # Build command arguments with standardized names
                    cmd_args = []
                    cmd_options = {
                        'dry_run': dry_run,
                        'force': force_overwrite,
                        'batch_size': batch_size,
                        'quiet': quiet,
                        'debug': debug
                    }
                    
                    # Add max_records if specified
                    if max_records > 0:
                        cmd_options['max_records'] = max_records
                    
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
            self.output_results({'success': True, 'results': results, 'duration': total_duration})
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nSync interrupted by user")
            )
        except Exception as e:
            logger.error(f"All sync command failed: {e}")
            if not isinstance(e, CommandError):
                raise CommandError(f'All sync failed: {e}')
    
    def output_results(self, result):
        """Output sync results following BaseSyncCommand pattern"""
        results = result.get('results', {})
        total_duration = result.get('duration', 0)
        
        success_count = sum(1 for r in results.values() if r.get('status') == 'success')
        failed_count = len(results) - success_count
        
        if failed_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ All Google Sheets sync completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ Google Sheets sync completed with {failed_count} failures')
            )
        
        self.stdout.write(f"Sheets: {len(results)} total ({success_count} succeeded, {failed_count} failed)")
        self.stdout.write(f"Duration: {total_duration:.2f} seconds")
        
        # Show individual results
        for sheet_name, sheet_result in results.items():
            status = sheet_result.get('status', 'unknown')
            duration = sheet_result.get('duration', 0)
            if status == 'success':
                self.stdout.write(f"  ✓ {sheet_name}: {duration:.1f}s")
            else:
                error = sheet_result.get('error', 'Unknown error')
                self.stdout.write(f"  ✗ {sheet_name}: {error}")
    
    def _test_all_connections(self):
        """Test all Google Sheets API connections"""
        # This would test connections for all configured sheets
        self.stdout.write("Testing Marketing Leads connection...")
        call_command('sync_gsheet_marketing_leads', '--test-connection')
        
        self.stdout.write("Testing Marketing Spends connection...")
        call_command('sync_gsheet_marketing_spends', '--test-connection')
        
        self.stdout.write(self.style.SUCCESS("All connection tests completed"))
    
    def _show_all_summaries(self):
        """Show summary for all Google Sheets"""
        self.stdout.write("Marketing Leads Summary:")
        call_command('sync_gsheet_marketing_leads', '--show-summary')
        
        self.stdout.write("\nMarketing Spends Summary:")
        call_command('sync_gsheet_marketing_spends', '--show-summary')
    
    def _display_final_summary(self, results, total_duration, options):
        """Display final summary (deprecated - use output_results)"""
    
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
