import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run all db_genius_* commands in order of model dependencies"

    def add_arguments(self, parser):
        """Add command arguments that will be passed to all sub-commands"""
        
        # Core sync options
        parser.add_argument(
            '--full',
            action='store_true',
            help='Force full sync instead of incremental (ignores last sync timestamp)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually updating the database'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Sync records modified since this timestamp (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for date range sync (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            help='Maximum number of records to process (for testing/debugging)'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging for detailed sync information'
        )
        
        # Legacy argument support (deprecated)
        parser.add_argument(
            '--force-overwrite',
            action='store_true',
            help='DEPRECATED: Use --full instead. Forces full sync ignoring timestamps.'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Set up logging
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        
        # Handle dry run
        if options.get('dry_run'):
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Handle legacy arguments
        if options.get('force_overwrite'):
            self.stdout.write(
                self.style.WARNING("⚠️  --force-overwrite is deprecated, use --full instead")
            )
            options['full'] = True
        
        # Prepare common options to pass to sub-commands
        common_options = {}
        for key in ['full', 'dry_run', 'since', 'start_date', 'end_date', 'max_records', 'debug']:
            if options.get(key) is not None:
                common_options[key] = options[key]
        
        commands = [
            # Independent tables (no foreign keys)
            {"name": "db_genius_division_groups", "options": {}},
            {"name": "db_genius_user_titles", "options": {}},
            {"name": "db_genius_services", "options": {}},
            {"name": "db_genius_appointment_types", "options": {}},
            {"name": "db_genius_appointment_outcome_types", "options": {}},
            {"name": "db_genius_appointment_outcomes", "options": {}},
            {"name": "db_genius_marketing_source_types", "options": {}},
            {"name": "db_genius_marketsharp_sources", "options": {}},
            {"name": "db_genius_marketsharp_marketing_source_maps", "options": {}},
            
            # Depends on division_groups
            {"name": "db_genius_divisions", "options": {}},
            
            # Depends on marketing_source_types
            {"name": "db_genius_marketing_sources", "options": {}},
            
            # Depends on divisions and user_titles
            {"name": "db_genius_users", "options": {}},
            
            # Depends on divisions
            {"name": "db_genius_prospects", "options": {}},
            {"name": "db_genius_leads", "options": {}},
            
            # Depends on prospects and marketing_sources
            {"name": "db_genius_prospect_sources", "options": {}},
            
            # Depends on prospects, prospect_sources, appointment_types, and appointment_outcomes
            {"name": "db_genius_appointments", "options": {}},
            
            # Depends on prospects, appointments, and services
            {"name": "db_genius_quotes", "options": {}},
            
            # Depends on appointments and services
            {"name": "db_genius_appointment_services", "options": {}},
        ]

        self.stdout.write(self.style.NOTICE('Starting full Genius DB import sequence...'))
        
        total_commands = len(commands)
        successful_commands = 0
        
        for i, cmd in enumerate(commands, 1):
            # Merge common options with command-specific options
            cmd_options = {**common_options, **cmd["options"]}
            
            self.stdout.write(self.style.NOTICE(f"[{i}/{total_commands}] Running {cmd['name']}..."))
            
            try:
                call_command(cmd['name'], **cmd_options)
                self.stdout.write(self.style.SUCCESS(f"✅ Completed {cmd['name']}"))
                successful_commands += 1
            except Exception as e:
                error_msg = f"❌ Error running {cmd['name']}: {e}"
                self.stdout.write(self.style.ERROR(error_msg))
                logger.error(f"db_genius_all: failed at {cmd['name']}: {e}")
                
                if not options.get('dry_run'):
                    self.stdout.write(self.style.ERROR("Stopping execution due to error. Use --dry-run to test without stopping."))
                    break
                else:
                    self.stdout.write(self.style.WARNING("Continuing with dry-run mode..."))

        if successful_commands == total_commands:
            self.stdout.write(self.style.SUCCESS('✅ All Genius DB commands executed successfully.'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  {successful_commands}/{total_commands} commands completed successfully.'))
