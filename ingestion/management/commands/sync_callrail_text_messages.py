"""
Management command to sync CallRail text messages
"""
import logging
import asyncio
import os
from django.core.management.base import CommandError
from django.conf import settings
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.callrail.engines.text_messages import TextMessagesSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    help = 'Sync CallRail text messages data'
    crm_name = 'CallRail'
    entity_name = 'text_messages'

    def handle(self, *args, **options):
        """Handle the command execution"""
        try:
            # Check for API key
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError('CALLRAIL_API_KEY not configured in settings or environment')
            
            # Parse command line options
            dry_run = options['dry_run']
            full_sync = options['full']
            since_date = options.get('start_date')
            batch_size = options['batch_size']
            max_records = options['max_records']
            
            self.stdout.write(
                self.style.SUCCESS('Starting CallRail text messages sync')
            )
            
            if dry_run:
                self.stdout.write(self.style.WARNING('Running in DRY-RUN mode'))
            
            # Parse since_date date if provided
            since_date_date = None
            if since_date:
                from datetime import datetime
                try:
                    since_date_date = datetime.strptime(since_date, '%Y-%m-%d')
                except ValueError:
                    raise CommandError(f'Invalid date format: {since_date}. Use YYYY-MM-DD format.')
            
            # Run the sync
            result = asyncio.run(self._run_sync(
                dry_run=dry_run,
                full_sync=full_sync,
                since_date_date=since_date_date,
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
                dry_run=kwargs['dry_run'],
                batch_size=kwargs['batch_size']
            )
            
            # Prepare sync parameters - filter out boolean values for API
            sync_params = {}
            if kwargs.get('since_date_date'):
                sync_params['since_date_date'] = kwargs['since_date_date']
            if kwargs.get('max_records'):
                sync_params['max_records'] = kwargs['max_records']
            if kwargs.get('full_sync'):
                sync_params['force'] = True
            
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
