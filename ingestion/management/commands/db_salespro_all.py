"""
Unified SalesPro sync command for all entities
Following import_refactoring.md guidelines
"""
import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime

# Import all sync engines
from ingestion.management.commands.db_salespro_creditapplications import SalesProCreditApplicationSyncEngine
from ingestion.management.commands.db_salespro_customers import SalesProCustomerSyncEngine
from ingestion.management.commands.db_salespro_estimates import SalesProEstimateSyncEngine
from ingestion.management.commands.db_salespro_leadresults import SalesProLeadResultSyncEngine
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Sync all SalesPro entities from AWS Athena database"""
    
    help = "Sync all SalesPro entities from AWS Athena database"
    
    # Define sync order (considering dependencies)
    SYNC_ENGINES = [
        ('customers', SalesProCustomerSyncEngine),
        ('creditapplications', SalesProCreditApplicationSyncEngine),
        ('estimates', SalesProEstimateSyncEngine),
        ('leadresults', SalesProLeadResultSyncEngine),
    ]
    
    def add_arguments(self, parser):
        """Add command arguments"""
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Show debug output"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run sync without saving data to database"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of records to process in each batch"
        )
        parser.add_argument(
            "--max-records",
            type=int,
            default=0,
            help="Maximum number of records to sync per entity (0 for unlimited)"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Sync records modified since this date (YYYY-MM-DD format)"
        )

        parser.add_argument(
            "--parallel",
            action="store_true",
            help="Run entity syncs in parallel (faster but uses more resources)"
        )
        
    def handle(self, *args, **options):
        """Handle the unified sync command"""
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            
        self.stdout.write("Starting unified SalesPro sync from AWS Athena...")
        
        try:
            # Parse since date if provided
            since_date = None
            if options.get('since'):
                try:
                    since_date = datetime.strptime(options['since'], '%Y-%m-%d')
                    since_date = timezone.make_aware(since_date)
                except ValueError:
                    raise CommandError(f"Invalid date format: {options['since']}. Use YYYY-MM-DD")
            
            # Determine which entities to sync
            entities_to_sync = self._get_entities_to_sync(options.get('entities'))
            
            # Run sync
            results = asyncio.run(self._run_all_syncs(
                entities_to_sync=entities_to_sync,
                since_date=since_date,
                dry_run=options['dry_run'],
                batch_size=options['batch_size'],
                max_records=options['max_records'],
                parallel=options['parallel'],
                full_sync=options['full']
            ))
            
            # Report overall results
            self._report_overall_results(results)
            
        except Exception as e:
            logger.error(f"Unified sync failed: {e}")
            self.stdout.write(
                self.style.ERROR(f"❌ SalesPro unified sync failed: {e}")
            )
            raise CommandError(str(e))
            
    def _get_entities_to_sync(self, requested_entities):
        """Get the list of entities to sync"""
        if requested_entities:
            # Validate requested entities
            available_entities = {name for name, _ in self.SYNC_ENGINES}
            invalid_entities = set(requested_entities) - available_entities
            if invalid_entities:
                raise CommandError(f"Invalid entities: {', '.join(invalid_entities)}")
            
            # Filter sync engines
            return [(name, engine_class) for name, engine_class in self.SYNC_ENGINES 
                   if name in requested_entities]
        else:
            # Sync all entities
            return self.SYNC_ENGINES
            
    async def _run_all_syncs(self, **kwargs):
        """Run all entity syncs"""
        entities_to_sync = kwargs['entities_to_sync']
        parallel = kwargs.get('parallel', False)
        
        if parallel:
            # Run syncs in parallel
            self.stdout.write("Running syncs in parallel...")
            tasks = []
            for entity_name, engine_class in entities_to_sync:
                task = self._run_entity_sync(entity_name, engine_class, **kwargs)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return dict(zip([name for name, _ in entities_to_sync], results))
        else:
            # Run syncs sequentially
            self.stdout.write("Running syncs sequentially...")
            results = {}
            for entity_name, engine_class in entities_to_sync:
                try:
                    result = await self._run_entity_sync(entity_name, engine_class, **kwargs)
                    results[entity_name] = result
                except Exception as e:
                    results[entity_name] = e
                    logger.error(f"Error syncing {entity_name}: {e}")
                    
            return results
            
    async def _run_entity_sync(self, entity_name, engine_class, **kwargs):
        """Run sync for a single entity"""
        self.stdout.write(f"Starting {entity_name} sync...")
        
        try:
            # Create sync engine
            engine = engine_class(
                batch_size=kwargs['batch_size'],
                dry_run=kwargs['dry_run']
            )
            
            # Run sync - ensure manual since_date is preserved
            sync_kwargs = {
                'max_records': kwargs.get('max_records', 0),
                'full_sync': kwargs.get('full_sync', False)
            }
            
            # Only add since_date if it was manually provided (from --since parameter)
            # This allows each engine's run_sync method to handle automatic incremental logic
            if kwargs.get('since_date') is not None:
                sync_kwargs['since_date'] = kwargs.get('since_date')
            
            history = await engine.run_sync(**sync_kwargs)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ {entity_name} sync completed: "
                                 f"{history.records_processed} processed, "
                                 f"{history.records_created} created, "
                                 f"{history.records_updated} updated, "
                                 f"{history.records_failed} failed")
            )
            
            return history
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ {entity_name} sync failed: {e}")
            )
            raise
            
    def _report_overall_results(self, results):
        """Report overall sync results"""
        total_processed = 0
        total_created = 0
        total_updated = 0
        total_failed = 0
        successful_syncs = 0
        failed_syncs = 0
        
        for entity_name, result in results.items():
            if isinstance(result, Exception):
                failed_syncs += 1
            else:
                successful_syncs += 1
                total_processed += result.records_processed
                total_created += result.records_created
                total_updated += result.records_updated
                total_failed += result.records_failed
                
        self.stdout.write("\n" + "="*60)
        self.stdout.write("OVERALL SYNC RESULTS")
        self.stdout.write("="*60)
        self.stdout.write(f"Successful entities: {successful_syncs}")
        self.stdout.write(f"Failed entities: {failed_syncs}")
        self.stdout.write(f"Total records processed: {total_processed}")
        self.stdout.write(f"Total records created: {total_created}")
        self.stdout.write(f"Total records updated: {total_updated}")
        self.stdout.write(f"Total records failed: {total_failed}")
        
        if failed_syncs == 0:
            self.stdout.write(self.style.SUCCESS("🎉 All SalesPro entities synced successfully!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ {failed_syncs} entities failed to sync"))
