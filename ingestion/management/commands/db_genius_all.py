import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from ingestion.models.common import SyncHistory
from django.utils import timezone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run all db_genius_* commands in order of model dependencies following CRM sync guide standards"

    def add_arguments(self, parser):
        """Add universal command arguments following CRM sync guide standards"""
        
        # Universal Standard Flags (All CRM Systems) - From CRM Sync Guide
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging, detailed output, and test mode'
        )
        
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        
        parser.add_argument(
            '--skip-validation',
            action='store_true',
            help='Skip data validation steps'
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
            '--force',
            action='store_true',
            help='Completely replace existing records'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Manual sync start date (YYYY-MM-DD)'
        )
        
        # Additional useful flags
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        # Legacy argument support (deprecated but maintained for compatibility)
        parser.add_argument(
            '--since',
            type=str,
            help='DEPRECATED: Use --start-date instead. Sync records modified since this timestamp'
        )

    def handle(self, *args, **options):
        """Main command handler following CRM sync guide patterns with SyncHistory tracking"""
        
        # Create SyncHistory record following mandatory pattern
        sync_record = SyncHistory.objects.create(
            crm_source='genius',
            sync_type='all',
            status='running',
            start_time=timezone.now(),
            configuration=options
        )
        
        stats = {
            'sync_history_id': sync_record.id,
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0
        }
        
        try:
            # Set up logging
            if options.get('debug'):
                logging.getLogger().setLevel(logging.DEBUG)
                self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
            
            # Handle dry run
            if options.get('dry_run'):
                self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
            
            # Handle legacy arguments with deprecation warning
            if options.get('since'):
                self.stdout.write(
                    self.style.WARNING("⚠️  --since is deprecated, use --start-date instead")
                )
                if not options.get('start_date'):
                    options['start_date'] = options['since']
            
            # Prepare common options to pass to sub-commands (Universal Flags)
            # Only pass flags that most individual commands currently support
            common_options = {}
            supported_flags = [
                'debug', 'full', 'dry_run', 'max_records', 'force', 
                'start_date', 'end_date', 'since'
            ]
            
            for flag in supported_flags:
                if options.get(flag) is not None:
                    common_options[flag] = options[flag]
            
            # Note: batch_size and skip_validation will be added to individual commands in future updates
            unsupported_flags = []
            if options.get('batch_size', 100) != 100:
                unsupported_flags.append('--batch-size')
            if options.get('skip_validation'):
                unsupported_flags.append('--skip-validation')
                
            if unsupported_flags:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Note: {', '.join(unsupported_flags)} flags are not yet supported by individual db_genius commands"
                    )
                )

            # Complete list of ALL db_genius_* commands in proper dependency order
            # Following the CRM sync guide patterns for database-based sources
            commands = [
                # Level 1: Independent tables (no foreign keys)
                {"name": "db_genius_division_groups", "description": "Division organizational groups", "options": {}},
                {"name": "db_genius_user_titles", "description": "User title/role definitions", "options": {}},
                {"name": "db_genius_services", "description": "Service catalog definitions", "options": {}},
                {"name": "db_genius_appointment_types", "description": "Appointment type classifications", "options": {}},
                {"name": "db_genius_appointment_outcome_types", "description": "Appointment outcome classifications", "options": {}},
                {"name": "db_genius_appointment_outcomes", "description": "Appointment outcome records", "options": {}},
                {"name": "db_genius_marketing_source_types", "description": "Marketing source type definitions", "options": {}},
                {"name": "db_genius_marketsharp_sources", "description": "MarketSharp source integrations", "options": {}},
                {"name": "db_genius_marketsharp_marketing_source_maps", "description": "MarketSharp source mappings", "options": {}},
                {"name": "db_genius_job_statuses", "description": "Job status definitions", "options": {}},
                {"name": "db_genius_job_financings", "description": "Job financing options", "options": {}},
                {"name": "db_genius_job_change_order_types", "description": "Job change order type definitions", "options": {}},
                {"name": "db_genius_job_change_order_statuses", "description": "Job change order status definitions", "options": {}},
                {"name": "db_genius_job_change_order_reasons", "description": "Job change order reason codes", "options": {}},
                {"name": "db_genius_integration_field_definitions", "description": "Integration field definition templates", "options": {}},
                
                # Level 2: Depends on division_groups
                {"name": "db_genius_divisions", "description": "Organizational divisions", "options": {}},
                {"name": "db_genius_division_regions", "description": "Division regional mappings", "options": {}},
                
                # Level 3: Depends on marketing_source_types
                {"name": "db_genius_marketing_sources", "description": "Marketing source definitions", "options": {}},
                
                # Level 4: Depends on divisions and user_titles
                {"name": "db_genius_user_data", "description": "System users", "options": {}},
                
                # Level 5: Depends on users and divisions and integration_field_definitions
                {"name": "db_genius_user_associations", "description": "User organizational associations", "options": {}},
                {"name": "db_genius_prospects", "description": "Prospect records", "options": {}},
                {"name": "db_genius_leads", "description": "Lead records", "options": {}},
                {"name": "db_genius_integration_fields", "description": "Integration field values", "options": {}},
                
                # Level 6: Depends on prospects and marketing_sources
                {"name": "db_genius_prospect_sources", "description": "Prospect source attributions", "options": {}},
                
                # Level 7: Depends on prospects, appointment_types, and appointment_outcomes
                {"name": "db_genius_appointments", "description": "Appointment records", "options": {}},
                
                # Level 8: Depends on prospects, appointments, services, and job_statuses
                {"name": "db_genius_quotes", "description": "Quote records", "options": {}},
                {"name": "db_genius_jobs", "description": "Job records", "options": {}},
                
                # Level 9: Depends on appointments and services
                {"name": "db_genius_appointment_services", "description": "Appointment service associations", "options": {}},
                
                # Level 10: Depends on jobs and change order definitions
                {"name": "db_genius_job_change_order_items", "description": "Job change order line items", "options": {}},
                {"name": "db_genius_job_change_orders", "description": "Job change order records", "options": {}},
            ]

            self.stdout.write(self.style.NOTICE('🚀 Starting comprehensive Genius DB import sequence...'))
            self.stdout.write(self.style.NOTICE(f'📊 Total commands to execute: {len(commands)}'))
            
            if options.get('debug'):
                self.stdout.write(self.style.SUCCESS('🔧 Supported flags passed to all commands:'))
                for flag, value in common_options.items():
                    self.stdout.write(f"   --{flag.replace('_', '-')}: {value}")
                if unsupported_flags:
                    self.stdout.write(self.style.WARNING(f"   🚧 Unsupported flags (not passed): {', '.join(unsupported_flags)}"))
                self.stdout.write("")
            
            stats['total_commands'] = len(commands)
            
            for i, cmd in enumerate(commands, 1):
                # Merge common options with command-specific options
                cmd_options = {**common_options, **cmd["options"]}
                
                self.stdout.write(
                    self.style.NOTICE(f"[{i:2d}/{len(commands)}] 🔄 {cmd['name']}")
                )
                if options.get('debug'):
                    self.stdout.write(f"        📝 {cmd['description']}")
                
                try:
                    call_command(cmd['name'], **cmd_options)
                    self.stdout.write(self.style.SUCCESS(f"        ✅ Completed {cmd['name']}"))
                    stats['successful_commands'] += 1
                    
                except Exception as e:
                    error_msg = f"❌ Error running {cmd['name']}: {e}"
                    self.stdout.write(self.style.ERROR(f"        {error_msg}"))
                    logger.error(f"db_genius_all: failed at {cmd['name']}: {e}")
                    stats['failed_commands'] += 1
                    
                    if not options.get('dry_run'):
                        self.stdout.write(self.style.ERROR("🛑 Stopping execution due to error. Use --dry-run to test without stopping."))
                        break
                    else:
                        self.stdout.write(self.style.WARNING("⚠️  Continuing with dry-run mode..."))

            # Update SyncHistory with results
            if stats['successful_commands'] == stats['total_commands']:
                sync_record.status = 'success'
                self.stdout.write(self.style.SUCCESS('🎉 All Genius DB commands executed successfully!'))
            else:
                sync_record.status = 'partial' if stats['successful_commands'] > 0 else 'failed'
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Completed {stats["successful_commands"]}/{stats["total_commands"]} commands successfully.'
                    )
                )
            
            sync_record.end_time = timezone.now()
            sync_record.records_processed = stats['total_commands']
            sync_record.records_created = stats['successful_commands']  
            sync_record.records_failed = stats['failed_commands']
            sync_record.performance_metrics = {
                'duration_seconds': (sync_record.end_time - sync_record.start_time).total_seconds(),
                'commands_per_minute': stats['total_commands'] / ((sync_record.end_time - sync_record.start_time).total_seconds() / 60) if stats['total_commands'] > 0 else 0,
                'success_rate': (stats['successful_commands'] / stats['total_commands'] * 100) if stats['total_commands'] > 0 else 0
            }
            sync_record.save()

            # Summary output
            duration = (sync_record.end_time - sync_record.start_time).total_seconds()
            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("📈 EXECUTION SUMMARY"))
            self.stdout.write(f"   ⏱️  Duration: {duration:.1f} seconds")
            self.stdout.write(f"   ✅ Successful: {stats['successful_commands']}/{stats['total_commands']}")
            self.stdout.write(f"   ❌ Failed: {stats['failed_commands']}")
            self.stdout.write(f"   📊 Success Rate: {sync_record.performance_metrics['success_rate']:.1f}%")
            self.stdout.write(f"   🆔 SyncHistory ID: {sync_record.id}")
            
        except Exception as e:
            # Update SyncHistory with failure
            sync_record.status = 'failed'
            sync_record.end_time = timezone.now()
            sync_record.error_message = str(e)
            sync_record.records_failed = stats.get('failed_commands', 0)
            sync_record.save()
            
            logger.error(f"db_genius_all sync failed: {e}")
            self.stdout.write(self.style.ERROR(f"💥 Fatal error during sync execution: {e}"))
            raise
