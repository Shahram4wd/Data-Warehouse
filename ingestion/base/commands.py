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
        
        Standard Flags (All CRM Syncs):
        - --full: Perform full sync (ignore last sync timestamp)
        - --force-overwrite: Completely replace existing records
        - --since: Manual sync start date (YYYY-MM-DD)
        - --dry-run: Test run without database writes
        - --batch-size: Records per API batch
        - --max-records: Limit total records (0 = unlimited)
        - --debug: Enable verbose logging
        """
        # Core sync strategy flags
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        
        parser.add_argument(
            '--force-overwrite',
            action='store_true',
            help='Completely replace existing records'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
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
        
        # Debugging and monitoring
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging'
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
        # Validate date format for --since parameter
        if options.get('since'):
            try:
                datetime.strptime(options['since'], '%Y-%m-%d')
            except ValueError:
                raise CommandError(f"Invalid date format: {options['since']}. Use YYYY-MM-DD")
        
        # Validate batch size
        batch_size = options.get('batch_size', 100)
        if batch_size < 1 or batch_size > 10000:
            raise CommandError(f"Batch size must be between 1 and 10000, got: {batch_size}")
        
        # Validate max records
        max_records = options.get('max_records', 0)
        if max_records < 0:
            raise CommandError(f"Max records must be non-negative, got: {max_records}")
        
        # Validate conflicting flags
        if options.get('full') and options.get('since'):
            raise CommandError("Cannot use --full and --since together")
        
        if options.get('force_overwrite') and options.get('dry_run'):
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  --force-overwrite with --dry-run: No actual overwriting will occur"
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
    
    def parse_date_parameter(self, date_str: str) -> datetime:
        """
        Parse date string to timezone-aware datetime object
        
        Follows crm_sync_guide.md patterns for consistent date handling.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
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
            raise CommandError(f"Error parsing date '{date_str}': {str(e)}")
    
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
    
    def display_sync_summary(self, results: dict, entity_type: str):
        """
        Display sync results in a consistent format
        
        Args:
            results: Sync results dictionary
            entity_type: Type of entity that was synced
        """
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
            
            # Display main summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {entity_type.upper()} sync complete: "
                    f"{processed} processed, {created} created, "
                    f"{updated} updated, {failed} failed "
                    f"in {duration:.2f}s ({rate:.1f} records/sec)"
                )
            )
            
            # Display warnings for failures
            if failed > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  {failed} records failed to sync. Check logs for details."
                    )
                )
            
            # Display additional metrics if available
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
