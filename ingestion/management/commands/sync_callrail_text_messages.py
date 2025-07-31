"""
Management command to sync CallRail text messages
"""
import logging
import asyncio
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.sync.callrail.engines.text_messages import TextMessagesSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync CallRail text messages data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=str,
            required=True,
            help='CallRail account ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no database writes)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Sync data since date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for API requests'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Maximum records to sync (0 = unlimited)'
        )

    def handle(self, *args, **options):
        """Handle the command execution"""
        try:
            # Parse command line options
            account_id = options['account_id']
            dry_run = options['dry_run']
            force = options['force']
            since = options.get('since')
            batch_size = options['batch_size']
            max_records = options['max_records']
            
            self.stdout.write(
                self.style.SUCCESS(f'Starting CallRail text messages sync for account: {account_id}')
            )
            
            if dry_run:
                self.stdout.write(self.style.WARNING('Running in DRY-RUN mode'))
            
            # Parse since date if provided
            since_date = None
            if since:
                from datetime import datetime
                try:
                    since_date = datetime.strptime(since, '%Y-%m-%d')
                except ValueError:
                    raise CommandError(f'Invalid date format: {since}. Use YYYY-MM-DD format.')
            
            # Run the sync
            result = asyncio.run(self._run_sync(
                account_id=account_id,
                dry_run=dry_run,
                force=force,
                since_date=since_date,
                batch_size=batch_size,
                max_records=max_records
            ))
            
            # Display results
            if result.get('success', False):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Sync completed successfully!\n"
                        f"Records fetched: {result.get('records_fetched', 0)}\n"
                        f"Records processed: {result.get('records_processed', 0)}\n"
                        f"Records created: {result.get('records_created', 0)}\n"
                        f"Records updated: {result.get('records_updated', 0)}\n"
                        f"Errors: {len(result.get('errors', []))}"
                    )
                )
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                self.stdout.write(
                    self.style.ERROR(f"Sync failed: {error_msg}")
                )
                raise CommandError(f"Sync failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise CommandError(f"Command execution failed: {e}")

    async def _run_sync(self, **kwargs):
        """Run the actual sync operation"""
        try:
            # Initialize the sync engine
            engine = TextMessagesSyncEngine(
                account_id=kwargs['account_id'],
                dry_run=kwargs['dry_run'],
                batch_size=kwargs['batch_size']
            )
            
            # Prepare sync parameters
            sync_params = {
                'force': kwargs['force'],
                'since_date': kwargs['since_date'],
                'max_records': kwargs['max_records']
            }
            
            # Run the sync
            result = await engine.sync_text_messages(**sync_params)
            
            return {
                'success': True,
                'records_fetched': result.get('total_fetched', 0),
                'records_processed': result.get('total_processed', 0),
                'records_created': result.get('total_created', 0),
                'records_updated': result.get('total_updated', 0),
                'errors': result.get('errors', [])
            }
            
        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'records_processed': 0
            }
