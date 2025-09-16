"""
Management command to sync CallRail accounts
"""
import logging
import asyncio
import os
from django.core.management.base import CommandError
from django.conf import settings
from django.utils import timezone
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.callrail.engines.accounts import AccountsSyncEngine
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    help = 'Sync CallRail accounts data with standardized flags'

    def add_arguments(self, parser):
        # Add standardized flags from BaseSyncCommand
        super().add_arguments(parser)
        
        # No additional CallRail-specific flags needed for accounts

    def handle(self, *args, **options):
        """Handle the command execution"""
        sync_record = None
        try:
            # Check if CallRail API key is configured
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError("CALLRAIL_API_KEY not configured in settings or environment")
            
            # Parse standard CRM sync arguments
            dry_run = options['dry_run']
            full_sync = options['full']
            # Standard flag naming: --force
            force_overwrite = options.get('force', False)
            since = options.get('since')
            batch_size = options['batch_size']
            max_records = options['max_records']
            debug = options.get('debug', False)
            
            # Create SyncHistory record for tracking
            sync_record = SyncHistory.objects.create(
                crm_source='callrail',
                sync_type='accounts',
                status='running',
                start_time=timezone.now(),
                configuration={
                    'command': 'sync_callrail_accounts',
                    'parameters': {
                        'dry_run': dry_run,
                        'full_sync': full_sync,
                        'force_overwrite': force_overwrite,
                        'since': since,
                        'batch_size': batch_size,
                        'max_records': max_records,
                        'debug': debug
                    },
                    'execution_method': 'management_command'
                }
            )
            
            # Set up debug logging if requested
            if debug:
                logging.getLogger('ingestion.sync.callrail').setLevel(logging.DEBUG)
            
            self.stdout.write(
                self.style.SUCCESS(f'Starting CallRail accounts sync (Sync ID: {sync_record.id})')
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
                # Update sync record on success
                sync_record.status = 'success'
                sync_record.end_time = timezone.now()
                sync_record.records_processed = result.get('records_processed', 0)
                sync_record.records_created = result.get('records_created', 0)
                sync_record.records_updated = result.get('records_updated', 0)
                sync_record.records_failed = len(result.get('errors', []))
                sync_record.performance_metrics = {
                    'total_fetched': result.get('records_fetched', 0),
                    'execution_method': 'management_command'
                }
                sync_record.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Sync completed successfully! (Sync ID: {sync_record.id})\n"
                        f"Records fetched: {result.get('records_fetched', 0)}\n"
                        f"Records processed: {result.get('records_processed', 0)}\n"
                        f"Records created: {result.get('records_created', 0)}\n"
                        f"Records updated: {result.get('records_updated', 0)}\n"
                        f"Errors: {len(result.get('errors', []))}"
                    )
                )
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                
                # Update sync record on failure
                if sync_record:
                    sync_record.status = 'failed'
                    sync_record.end_time = timezone.now()
                    sync_record.error_message = error_msg
                    sync_record.save()
                
                self.stdout.write(
                    self.style.ERROR(f"Sync failed (Sync ID: {sync_record.id if sync_record else 'N/A'}): {error_msg}")
                )
                raise CommandError(f"Sync failed: {error_msg}")
                
        except Exception as e:
            # Update sync record on exception
            if sync_record:
                sync_record.status = 'failed'
                sync_record.end_time = timezone.now()
                sync_record.error_message = str(e)
                sync_record.save()
            
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
                # Engine expects 'force' parameter
                'force': kwargs['force_overwrite'],
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
