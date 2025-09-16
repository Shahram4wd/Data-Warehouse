"""
Management command to sync CallRail form submissions (enterprise pattern)
"""
import logging
import asyncio
import os
from django.core.management.base import CommandError
from django.conf import settings
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.callrail.engines.form_submissions import FormSubmissionsSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseSyncCommand):
    help = 'Sync CallRail form submissions data with standardized flags'
    crm_name = 'callrail'
    entity_name = 'form_submissions'

    def handle(self, *args, **options):
        try:
            # Standardized setup
            self.configure_logging(options)
            self.validate_arguments(options)

            # Check for API key
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError('CALLRAIL_API_KEY not configured in settings or environment')

            # Flags
            full_sync = options.get('full', False)
            force_overwrite = options.get('force', False)
            start_date = options.get('start_date')
            end_date = options.get('end_date')
            dry_run = options.get('dry_run', False)
            batch_size = options.get('batch_size', 100)
            max_records = options.get('max_records', 0)
            quiet = options.get('quiet', False)

            if not quiet:
                self.stdout.write(self.style.SUCCESS('Starting CallRail form submissions sync...'))
                if dry_run:
                    self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
                if start_date:
                    self.stdout.write(f'Start date: {start_date}')
                if end_date:
                    self.stdout.write(f'End date: {end_date}')
                if batch_size != 100:
                    self.stdout.write(f'Batch size: {batch_size}')

            # Prepare params (map start_date to since_date for engine)
            sync_params = {}
            if start_date:
                sync_params['since_date'] = start_date
            if end_date:
                sync_params['end_date'] = end_date

            # Run sync
            result = asyncio.run(
                self._run_sync(full_sync, force_overwrite, dry_run, max_records, batch_size, **sync_params)
            )

            # Output results
            self._output_results(result)

            if result.get('error'):
                raise CommandError(result['error'])

        except Exception as e:
            logger.error(f"CallRail form submissions sync failed: {e}")
            raise CommandError(f"Sync failed: {e}")

    async def _run_sync(self, full_sync, force_overwrite, dry_run, max_records, batch_size, **sync_params):
        engine = FormSubmissionsSyncEngine(dry_run=dry_run, batch_size=batch_size)
        return await engine.sync_form_submissions(
            full_sync=full_sync,
            force_overwrite=force_overwrite,
            max_records=max_records,
            **sync_params
        )

    def _output_results(self, result):
        success = not result.get('error')
        if success:
            self.stdout.write(self.style.SUCCESS('✓ CallRail form submissions sync completed successfully!'))
        else:
            self.stdout.write(self.style.ERROR('✗ CallRail form submissions sync failed'))

        self.stdout.write(
            f"Form submissions: {result.get('total_processed', 0)} processed "
            f"({result.get('total_created', 0)} created, {result.get('total_updated', 0)} updated, "
            f"{result.get('total_errors', 0)} failed)"
        )
        duration = result.get('duration', 0)
        try:
            duration_val = duration.total_seconds() if hasattr(duration, 'total_seconds') else float(duration)
        except Exception:
            duration_val = 0.0
        self.stdout.write(f"Duration: {duration_val:.2f} seconds")
