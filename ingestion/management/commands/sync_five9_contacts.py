"""
Five9 Contacts Sync Management Comm        parser.add_argument(
            '--max-records',
            type=int,
            default=Five9Config.MAX_BATCH_SIZE,
            help=f'Maximum records to retrieve per list (default: {Five9Config.MAX_BATCH_SIZE})'
        )ynchronizes contact records from Five9 to the data warehouse
"""
import logging
from typing import Any, Dict
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone
from ingestion.sync.five9.engines.contacts import ContactsSyncEngine
from ingestion.config.five9_config import Five9Config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command for syncing Five9 contacts"""
    
    help = 'Sync contact records from Five9'
    
    def add_arguments(self, parser: CommandParser):
        """Add command arguments"""
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync instead of delta sync'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run sync without saving data to database'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=Five9Config.DEFAULT_BATCH_SIZE,
            help=f'Number of records to process in each batch (default: {Five9Config.DEFAULT_BATCH_SIZE})'
        )
        
        parser.add_argument(
            '--max-records-per-list',
            type=int,
            default=1000,
            help='Maximum records to retrieve per list (default: 1000)'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Sync records modified since this datetime (YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--list-name',
            type=str,
            help='Sync only the specified contact list'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging output'
        )
    
    def handle(self, *args, **options):
        """Execute the sync command"""
        # Setup logging
        if options['verbose']:
            logging.getLogger('ingestion.sync.five9').setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.stdout.write(
            self.style.SUCCESS('Starting Five9 contacts sync...')
        )
        
        # Validate arguments
        if options['since'] and options['full']:
            self.stdout.write(
                self.style.ERROR('Cannot use --since with --full. Use one or the other.')
            )
            return
        
        # Parse since datetime if provided
        since_datetime = None
        if options['since']:
            try:
                since_datetime = timezone.datetime.fromisoformat(options['since'])
                if timezone.is_naive(since_datetime):
                    since_datetime = timezone.make_aware(since_datetime)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid datetime format: {options['since']}. "
                        "Use YYYY-MM-DD HH:MM:SS"
                    )
                )
                return
        
        # Create sync engine
        sync_engine = ContactsSyncEngine(
            batch_size=options['batch_size']
        )
        
        try:
            # Prepare sync parameters
            sync_params = {
                'force_full': options['full'],
                'max_records_per_list': options['max_records_per_list'],
                'dry_run': options['dry_run'],
            }
            
            if options['list_name']:
                sync_params['target_list'] = options['list_name']
            
            if since_datetime:
                sync_params['since'] = since_datetime
            
            # Log sync parameters
            self.stdout.write(
                f"Sync parameters:\n"
                f"  - Full sync: {options['full']}\n"
                f"  - Dry run: {options['dry_run']}\n"
                f"  - Batch size: {options['batch_size']}\n"
                f"  - Max records per list: {options['max_records_per_list']}\n"
                f"  - Target list: {options['list_name'] or 'All lists'}\n"
                f"  - Since: {since_datetime or 'Not specified'}"
            )
            
            # Run the sync
            start_time = timezone.now()
            result = sync_engine.sync_data(**sync_params)
            end_time = timezone.now()
            
            # Report results
            duration = end_time - start_time
            
            if result.get('success'):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Five9 contacts sync completed successfully!\n"
                        f"Duration: {duration}\n"
                        f"Records processed: {result.get('total_processed', 0)}\n"
                        f"Created: {result.get('created', 0)}\n"
                        f"Updated: {result.get('updated', 0)}\n"
                        f"Skipped: {result.get('skipped', 0)}\n"
                        f"Errors: {len(result.get('errors', []))}"
                    )
                )
                
                if options['dry_run']:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠️ This was a dry run - no data was saved to the database."
                        )
                    )
            else:
                error_msg = result.get('error', 'Unknown error')
                self.stdout.write(
                    self.style.ERROR(
                        f"\n❌ Five9 contacts sync failed!\n"
                        f"Duration: {duration}\n"
                        f"Error: {error_msg}"
                    )
                )
                return
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n⚠️ Sync interrupted by user')
            )
            return
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Unexpected error: {e}')
            )
            logger.exception("Unexpected error in Five9 sync command")
            raise
        
        finally:
            # Ensure cleanup - don't call cleanup since it's async and handled internally
            pass
    
    def _format_duration(self, duration) -> str:
        """Format duration for display"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
