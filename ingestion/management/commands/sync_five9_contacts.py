"""
Five9 Contacts Sync Management Command

Synchronizes contact records from Five9 to the data warehouse
"""
import logging
from typing import Any, Dict
from django.core.management.base import CommandParser
from django.utils import timezone
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.five9.engines.contacts import ContactsSyncEngine
from ingestion.config.five9_config import Five9Config

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    """Management command for syncing Five9 contacts"""
    
    help = 'Sync contact records from Five9'
    crm_name = 'Five9'
    entity_name = 'contacts'
    
    def add_arguments(self, parser: CommandParser):
        """Add command arguments"""
        # Add base sync arguments (--full, --force, --start-date, etc.)
        super().add_arguments(parser)
        
        # Add Five9-specific arguments
        parser.add_argument(
            '--max-records-per-list',
            type=int,
            default=2000,  # Increased for better bulk processing
            help='Maximum records to retrieve per list (default: 2000)'
        )
        
        parser.add_argument(
            '--list-name',
            type=str,
            help='Sync only the specified contact list'
        )
    
    def handle(self, *args, **options):
        """Execute the sync command"""
        # Setup logging
        if options['debug']:
            logging.getLogger('ingestion.sync.five9').setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.stdout.write(
            self.style.SUCCESS('Starting Five9 contacts sync...')
        )
        
        # Validate arguments
        if options['start_date'] and options['full']:
            self.stdout.write(
                self.style.ERROR('Cannot use --start-date with --full. Use one or the other.')
            )
            return
        
        # Parse since datetime if provided
        since_datetime = None
        if options['start_date']:
            try:
                since_datetime = timezone.datetime.fromisoformat(options['start_date'])
                if timezone.is_naive(since_datetime):
                    since_datetime = timezone.make_aware(since_datetime)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid datetime format: {options['start_date']}. "
                        "Use YYYY-MM-DD format"
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
