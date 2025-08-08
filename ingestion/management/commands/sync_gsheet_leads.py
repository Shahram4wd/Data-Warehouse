"""
Google Sheets Lead Sync Management Command

Django management command for syncing leads from Google Sheets
following sync_crm_guide.md patterns.

Usage:
    python manage.py sync_gsheet_leads --sheet-url "https://docs.google.com/spreadsheets/d/..." [options]
    python manage.py sync_gsheet_leads --sheet-id "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" [options]
"""
import logging
from typing import Dict, Any
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.config.gsheet_config import GSheetConfig
from ingestion.gsheet.gsheet_sync_engine import GSheetSyncEngine
from ingestion.base.exceptions import SyncError, AuthenticationError, ValidationError


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync leads from Google Sheets to the data warehouse'
    
    def add_arguments(self, parser):
        """Add command line arguments"""
        
        # Required arguments (mutually exclusive)
        sheet_group = parser.add_mutually_exclusive_group(required=True)
        sheet_group.add_argument(
            '--sheet-url',
            type=str,
            help='Google Sheets URL to sync from'
        )
        sheet_group.add_argument(
            '--sheet-id',
            type=str,
            help='Google Sheets ID to sync from'
        )
        
        # Sync options
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of rows to process per batch (default: 1000)'
        )
        parser.add_argument(
            '--start-row',
            type=int,
            default=2,
            help='Row number to start sync from (default: 2, after headers)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate data without saving to database'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if sheet has not changed'
        )
        
        # Configuration options
        parser.add_argument(
            '--sheet-name',
            type=str,
            help='Specific sheet tab name to sync (default: first sheet)'
        )
        parser.add_argument(
            '--field-mappings',
            type=str,
            help='JSON string of custom field mappings: {"Sheet Header": "model_field"}'
        )
        parser.add_argument(
            '--auth-method',
            choices=['service_account', 'oauth2', 'api_key'],
            default='service_account',
            help='Authentication method to use (default: service_account)'
        )
        
        # Verbose options
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress non-error output'
        )
        
        # Testing options
        parser.add_argument(
            '--validate-access',
            action='store_true',
            help='Only validate access to the sheet, do not sync'
        )
        parser.add_argument(
            '--show-structure',
            action='store_true',
            help='Show sheet structure and suggested mappings'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Set up logging level
        if options['verbose']:
            logging.getLogger('ingestion').setLevel(logging.DEBUG)
        elif options['quiet']:
            logging.getLogger('ingestion').setLevel(logging.ERROR)
        
        # Get sheet identifier
        sheet_identifier = options['sheet_url'] or options['sheet_id']
        
        try:
            # Initialize sync engine
            config = GSheetConfig()
            if options['auth_method']:
                config.auth_method = options['auth_method']
            
            sync_engine = GSheetSyncEngine(config)
            
            # Parse custom field mappings if provided
            custom_mappings = None
            if options['field_mappings']:
                import json
                try:
                    custom_mappings = json.loads(options['field_mappings'])
                except json.JSONDecodeError as e:
                    raise CommandError(f"Invalid JSON in field-mappings: {e}")
            
            # Validate access if requested
            if options['validate_access']:
                self._validate_access(sync_engine, sheet_identifier)
                return
            
            # Show structure if requested
            if options['show_structure']:
                self._show_structure(sync_engine, sheet_identifier)
                return
            
            # Configure sheet
            if not options['quiet']:
                self.stdout.write("Configuring Google Sheets sync...")
            
            config_result = sync_engine.configure_sheet(
                sheet_identifier,
                model_type='lead',
                custom_mappings=custom_mappings
            )
            
            if not options['quiet']:
                self._display_config_summary(config_result)
            
            # Run sync
            if not options['quiet']:
                sync_type = "DRY RUN" if options['dry_run'] else "SYNC"
                self.stdout.write(f"\nStarting {sync_type}...")
            
            sync_result = sync_engine.sync_leads(
                batch_size=options['batch_size'],
                start_row=options['start_row'],
                dry_run=options['dry_run']
            )
            
            # Display results
            self._display_sync_results(sync_result, options['quiet'])
            
        except AuthenticationError as e:
            raise CommandError(f"Authentication failed: {e}")
        except ValidationError as e:
            raise CommandError(f"Validation error: {e}")
        except SyncError as e:
            raise CommandError(f"Sync error: {e}")
        except Exception as e:
            logger.exception("Unexpected error during sync")
            raise CommandError(f"Unexpected error: {e}")
    
    def _validate_access(self, sync_engine: GSheetSyncEngine, sheet_identifier: str):
        """Validate access to Google Sheets"""
        self.stdout.write("Validating access to Google Sheets...")
        
        success, message = sync_engine.validate_sheet_access(sheet_identifier)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f"✓ {message}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ {message}")
            )
            raise CommandError("Access validation failed")
    
    def _show_structure(self, sync_engine: GSheetSyncEngine, sheet_identifier: str):
        """Show sheet structure and suggested mappings"""
        self.stdout.write("Analyzing sheet structure...\n")
        
        try:
            # Get sheet metadata and structure
            metadata = sync_engine.client.get_sheet_metadata(sheet_identifier)
            structure = sync_engine.client.get_sheet_structure(sheet_identifier)
            
            # Display metadata
            self.stdout.write(self.style.SUCCESS("Sheet Information:"))
            self.stdout.write(f"  Title: {metadata['title']}")
            self.stdout.write(f"  Sheet ID: {metadata['sheet_id']}")
            self.stdout.write(f"  Total Rows: {structure['total_rows']}")
            self.stdout.write(f"  Total Columns: {structure['total_columns']}")
            
            # Display headers
            self.stdout.write(f"\nColumn Headers ({len(structure['headers'])}):")
            for i, header in enumerate(structure['headers'], 1):
                self.stdout.write(f"  {i:2d}. {header}")
            
            # Display suggested mappings
            mappings = structure['suggested_mappings']
            self.stdout.write(f"\nSuggested Field Mappings ({len(mappings)}):")
            if mappings:
                for header, field in mappings.items():
                    self.stdout.write(f"  '{header}' → {field}")
            else:
                self.stdout.write("  No automatic mappings suggested")
            
            # Display unmapped headers
            unmapped = [h for h in structure['headers'] if h not in mappings]
            if unmapped:
                self.stdout.write(f"\nUnmapped Headers ({len(unmapped)}):")
                for header in unmapped:
                    self.stdout.write(f"  '{header}'")
            
            # Display sample data
            if structure['sample_data']:
                self.stdout.write(f"\nSample Data (first 3 rows):")
                for i, row in enumerate(structure['sample_data'][:3], 1):
                    self.stdout.write(f"  Row {i}: {row[:5]}{'...' if len(row) > 5 else ''}")
        
        except Exception as e:
            raise CommandError(f"Failed to analyze sheet structure: {e}")
    
    def _display_config_summary(self, config_result: Dict[str, Any]):
        """Display configuration summary"""
        self.stdout.write(self.style.SUCCESS("\nConfiguration Summary:"))
        self.stdout.write(f"  Sheet: {config_result['sheet_title']}")
        self.stdout.write(f"  Sheet ID: {config_result['sheet_id']}")
        self.stdout.write(f"  Total Rows: {config_result['total_rows']}")
        self.stdout.write(f"  Headers: {len(config_result['headers'])}")
        self.stdout.write(f"  Mapped Fields: {config_result['mapped_fields']}")
        
        if config_result['unmapped_headers']:
            self.stdout.write(f"  Unmapped Headers: {len(config_result['unmapped_headers'])}")
            if len(config_result['unmapped_headers']) <= 5:
                for header in config_result['unmapped_headers']:
                    self.stdout.write(f"    - {header}")
            else:
                for header in config_result['unmapped_headers'][:3]:
                    self.stdout.write(f"    - {header}")
                self.stdout.write(f"    ... and {len(config_result['unmapped_headers']) - 3} more")
    
    def _display_sync_results(self, sync_result: Dict[str, Any], quiet: bool = False):
        """Display sync results"""
        if quiet and sync_result.get('errors', 0) == 0:
            return
        
        # Status message
        if sync_result['dry_run']:
            status_msg = "DRY RUN COMPLETED"
            status_style = self.style.WARNING
        elif sync_result.get('errors', 0) > 0:
            status_msg = "SYNC COMPLETED WITH ERRORS"
            status_style = self.style.ERROR
        else:
            status_msg = "SYNC COMPLETED SUCCESSFULLY"
            status_style = self.style.SUCCESS
        
        self.stdout.write(f"\n{status_style(status_msg)}")
        
        # Summary statistics
        self.stdout.write("\nSync Results:")
        self.stdout.write(f"  Total Processed: {sync_result['total_processed']}")
        self.stdout.write(f"  Created: {sync_result['created']}")
        self.stdout.write(f"  Updated: {sync_result['updated']}")
        self.stdout.write(f"  Skipped: {sync_result['skipped']}")
        self.stdout.write(f"  Errors: {sync_result['errors']}")
        
        # Duration
        if 'duration' in sync_result:
            duration = sync_result['duration']
            if duration < 60:
                self.stdout.write(f"  Duration: {duration:.1f} seconds")
            else:
                minutes = int(duration // 60)
                seconds = duration % 60
                self.stdout.write(f"  Duration: {minutes}m {seconds:.1f}s")
        
        # Error details
        if sync_result.get('error_details') and not quiet:
            self.stdout.write(f"\nError Details (showing first 10):")
            for i, error in enumerate(sync_result['error_details'][:10], 1):
                self.stdout.write(
                    f"  {i}. Row {error['row_number']}: {error['error']}"
                )
            
            if len(sync_result['error_details']) > 10:
                remaining = len(sync_result['error_details']) - 10
                self.stdout.write(f"  ... and {remaining} more errors")
        
        # Recommendations
        if not sync_result['dry_run'] and sync_result.get('errors', 0) > 0:
            self.stdout.write(f"\n{self.style.WARNING('Recommendations:')}")
            self.stdout.write("  - Review error details above")
            self.stdout.write("  - Check field mappings with --show-structure")
            self.stdout.write("  - Use --dry-run to validate before syncing")
        
        # Fatal error
        if sync_result.get('fatal_error'):
            self.stdout.write(f"\n{self.style.ERROR('Fatal Error:')}")
            self.stdout.write(f"  {sync_result['fatal_error']}")
