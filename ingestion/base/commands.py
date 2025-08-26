"""
Base Management Commands for CRM Sync Operations

Enterprise-grade base classes following crm_sync_guide.md patterns.
Provides standardized argument handling, SyncHistory integration, and error handling.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger(__name__)

class BaseSyncCommand(BaseCommand, ABC):
    """
    Base class for all CRM sync management commands
    
    Implements standardized patterns from crm_sync_guide.md:
    - Standard command-line flags and options
    - Consistent error handling and logging
    - SyncHistory integration patterns
    - Enterprise-grade validation and reporting
    """
    
    def add_arguments(self, parser):
        """
        Add standard CRM sync arguments following crm_sync_guide.md
        
        Standard Flags (All CRM Syncs) - SIMPLIFIED AND STANDARDIZED:
        - --full: Perform full sync (ignore last sync timestamp)
        - --force: Force overwrite existing records (standardized from --force-overwrite)
        - --start-date: Manual sync start date (YYYY-MM-DD) - replaces deprecated --since
        - --end-date: Manual sync end date (YYYY-MM-DD)
        - --dry-run: Test run without database writes
        - --batch-size: Records per API batch
        - --max-records: Limit total records (0 = unlimited)
        - --debug: Enable verbose logging, detailed output, and test mode (consolidated)
        - --skip-validation: Skip data validation steps
        - --quiet: Suppress non-error output
        """
        # Core sync strategy flags
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite existing records'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='Manual sync end date (YYYY-MM-DD format)'
        )
        
        # Execution control flags
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
        
        # Debugging and output control
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging, detailed output, and test mode'
        )
        
        parser.add_argument(
            '--skip-validation',
            action='store_true',
            help='Skip data validation steps'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress non-error output'
        )
        
        parser.add_argument(
            '--no-progress',
            action='store_true',
            help='Disable progress bar display'
        )
    
    def validate_arguments(self, options):
        """
        Validate command arguments following enterprise standards
        
        Args:
            options: Parsed command options
            
        Raises:
            CommandError: If validation fails
        """
        # Validate date format for --start-date parameter (was --since)
        if options.get('start_date'):
            try:
                datetime.strptime(options['start_date'], '%Y-%m-%d')
            except ValueError:
                raise CommandError(f"Invalid start-date format: {options['start_date']}. Use YYYY-MM-DD")
                
        # Validate date format for --end-date parameter
        if options.get('end_date'):
            try:
                datetime.strptime(options['end_date'], '%Y-%m-%d')
            except ValueError:
                raise CommandError(f"Invalid end-date format: {options['end_date']}. Use YYYY-MM-DD")
        
        # Validate batch size
        batch_size = options.get('batch_size', 100)
        if batch_size < 1 or batch_size > 10000:
            raise CommandError(f"Batch size must be between 1 and 10000, got: {batch_size}")
        
        # Validate max records
        max_records = options.get('max_records', 0)
        if max_records < 0:
            raise CommandError(f"Max records must be non-negative, got: {max_records}")
        
        # Validate conflicting flags
        if options.get('full') and options.get('start_date'):
            raise CommandError("Cannot use --full and --start-date together")
        
        # Validate date range consistency
        if options.get('start_date') and options.get('end_date'):
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d')
            if start_date >= end_date:
                raise CommandError("--start-date must be before --end-date")
        
        if options.get('force') and options.get('dry_run'):
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  --force with --dry-run: No actual overwriting will occur"
                )
            )
    
    def configure_logging(self, options):
        """
        Configure logging based on debug flag
        
        Args:
            options: Parsed command options
        """
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            # Enable debug logging for all relevant loggers
            for logger_name in ['arrivy', 'hubspot', 'salesrabbit', 'salespro', 'callrail']:
                logging.getLogger(logger_name).setLevel(logging.DEBUG)
    
    def parse_date_parameter(self, date_str: str, parameter_name: str = 'start-date') -> datetime:
        """
        Parse date string to timezone-aware datetime object
        
        Follows crm_sync_guide.md patterns for consistent date handling.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            parameter_name: Name of the parameter for error messages
            
        Returns:
            Timezone-aware datetime object
            
        Raises:
            CommandError: If date format is invalid
        """
        try:
            from django.utils.dateparse import parse_date
            date_obj = parse_date(date_str)
            if date_obj:
                return timezone.make_aware(
                    timezone.datetime.combine(date_obj, timezone.datetime.min.time())
                )
            else:
                raise ValueError(f"Invalid date format: {date_str}")
        except Exception as e:
            raise CommandError(f"Error parsing {parameter_name} '{date_str}': {str(e)}")
    
    def handle_execution_error(self, error: Exception, entity_type: str):
        """
        Handle execution errors with consistent formatting
        
        Args:
            error: The exception that occurred
            entity_type: Type of entity being synced
        """
        error_msg = str(error)
        logger.error(f"Error during {entity_type} sync: {error_msg}", exc_info=True)
        
        self.stdout.write(
            self.style.ERROR(f"❌ {entity_type.title()} sync failed: {error_msg}")
        )
        
        # Provide helpful troubleshooting hints
        if "connection" in error_msg.lower():
            self.stdout.write("💡 Check network connectivity and API credentials")
        elif "rate limit" in error_msg.lower():
            self.stdout.write("💡 Try reducing --batch-size or adding delays")
        elif "authentication" in error_msg.lower():
            self.stdout.write("💡 Check API tokens and credentials")
        elif "timeout" in error_msg.lower():
            self.stdout.write("💡 Try reducing --batch-size or check API status")
    
    def display_sync_summary(self, results: dict, entity_type: str, options: dict = None):
        """
        Display sync results in a consistent format
        
        Args:
            results: Sync results dictionary
            entity_type: Type of entity that was synced
            options: Command options (for quiet flag)
        """
        # Check if quiet mode is enabled
        is_quiet = options and options.get('quiet', False)
        
        if results.get('error'):
            self.stdout.write(
                self.style.ERROR(f"❌ {entity_type.title()} sync failed: {results['error']}")
            )
        else:
            # Extract metrics with defaults
            processed = results.get('processed', 0)
            created = results.get('created', 0)
            updated = results.get('updated', 0)
            failed = results.get('failed', 0)
            duration = results.get('duration_seconds', 0)
            rate = results.get('records_per_second', 0)
            
            # Display main summary (always shown, even in quiet mode)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {entity_type.upper()} sync complete: "
                    f"{processed} processed, {created} created, "
                    f"{updated} updated, {failed} failed "
                    f"in {duration:.2f}s ({rate:.1f} records/sec)"
                )
            )
            
            # Display warnings for failures (always shown)
            if failed > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  {failed} records failed to sync. Check logs for details."
                    )
                )
            
            # Display additional metrics only if not in quiet mode
            if not is_quiet:
                if 'api_calls' in results:
                    self.stdout.write(f"📊 API calls made: {results['api_calls']}")
                if 'batches_processed' in results:
                    self.stdout.write(f"📦 Batches processed: {results['batches_processed']}")
    
    @abstractmethod
    def handle(self, *args, **options):
        """
        Main command handler - must be implemented by subclasses
        
        Should follow this pattern:
        1. Call self.configure_logging(options)
        2. Call self.validate_arguments(options)
        3. Execute sync logic
        4. Call self.display_sync_summary(results, entity_type)
        5. Handle errors with self.handle_execution_error(error, entity_type)
        """
        pass
