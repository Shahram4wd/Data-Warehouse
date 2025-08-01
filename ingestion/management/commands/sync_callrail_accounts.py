"""
Management command to sync CallRail accounts
"""
import logging
import asyncio
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.sync.callrail.engines.accounts import AccountsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync CallRail accounts data'

    def add_arguments(self, parser):
        # Standard CRM sync flags according to sync_crm_guide.md
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force-overwrite',
            action='store_true',
            help='Completely replace existing records'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Records per API batch (default: 100)'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging'
        )

    def handle(self, *args, **options):
        """Handle the command execution"""
        try:
            # Check if CallRail API key is configured
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError("CALLRAIL_API_KEY not configured in settings or environment")
            
            # Parse standard CRM sync arguments
            dry_run = options['dry_run']
            full_sync = options['full']
            force_overwrite = options['force_overwrite']
            since = options.get('since')
            batch_size = options['batch_size']
            max_records = options['max_records']
            debug = options.get('debug', False)
            
            # Set up debug logging if requested
            if debug:
                logging.getLogger('ingestion.sync.callrail').setLevel(logging.DEBUG)
            
            self.stdout.write(
                self.style.SUCCESS('Starting CallRail accounts sync')
            )
            
            if dry_run:
                self.stdout.write(self.style.WARNING('Running in DRY-RUN mode'))
            
            # Display sync mode
            if force_overwrite:
                self.stdout.write(self.style.WARNING('FORCE OVERWRITE MODE - Existing records will be replaced'))
            elif full_sync:
                self.stdout.write('Full sync mode (ignoring last sync timestamp)')
            else:
                self.stdout.write('Delta sync mode (incremental update)')
            
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
                dry_run=dry_run,
                full_sync=full_sync,
                force_overwrite=force_overwrite,
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
            engine = AccountsSyncEngine(
                dry_run=kwargs['dry_run'],
                batch_size=kwargs['batch_size']
            )
            
            # Prepare sync parameters
            sync_params = {
                'full_sync': kwargs['full_sync'],
                'force_overwrite': kwargs['force_overwrite'],
                'since_date': kwargs['since_date'],
                'max_records': kwargs['max_records']
            }
            
            # Run the sync
            result = await engine.sync_accounts(**sync_params)
            
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
