"""
SalesRabbit all sync command using the unified architecture
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Run all SalesRabbit sync operations using the new unified architecture"""
    
    help = """Run all SalesRabbit sync operations using the unified architecture.
    
This command will sync all SalesRabbit entities in the correct order to maintain
data integrity and relationships."""

    def add_arguments(self, parser):
        """Add arguments for all sync command"""
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental for all entities"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable verbose logging, detailed output, and test mode"
        )
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Skip data validation steps"
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
            help="Maximum number of records to process per entity (0 for unlimited)"
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Sync records modified after this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force overwrite all existing records, ignoring timestamps and sync history"
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress non-error output"
        )
        parser.add_argument(
            "--skip-leads",
            action="store_true",
            help="Skip syncing leads"
        )
        parser.add_argument(
            "--skip-users",
            action="store_true",
            help="Skip syncing users"
        )

    def handle(self, *args, **options):
        """Main command handler"""
        start_time = timezone.now()
        
        # Set logging level
        if options.get("debug"):
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.stdout.write(self.style.SUCCESS("Starting complete SalesRabbit data sync..."))
        
        # Prepare common arguments
        common_args = []
        common_kwargs = {}
        
        # Pass through all relevant options
        for option in ['full', 'debug', 'dry_run', 'batch_size', 'max_records', 'since', 'force_overwrite']:
            if options.get(option):
                if option == 'dry_run':
                    common_kwargs['dry-run'] = True
                elif option == 'force_overwrite':
                    common_kwargs['force'] = True
                else:
                    common_kwargs[option.replace('_', '-')] = options[option]
        
        sync_results = {}
        
        # 1. Sync Leads (currently the main entity)
        if not options.get('skip_leads'):
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING SALESRABBIT LEADS")
            self.stdout.write("="*60)
            try:
                call_command('sync_salesrabbit_leads', *common_args, **common_kwargs)
                sync_results['leads'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Leads sync completed"))
            except Exception as e:
                sync_results['leads'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Leads sync failed: {str(e)}"))
        
        # 2. Sync Users (representatives/staff)
        if not options.get('skip_users'):
            self.stdout.write("\n" + "="*60)
            self.stdout.write("👥 SYNCING SALESRABBIT USERS")
            self.stdout.write("="*60)
            try:
                call_command('sync_salesrabbit_users', *common_args, **common_kwargs)
                sync_results['users'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Users sync completed"))
            except Exception as e:
                sync_results['users'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Users sync failed: {str(e)}"))
        
        # Future entities can be added here:
        # - Campaigns
        # - Custom fields
        # - Activity logs
        
        # Summary report
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📊 SALESRABBIT SYNC SUMMARY")
        self.stdout.write("="*60)
        
        for entity, status in sync_results.items():
            if 'SUCCESS' in status:
                self.stdout.write(self.style.SUCCESS(f"✓ {entity.upper()}: {status}"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ {entity.upper()}: {status}"))
        
        self.stdout.write(f"\nTotal sync duration: {duration:.2f} seconds")
        
        # Check overall success
        failed_syncs = [entity for entity, status in sync_results.items() if 'FAILED' in status]
        
        if failed_syncs:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  Some syncs failed: {', '.join(failed_syncs)}"
            ))
            self.stdout.write("Check the logs above for detailed error information.")
        else:
            self.stdout.write(self.style.SUCCESS(
                "\n🎉 All SalesRabbit syncs completed successfully!"
            ))
        
        # Log sync completion to database
        try:
            SyncHistory.objects.create(
                crm_source='salesrabbit',
                sync_type='all_entities',
                start_time=start_time,
                end_time=end_time,
                status='success' if not failed_syncs else 'partial',
                records_processed=0,  # Will be sum of individual syncs
                records_created=0,    # Will be sum of individual syncs  
                records_updated=0,    # Will be sum of individual syncs
                records_failed=len(failed_syncs),
                error_message=f"Failed entities: {', '.join(failed_syncs)}" if failed_syncs else None,
                configuration=options,
                performance_metrics={'duration_seconds': duration}
            )
        except Exception as e:
            logger.warning(f"Failed to log sync completion: {e}")
