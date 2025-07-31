"""
Main management command to sync all CallRail data
"""
import logging
import asyncio
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.sync.callrail.engines.accounts import AccountsSyncEngine
from ingestion.sync.callrail.engines.companies import CompaniesSyncEngine
from ingestion.sync.callrail.engines.calls import CallsSyncEngine
from ingestion.sync.callrail.engines.trackers import TrackersSyncEngine
from ingestion.sync.callrail.engines.form_submissions import FormSubmissionsSyncEngine
from ingestion.sync.callrail.engines.text_messages import TextMessagesSyncEngine
from ingestion.sync.callrail.engines.tags import TagsSyncEngine
from ingestion.sync.callrail.engines.users import UsersSyncEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync all CallRail data (accounts, companies, calls, trackers, form_submissions, text_messages, tags, users)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no database writes)'
        )
        parser.add_argument(
            '--full-sync',
            action='store_true',
            help='Perform full sync instead of delta sync'
        )
        parser.add_argument(
            '--entities',
            type=str,
            nargs='+',
            default=['accounts', 'companies', 'calls', 'trackers', 'form_submissions', 'text_messages', 'tags', 'users'],
            choices=['accounts', 'companies', 'calls', 'trackers', 'form_submissions', 'text_messages', 'tags', 'users'],
            help='Entities to sync (default: all)'
        )
        parser.add_argument(
            '--company-id',
            type=str,
            help='Optional company ID to filter trackers and calls'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for calls sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--parallel',
            action='store_true',
            help='Run entity syncs in parallel (experimental)'
        )
    
    def handle(self, *args, **options):
        """Handle the management command"""
        try:
            # Check if CallRail API key is configured
            api_key = getattr(settings, 'CALLRAIL_API_KEY', None) or os.getenv('CALLRAIL_API_KEY')
            if not api_key:
                raise CommandError("CALLRAIL_API_KEY not configured in settings or environment")
            
            full_sync = options['full_sync']
            entities = options['entities']
            company_id = options.get('company_id')
            start_date = options.get('start_date')
            end_date = options.get('end_date')
            dry_run = options.get('dry_run', False)
            parallel = options.get('parallel', False)
            
            self.stdout.write(
                self.style.SUCCESS('Starting CallRail sync')
            )
            self.stdout.write(f'Entities to sync: {", ".join(entities)}')
            
            if company_id:
                self.stdout.write(f'Filtering by company: {company_id}')
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No data will be saved')
                )
            
            # Run the sync
            if parallel:
                sync_results = asyncio.run(
                    self._run_parallel_sync(
                        entities, full_sync, dry_run, 
                        company_id, start_date, end_date
                    )
                )
            else:
                sync_results = asyncio.run(
                    self._run_sequential_sync(
                        entities, full_sync, dry_run,
                        company_id, start_date, end_date
                    )
                )
            
            # Display consolidated results
            self._display_consolidated_results(sync_results)
            
        except Exception as e:
            logger.error(f"CallRail sync failed: {e}")
            raise CommandError(f"Sync failed: {e}")
    
    async def _run_sequential_sync(
        self, entities, full_sync, dry_run, 
        company_id, start_date, end_date
    ):
        """Run entity syncs sequentially"""
        sync_results = {}
        
        # Sync companies first (dependencies for other entities)
        if 'companies' in entities:
            self.stdout.write(
                self.style.HTTP_INFO('\n📋 Starting companies sync...')
            )
            try:
                companies_engine = CompaniesSyncEngine()
                companies_result = await companies_engine.sync_companies(
                    full_sync=full_sync
                )
                sync_results['companies'] = companies_result
                self._display_entity_summary('companies', companies_result)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Companies sync failed: {e}')
                )
                sync_results['companies'] = {'error': str(e)}
        
        # Sync trackers second
        if 'trackers' in entities:
            self.stdout.write(
                self.style.HTTP_INFO('\n📞 Starting trackers sync...')
            )
            try:
                trackers_engine = TrackersSyncEngine()
                trackers_result = await trackers_engine.sync_trackers(
                    company_id=company_id,
                    full_sync=full_sync
                )
                sync_results['trackers'] = trackers_result
                self._display_entity_summary('trackers', trackers_result)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Trackers sync failed: {e}')
                )
                sync_results['trackers'] = {'error': str(e)}
        
        # Sync calls last (largest dataset)
        if 'calls' in entities:
            self.stdout.write(
                self.style.HTTP_INFO('\n☎️ Starting calls sync...')
            )
            try:
                calls_engine = CallsSyncEngine()
                
                # Prepare calls sync parameters
                calls_params = {}
                if company_id:
                    calls_params['company_id'] = company_id
                if start_date:
                    calls_params['start_date'] = start_date
                if end_date:
                    calls_params['end_date'] = end_date
                
                calls_result = await calls_engine.sync_calls(
                    full_sync=full_sync,
                    **calls_params
                )
                sync_results['calls'] = calls_result
                self._display_entity_summary('calls', calls_result)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Calls sync failed: {e}')
                )
                sync_results['calls'] = {'error': str(e)}
        
        return sync_results
    
    async def _run_parallel_sync(
        self, entities, full_sync, dry_run,
        company_id, start_date, end_date
    ):
        """Run entity syncs in parallel (experimental)"""
        self.stdout.write(
            self.style.WARNING('⚠️ Parallel sync is experimental')
        )
        
        tasks = []
        
        if 'companies' in entities:
            companies_engine = CompaniesSyncEngine()
            tasks.append(('companies', companies_engine.sync_companies(
                full_sync=full_sync
            )))
        
        if 'trackers' in entities:
            trackers_engine = TrackersSyncEngine()
            tasks.append(('trackers', trackers_engine.sync_trackers(
                company_id=company_id,
                full_sync=full_sync
            )))
        
        if 'calls' in entities:
            calls_engine = CallsSyncEngine()
            calls_params = {}
            if company_id:
                calls_params['company_id'] = company_id
            if start_date:
                calls_params['start_date'] = start_date
            if end_date:
                calls_params['end_date'] = end_date
            
            tasks.append(('calls', calls_engine.sync_calls(
                full_sync=full_sync,
                **calls_params
            )))
        
        # Run all tasks in parallel
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        
        # Map results back to entities
        sync_results = {}
        for i, (entity_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                sync_results[entity_name] = {'error': str(result)}
            else:
                sync_results[entity_name] = result
        
        return sync_results
    
    def _display_entity_summary(self, entity_name, result):
        """Display a brief summary for an entity sync"""
        if 'error' in result:
            self.stdout.write(
                self.style.ERROR(f'❌ {entity_name.title()} sync failed')
            )
            return
        
        created = result.get('total_created', 0)
        updated = result.get('total_updated', 0)
        errors = result.get('total_errors', 0)
        duration = result.get('duration', 0)
        
        status_icon = '✅' if errors == 0 else '⚠️'
        self.stdout.write(
            f'{status_icon} {entity_name.title()}: +{created} created, ~{updated} updated, '
            f'{errors} errors ({duration:.1f}s)'
        )
    
    def _display_consolidated_results(self, sync_results):
        """Display consolidated results for all entities"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("📊 CONSOLIDATED SYNC RESULTS"))
        self.stdout.write("="*60)
        
        total_created = 0
        total_updated = 0
        total_errors = 0
        total_duration = 0
        
        for entity_name, result in sync_results.items():
            if 'error' in result:
                self.stdout.write(
                    self.style.ERROR(f"❌ {entity_name.title()}: {result['error']}")
                )
                continue
            
            created = result.get('total_created', 0)
            updated = result.get('total_updated', 0)
            errors = result.get('total_errors', 0)
            duration = result.get('duration', 0)
            
            total_created += created
            total_updated += updated
            total_errors += errors
            total_duration += duration
            
            status = '✅' if errors == 0 else '⚠️'
            self.stdout.write(
                f"{status} {entity_name.title()}: +{created} created, ~{updated} updated, "
                f"{errors} errors ({duration:.1f}s)"
            )
        
        self.stdout.write("-" * 60)
        self.stdout.write(
            f"📈 TOTALS: +{total_created} created, ~{total_updated} updated, "
            f"{total_errors} errors ({total_duration:.1f}s)"
        )
        self.stdout.write("="*60)
        
        if total_errors == 0:
            self.stdout.write(
                self.style.SUCCESS("🎉 All syncs completed successfully!")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠️ Syncs completed with {total_errors} total errors")
            )
