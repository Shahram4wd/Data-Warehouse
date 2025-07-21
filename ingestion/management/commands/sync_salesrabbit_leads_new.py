"""
Refactored SalesRabbit sync command following framework standards
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from ingestion.sync.salesrabbit.engines.leads import SalesRabbitLeadSyncEngine

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Refactored command following framework standards"""
    help = 'Sync leads from SalesRabbit using four-layer architecture'
    
    def add_arguments(self, parser):
        """Framework-standard command arguments"""
        parser.add_argument(
            '--force-full',
            action='store_true',
            help='Force full sync instead of incremental'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for bulk operations'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform dry run without saving data'
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test API connection and exit'
        )
    
    def handle(self, *args, **options):
        """Main command handler using async engine"""
        try:
            # Test connection if requested
            if options.get('test_connection'):
                self.test_api_connection()
                return
            
            # Create sync engine
            engine = SalesRabbitLeadSyncEngine(
                batch_size=options.get('batch_size', 500),
                dry_run=options.get('dry_run', False)
            )
            
            # Run sync using framework patterns
            self.stdout.write("Starting SalesRabbit leads sync...")
            
            results = asyncio.run(
                engine.run_sync(
                    force_full=options.get('force_full', False)
                )
            )
            
            # Output results in framework-standard format
            self.stdout.write(
                self.style.SUCCESS(
                    f"SalesRabbit sync completed successfully: "
                    f"{results['created']} created, "
                    f"{results['updated']} updated, "
                    f"{results['failed']} failed"
                )
            )
            
            # Show performance summary
            if results['created'] > 0 or results['updated'] > 0:
                total_processed = results['created'] + results['updated']
                self.stdout.write(f"Total records processed: {total_processed}")
            
            if results['failed'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Warning: {results['failed']} records failed to process"
                    )
                )
        
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("Sync interrupted by user")
            )
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f"Sync failed: {e}")
            )
            raise
    
    def test_api_connection(self):
        """Test API connection"""
        self.stdout.write("Testing SalesRabbit API connection...")
        
        try:
            engine = SalesRabbitLeadSyncEngine()
            success = asyncio.run(engine.test_connection())
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS("✓ API connection test successful")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("✗ API connection test failed")
                )
        except Exception as e:
            logger.error(f"Connection test failed: {e}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f"✗ API connection test failed: {e}")
            )
