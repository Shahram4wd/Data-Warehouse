"""
Management command to sync CallRail companies, aligned with CRM sync guide
"""
import logging
import asyncio
import os
from django.core.management.base import CommandError
from django.conf import settings
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.callrail.engines.companies import CompaniesSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    help = 'Sync CallRail companies data with standardized flags'
    crm_name = 'callrail'
    entity_name = 'companies'

    def handle(self, *args, **options):
        try:
            # Validate arguments using BaseSyncCommand
            self.validate_arguments(options)

            # Check API key
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError('CALLRAIL_API_KEY not configured in settings or environment')

            # Standard flags
            full_sync = options['full']
            force_overwrite = options['force']
            start_date = options.get('start_date')
            end_date = options.get('end_date')
            dry_run = options.get('dry_run', False)
            batch_size = options.get('batch_size', 100)
            max_records = options.get('max_records', 0)
            quiet = options.get('quiet', False)

            if not quiet:
                self.stdout.write(self.style.SUCCESS('Starting CallRail companies sync...'))
                if dry_run:
                    self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
                if start_date:
                    self.stdout.write(f'Start date: {start_date}')
                if end_date:
                    self.stdout.write(f'End date: {end_date}')
                if batch_size != 100:
                    self.stdout.write(f'Batch size: {batch_size}')

            # Prepare params
            sync_params = {}
            if start_date:
                sync_params['start_date'] = start_date
            if end_date:
                sync_params['end_date'] = end_date

            # Run
            result = asyncio.run(
                self._run_sync(full_sync, force_overwrite, dry_run, max_records, batch_size, **sync_params)
            )

            # Output
            self.output_results(result)

            if not result.get('success', True):
                raise CommandError('CallRail companies sync failed')

        except Exception as e:
            logger.error(f'CallRail companies sync failed: {e}')
            raise CommandError(f'Sync failed: {e}')

    async def _run_sync(self, full_sync, force_overwrite, dry_run, max_records, batch_size, **sync_params):
        engine = CompaniesSyncEngine(dry_run=dry_run, batch_size=batch_size)
        return await engine.sync_companies(full_sync=full_sync, force_overwrite=force_overwrite, max_records=max_records, **sync_params)

    def output_results(self, result):
        success = result.get('success', True)
        if success:
            self.stdout.write(self.style.SUCCESS('✓ CallRail companies sync completed successfully!'))
        else:
            self.stdout.write(self.style.ERROR('✗ CallRail companies sync failed'))

        self.stdout.write(f"Companies: {result.get('total_processed', 0)} processed ({result.get('total_created', 0)} created, {result.get('total_updated', 0)} updated, {result.get('total_errors', 0)} failed)")
        duration = result.get('duration', 0)
        if hasattr(duration, 'total_seconds'):
            duration = duration.total_seconds()
        self.stdout.write(f"Duration: {duration:.2f} seconds")
