"""
New HubSpot all sync command using the unified architecture
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Run all HubSpot sync operations using the new unified architecture"""
    
    help = "Run all HubSpot sync operations using the new unified architecture"
    
    def add_arguments(self, parser):
        """Add arguments for the all sync command"""
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform full sync for all operations"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Show debug output"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run all syncs without saving data"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for all sync operations"
        )
        parser.add_argument(
            "--skip-associations",
            action="store_true",
            help="Skip association syncs"
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        start_time = timezone.now()
        
        # Define sync commands in order of execution
        sync_commands = [
            ('divisions', 'sync_hubspot_divisions'),
            ('contacts', 'sync_hubspot_contacts'),
            ('appointments', 'sync_hubspot_appointments'),
            ('deals', 'sync_hubspot_deals'),
            ('zipcodes', 'sync_hubspot_zipcodes'),
            ('check removed hubspot contacts', 'check_removed_hubspot_contacts'),
            ('check removed hubspot appointments', 'check_removed_hubspot_appointments'),
        ]
        
        # Add association commands if not skipped
        if not options.get('skip_associations'):
            sync_commands.extend([
                ('contact-deal associations', 'sync_hubspot_associations', 
                 ['--from-object', 'contacts', '--to-object', 'deals']),
                ('contact-appointment associations', 'sync_hubspot_associations', 
                 ['--from-object', 'contacts', '--to-object', '0-421']),
                ('division-contact associations', 'sync_hubspot_associations', 
                 ['--from-object', '2-37778609', '--to-object', 'contacts']),
            ])
        
        # Common arguments for all commands
        common_args = []
        if options.get('full'):
            common_args.append('--full')
        if options.get('debug'):
            common_args.append('--debug')
        if options.get('dry_run'):
            common_args.append('--dry-run')
        if options.get('batch_size'):
            common_args.extend(['--batch-size', str(options['batch_size'])])
        
        # Track results
        results = []
        total_processed = 0
        total_created = 0
        total_updated = 0
        total_failed = 0
        
        self.stdout.write(self.style.NOTICE('Starting comprehensive HubSpot sync using new architecture...'))
        
        # Execute each sync command
        for command_info in sync_commands:
            command_name = command_info[0]
            command_cmd = command_info[1]
            command_args = command_info[2] if len(command_info) > 2 else []
            
            self.stdout.write(self.style.NOTICE(f"\n🔄 Running {command_name} sync..."))
            
            try:
                # Build command arguments
                cmd_args = common_args + command_args
                
                # Execute the command
                call_command(command_cmd, *cmd_args)
                
                # Get the latest sync history for this command
                sync_type = command_name.split()[0]  # Get first word as sync type
                history = SyncHistory.objects.filter(
                    crm_source='hubspot',
                    sync_type=sync_type,
                    start_time__gte=start_time
                ).order_by('-start_time').first()
                
                if history:
                    results.append({
                        'command': command_name,
                        'status': history.status,
                        'processed': history.records_processed,
                        'created': history.records_created,
                        'updated': history.records_updated,
                        'failed': history.records_failed,
                        'duration': history.performance_metrics.get('duration_seconds', 0) if history.performance_metrics else 0
                    })
                    
                    # Accumulate totals
                    total_processed += history.records_processed
                    total_created += history.records_created
                    total_updated += history.records_updated
                    total_failed += history.records_failed
                
                self.stdout.write(self.style.SUCCESS(f"✓ Completed {command_name} sync"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error running {command_name} sync: {e}"))
                logger.error(f"sync_hubspot_all_new: failed at {command_name}: {e}")
                
                results.append({
                    'command': command_name,
                    'status': 'failed',
                    'error': str(e),
                    'processed': 0,
                    'created': 0,
                    'updated': 0,
                    'failed': 0,
                    'duration': 0
                })
                
                # Continue with other commands rather than break
                continue
        
        # Generate final report
        self.generate_final_report(results, total_processed, total_created, total_updated, total_failed, start_time)
    
    def generate_final_report(self, results, total_processed, total_created, total_updated, total_failed, start_time):
        """Generate and display the final sync report"""
        end_time = timezone.now()
        total_duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('📊 HUBSPOT SYNC COMPLETE - FINAL REPORT'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        # Summary
        self.stdout.write(f"\n🕒 Total Duration: {total_duration:.2f} seconds")
        self.stdout.write(f"📈 Total Records Processed: {total_processed}")
        self.stdout.write(f"➕ Total Records Created: {total_created}")
        self.stdout.write(f"✏️  Total Records Updated: {total_updated}")
        self.stdout.write(f"❌ Total Records Failed: {total_failed}")
        
        if total_duration > 0:
            rate = total_processed / total_duration
            self.stdout.write(f"⚡ Average Rate: {rate:.2f} records/second")
        
        # Individual command results
        self.stdout.write(f"\n📋 Individual Command Results:")
        self.stdout.write("-" * 60)
        
        for result in results:
            status_icon = "✓" if result['status'] == 'success' else "✗"
            status_style = self.style.SUCCESS if result['status'] == 'success' else self.style.ERROR
            
            self.stdout.write(status_style(
                f"{status_icon} {result['command']:30} | "
                f"Processed: {result['processed']:6} | "
                f"Created: {result['created']:6} | "
                f"Updated: {result['updated']:6} | "
                f"Failed: {result['failed']:6} | "
                f"Duration: {result['duration']:6.2f}s"
            ))
            
            if result.get('error'):
                self.stdout.write(f"    Error: {result['error']}")
        
        # Success/failure summary
        successful_commands = len([r for r in results if r['status'] == 'success'])
        failed_commands = len([r for r in results if r['status'] == 'failed'])
        
        self.stdout.write(f"\n📊 Commands Summary:")
        self.stdout.write(f"   ✓ Successful: {successful_commands}")
        self.stdout.write(f"   ✗ Failed: {failed_commands}")
        
        if failed_commands == 0:
            self.stdout.write(self.style.SUCCESS("\n🎉 All HubSpot sync operations completed successfully!"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {failed_commands} command(s) failed. Check logs for details."))
        
        self.stdout.write(self.style.SUCCESS('='*60))
