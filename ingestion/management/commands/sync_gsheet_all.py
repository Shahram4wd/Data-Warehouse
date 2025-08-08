"""
Google Sheets All Data Sync Management Command

Django management command for comprehensive Google Sheets sync
following sync_crm_guide.md patterns.

Usage:
    python manage.py sync_gsheet_all --sheet-url "https://docs.google.com/spreadsheets/d/..." [options]
"""
import logging
from typing import Dict, Any, List
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.config.gsheet_config import GSheetConfig
from ingestion.gsheet.gsheet_sync_engine import GSheetSyncEngine
from ingestion.base.exceptions import SyncError, AuthenticationError, ValidationError


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Comprehensive sync of all data from Google Sheets'
    
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
            '--model-type',
            choices=['lead', 'contact', 'auto'],
            default='auto',
            help='Data model type to use (default: auto-detect)'
        )
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
        
        # Sheet selection
        parser.add_argument(
            '--sheet-names',
            type=str,
            nargs='*',
            help='Specific sheet tab names to sync (default: all sheets)'
        )
        parser.add_argument(
            '--exclude-sheets',
            type=str,
            nargs='*',
            help='Sheet tab names to exclude from sync'
        )
        
        # Configuration
        parser.add_argument(
            '--field-mappings',
            type=str,
            help='JSON string of custom field mappings'
        )
        parser.add_argument(
            '--auth-method',
            choices=['service_account', 'oauth2', 'api_key'],
            default='service_account',
            help='Authentication method to use (default: service_account)'
        )
        
        # Processing options
        parser.add_argument(
            '--deduplicate',
            action='store_true',
            help='Remove duplicate entries based on email/phone'
        )
        parser.add_argument(
            '--validate-data',
            action='store_true',
            help='Apply strict data validation (may skip more records)'
        )
        parser.add_argument(
            '--parallel-sheets',
            action='store_true',
            help='Process multiple sheets in parallel (faster but uses more resources)'
        )
        
        # Reporting options
        parser.add_argument(
            '--generate-report',
            action='store_true',
            help='Generate detailed sync report'
        )
        parser.add_argument(
            '--report-file',
            type=str,
            help='File to save sync report (default: auto-generated)'
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
        
        # Analysis options
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze sheet structure, do not sync'
        )
        parser.add_argument(
            '--show-stats',
            action='store_true',
            help='Show detailed statistics after sync'
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
            
            # Get sheet metadata to identify all sheets
            if not options['quiet']:
                self.stdout.write("Analyzing Google Sheets document...")
            
            metadata = sync_engine.client.get_sheet_metadata(sheet_identifier)
            available_sheets = [sheet['title'] for sheet in metadata['sheets']]
            
            # Determine which sheets to process
            sheets_to_process = self._determine_sheets_to_process(
                available_sheets, options
            )
            
            if not sheets_to_process:
                raise CommandError("No sheets selected for processing")
            
            if not options['quiet']:
                self.stdout.write(f"Processing {len(sheets_to_process)} sheet(s): {', '.join(sheets_to_process)}")
            
            # Analysis only mode
            if options['analyze_only']:
                self._analyze_sheets(sync_engine, sheet_identifier, sheets_to_process)
                return
            
            # Process each sheet
            all_results = {}
            total_stats = {
                'total_processed': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': 0,
                'sheets_processed': 0,
                'start_time': timezone.now()
            }
            
            for sheet_name in sheets_to_process:
                if not options['quiet']:
                    self.stdout.write(f"\n{'='*60}")
                    self.stdout.write(f"Processing sheet: {sheet_name}")
                    self.stdout.write('='*60)
                
                try:
                    sheet_results = self._process_single_sheet(
                        sync_engine, sheet_identifier, sheet_name, 
                        custom_mappings, options
                    )
                    
                    all_results[sheet_name] = sheet_results
                    
                    # Update total stats
                    for key in ['total_processed', 'created', 'updated', 'skipped', 'errors']:
                        total_stats[key] += sheet_results.get(key, 0)
                    total_stats['sheets_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process sheet '{sheet_name}': {e}")
                    all_results[sheet_name] = {'error': str(e)}
                    if not options['force']:
                        raise CommandError(f"Sheet processing failed: {e}")
            
            total_stats['end_time'] = timezone.now()
            total_stats['duration'] = (total_stats['end_time'] - total_stats['start_time']).total_seconds()
            
            # Display final results
            self._display_final_results(all_results, total_stats, options)
            
            # Generate report if requested
            if options['generate_report']:
                self._generate_sync_report(all_results, total_stats, options)
                
        except AuthenticationError as e:
            raise CommandError(f"Authentication failed: {e}")
        except ValidationError as e:
            raise CommandError(f"Validation error: {e}")
        except SyncError as e:
            raise CommandError(f"Sync error: {e}")
        except Exception as e:
            logger.exception("Unexpected error during sync")
            raise CommandError(f"Unexpected error: {e}")
    
    def _determine_sheets_to_process(self, available_sheets: List[str], 
                                   options: Dict) -> List[str]:
        """Determine which sheets to process based on options"""
        
        if options['sheet_names']:
            # Use specific sheets
            requested_sheets = options['sheet_names']
            missing_sheets = [s for s in requested_sheets if s not in available_sheets]
            if missing_sheets:
                raise CommandError(f"Sheets not found: {', '.join(missing_sheets)}")
            sheets_to_process = requested_sheets
        else:
            # Use all sheets
            sheets_to_process = available_sheets.copy()
        
        # Exclude sheets if specified
        if options['exclude_sheets']:
            sheets_to_process = [s for s in sheets_to_process 
                               if s not in options['exclude_sheets']]
        
        return sheets_to_process
    
    def _analyze_sheets(self, sync_engine: GSheetSyncEngine, 
                       sheet_identifier: str, sheets: List[str]):
        """Analyze sheet structures without syncing"""
        
        for sheet_name in sheets:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Sheet: {sheet_name}")
            self.stdout.write('='*60)
            
            try:
                structure = sync_engine.client.get_sheet_structure(
                    sheet_identifier, sheet_name
                )
                
                self.stdout.write(f"Rows: {structure['total_rows']}")
                self.stdout.write(f"Columns: {structure['total_columns']}")
                
                # Display headers
                self.stdout.write(f"\nHeaders ({len(structure['headers'])}):")
                for i, header in enumerate(structure['headers'], 1):
                    self.stdout.write(f"  {i:2d}. {header}")
                
                # Display suggested mappings
                mappings = structure['suggested_mappings']
                if mappings:
                    self.stdout.write(f"\nSuggested Mappings ({len(mappings)}):")
                    for header, field in mappings.items():
                        self.stdout.write(f"  '{header}' → {field}")
                
                # Detect likely model type
                model_type = self._detect_model_type(structure['headers'])
                self.stdout.write(f"\nSuggested Model Type: {model_type}")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error analyzing sheet: {e}"))
    
    def _detect_model_type(self, headers: List[str]) -> str:
        """Detect the most appropriate model type based on headers"""
        header_text = ' '.join(headers).lower()
        
        # Lead indicators
        lead_indicators = ['lead', 'prospect', 'source', 'status', 'score', 'campaign']
        lead_score = sum(1 for indicator in lead_indicators if indicator in header_text)
        
        # Contact indicators
        contact_indicators = ['contact', 'directory', 'employee', 'staff', 'member']
        contact_score = sum(1 for indicator in contact_indicators if indicator in header_text)
        
        if lead_score > contact_score:
            return 'lead'
        elif contact_score > lead_score:
            return 'contact'
        else:
            return 'lead'  # Default to lead
    
    def _process_single_sheet(self, sync_engine: GSheetSyncEngine,
                             sheet_identifier: str, sheet_name: str,
                             custom_mappings: Dict, options: Dict) -> Dict[str, Any]:
        """Process a single sheet"""
        
        # Detect model type if auto
        model_type = options['model_type']
        if model_type == 'auto':
            structure = sync_engine.client.get_sheet_structure(
                sheet_identifier, sheet_name
            )
            model_type = self._detect_model_type(structure['headers'])
            if not options['quiet']:
                self.stdout.write(f"Auto-detected model type: {model_type}")
        
        # Configure sheet
        config_result = sync_engine.configure_sheet(
            sheet_identifier,
            model_type=model_type,
            custom_mappings=custom_mappings
        )
        
        if not options['quiet']:
            self.stdout.write(f"Headers: {len(config_result['headers'])}")
            self.stdout.write(f"Mapped fields: {config_result['mapped_fields']}")
            self.stdout.write(f"Total rows: {config_result['total_rows']}")
        
        # Run sync
        if model_type == 'lead':
            sync_result = sync_engine.sync_leads(
                batch_size=options['batch_size'],
                start_row=options['start_row'],
                dry_run=options['dry_run']
            )
        else:
            # For contacts, use leads sync for now (can be extended)
            sync_result = sync_engine.sync_leads(
                batch_size=options['batch_size'],
                start_row=options['start_row'],
                dry_run=options['dry_run']
            )
        
        # Add sheet-specific info
        sync_result['sheet_name'] = sheet_name
        sync_result['model_type'] = model_type
        sync_result['config'] = config_result
        
        if not options['quiet']:
            self._display_sheet_results(sync_result)
        
        return sync_result
    
    def _display_sheet_results(self, result: Dict[str, Any]):
        """Display results for a single sheet"""
        self.stdout.write(f"\nResults for '{result['sheet_name']}':")
        self.stdout.write(f"  Processed: {result['total_processed']}")
        self.stdout.write(f"  Created: {result['created']}")
        self.stdout.write(f"  Updated: {result['updated']}")
        self.stdout.write(f"  Skipped: {result['skipped']}")
        self.stdout.write(f"  Errors: {result['errors']}")
        
        if result.get('errors', 0) > 0:
            self.stdout.write(self.style.WARNING(
                f"  ⚠ {result['errors']} errors occurred"
            ))
    
    def _display_final_results(self, all_results: Dict[str, Dict], 
                              total_stats: Dict, options: Dict):
        """Display final comprehensive results"""
        
        if options['quiet'] and total_stats.get('errors', 0) == 0:
            return
        
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write("FINAL SYNC RESULTS")
        self.stdout.write('='*80)
        
        # Overall stats
        success_style = self.style.SUCCESS
        if total_stats.get('errors', 0) > 0:
            success_style = self.style.WARNING
        
        self.stdout.write(success_style("\nOverall Statistics:"))
        self.stdout.write(f"  Sheets Processed: {total_stats['sheets_processed']}")
        self.stdout.write(f"  Total Records: {total_stats['total_processed']}")
        self.stdout.write(f"  Created: {total_stats['created']}")
        self.stdout.write(f"  Updated: {total_stats['updated']}")
        self.stdout.write(f"  Skipped: {total_stats['skipped']}")
        self.stdout.write(f"  Errors: {total_stats['errors']}")
        
        # Duration
        if 'duration' in total_stats:
            duration = total_stats['duration']
            if duration < 60:
                self.stdout.write(f"  Duration: {duration:.1f} seconds")
            else:
                minutes = int(duration // 60)
                seconds = duration % 60
                self.stdout.write(f"  Duration: {minutes}m {seconds:.1f}s")
        
        # Per-sheet breakdown
        if not options['quiet'] or total_stats.get('errors', 0) > 0:
            self.stdout.write("\nPer-Sheet Results:")
            for sheet_name, result in all_results.items():
                if 'error' in result:
                    self.stdout.write(self.style.ERROR(
                        f"  {sheet_name}: FAILED - {result['error']}"
                    ))
                else:
                    status = "SUCCESS"
                    style = self.style.SUCCESS
                    if result.get('errors', 0) > 0:
                        status = f"PARTIAL ({result['errors']} errors)"
                        style = self.style.WARNING
                    
                    self.stdout.write(style(
                        f"  {sheet_name}: {status} - "
                        f"{result['total_processed']} processed, "
                        f"{result['created']} created, "
                        f"{result['updated']} updated"
                    ))
        
        # Show statistics if requested
        if options['show_stats']:
            self._display_detailed_stats(all_results, total_stats)
    
    def _display_detailed_stats(self, all_results: Dict[str, Dict], 
                               total_stats: Dict):
        """Display detailed statistics"""
        
        self.stdout.write(f"\n{self.style.SUCCESS('DETAILED STATISTICS:')}")
        
        # Processing rates
        if total_stats.get('duration', 0) > 0:
            rate = total_stats['total_processed'] / total_stats['duration']
            self.stdout.write(f"  Processing Rate: {rate:.1f} records/second")
        
        # Success rates
        total_records = total_stats['total_processed']
        if total_records > 0:
            success_rate = ((total_records - total_stats['errors']) / total_records) * 100
            self.stdout.write(f"  Success Rate: {success_rate:.1f}%")
        
        # Model type breakdown
        model_types = {}
        for result in all_results.values():
            if 'model_type' in result:
                model_type = result['model_type']
                if model_type not in model_types:
                    model_types[model_type] = 0
                model_types[model_type] += result.get('total_processed', 0)
        
        if model_types:
            self.stdout.write("  Model Types:")
            for model_type, count in model_types.items():
                self.stdout.write(f"    {model_type}: {count} records")
    
    def _generate_sync_report(self, all_results: Dict[str, Dict], 
                             total_stats: Dict, options: Dict):
        """Generate detailed sync report"""
        
        import json
        from datetime import datetime
        
        # Generate report filename if not provided
        report_file = options['report_file']
        if not report_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"gsheet_sync_report_{timestamp}.json"
        
        # Prepare report data
        report_data = {
            'sync_info': {
                'timestamp': timezone.now().isoformat(),
                'command': 'sync_gsheet_all',
                'options': {k: v for k, v in options.items() 
                          if k not in ['field_mappings']},  # Exclude sensitive data
                'duration': total_stats.get('duration', 0)
            },
            'summary': total_stats,
            'sheets': all_results
        }
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.stdout.write(f"\n{self.style.SUCCESS('Sync report saved:')} {report_file}")
            
        except Exception as e:
            self.stdout.write(f"\n{self.style.ERROR('Failed to save report:')} {e}")
