"""
Unified Arrivy Sync Orchestrator Command

Orchestrates all individual sync_arrivy_*.py commands using Django's call_command
to avoid code duplication while providing a unified interface.

Usage:
    python manage.py sync_arrivy_all --entity-type=entities
    python manage.py sync_arrivy_all --entity-type=tasks --full
    python manage.py sync_arrivy_all --entity-type=groups --since=2025-01-01
    python manage.py sync_arrivy_all --entity-type=all --dry-run
"""

import logging
from typing import Dict, Any, List
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone
from io import StringIO
import sys

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Unified orchestrator for all Arrivy sync commands (delegates to individual commands)"
    
    def add_arguments(self, parser):
        # Entity type selection
        parser.add_argument(
            '--entity-type',
            choices=['entities', 'tasks', 'groups', 'location_reports', 'task_status', 'all'],
            default='all',
            help='Type of Arrivy entities to sync (default: all)'
        )
        
        # Base sync arguments (passed to individual commands)
        parser.add_argument(
            '--full',
            action='store_true',
            help='Force full sync instead of incremental'
        )
        
        parser.add_argument(
            '--force-overwrite',
            action='store_true',
            help='Overwrite existing records'
        )
        
        parser.add_argument(
            '--since',
            type=str,
            help='Sync data since specific date (YYYY-MM-DD)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without committing'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for processing (default: 100)'
        )
        
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Maximum records to process (0 = no limit)'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )
        
        # Legacy compatibility arguments
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for task filtering (YYYY-MM-DD format, tasks only)'
        )
        
        parser.add_argument(
            '--end-date', 
            type=str,
            help='End date for task filtering (YYYY-MM-DD format, tasks only)'
        )
        
        parser.add_argument(
            '--use-legacy-tasks',
            action='store_true',
            help='Use legacy tasks endpoint instead of bookings endpoint'
        )
        
        parser.add_argument(
            '--crew-members-mode',
            action='store_true', 
            help='Fetch entities as crew members from divisions (with division context)'
        )
    
    def handle(self, *args, **options):
        """Main orchestrator handler that delegates to individual sync commands"""
        
        # Configure logging
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger('arrivy').setLevel(logging.DEBUG)
        
        entity_type = options['entity_type']
        
        try:
            if entity_type == 'all':
                # Run all entity types
                results = self._run_all_commands(options)
            else:
                # Run specific entity type
                results = self._run_single_command(entity_type, options)
            
            self._display_results(results, entity_type)
            
        except Exception as e:
            logger.exception(f"Error during Arrivy sync orchestration")
            raise CommandError(f"Sync orchestration failed: {str(e)}")
    
    def _run_all_commands(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all Arrivy sync commands in sequence
        
        Args:
            options: Command options
            
        Returns:
            Combined results from all commands
        """
        self.stdout.write("Starting comprehensive Arrivy sync (all entities)...")
        
        # Define command order (dependencies considered)
        commands = [
            ('entities', 'sync_arrivy_entities'),
            ('groups', 'sync_arrivy_groups'), 
            ('tasks', 'sync_arrivy_tasks'),
            ('location_reports', 'sync_arrivy_location_reports'),
            ('task_status', 'sync_arrivy_task_status')
        ]
        
        all_results = {}
        
        for entity_type, command_name in commands:
            self.stdout.write(f"\n--- Running {command_name} ---")
            
            try:
                result = self._run_single_command(entity_type, options, command_name)
                all_results[entity_type] = result
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {entity_type}: Command completed successfully")
                )
                
            except Exception as e:
                logger.error(f"Error running {command_name}: {str(e)}")
                all_results[entity_type] = {'error': str(e), 'command': command_name}
                
                self.stdout.write(
                    self.style.ERROR(f"❌ {entity_type}: {str(e)}")
                )
        
        return all_results
    
    def _run_single_command(self, entity_type: str, options: Dict[str, Any], command_name: str = None) -> Dict[str, Any]:
        """
        Run a single Arrivy sync command
        
        Args:
            entity_type: Type of entity to sync
            options: Command options
            command_name: Optional command name override
            
        Returns:
            Command execution results
        """
        if not command_name:
            command_name = f"sync_arrivy_{entity_type}"
        
        # Prepare arguments for the individual command
        command_args = []
        command_kwargs = {}
        
        # Map common arguments
        if options.get('full'):
            command_kwargs['full'] = True
        if options.get('force_overwrite'):
            command_kwargs['force_overwrite'] = True
        if options.get('since'):
            command_kwargs['since'] = options['since']
        if options.get('dry_run'):
            command_kwargs['dry_run'] = True
        if options.get('batch_size', 100) != 100:
            command_kwargs['batch_size'] = options['batch_size']
        if options.get('max_records', 0) != 0:
            command_kwargs['max_records'] = options['max_records']
        if options.get('debug'):
            command_kwargs['debug'] = True
        
        # Add entity-specific arguments
        if entity_type == 'tasks':
            if options.get('start_date'):
                # Individual task command uses --date-range-days, convert from start/end dates
                try:
                    from django.utils.dateparse import parse_date
                    start_date = parse_date(options['start_date'])
                    end_date = parse_date(options.get('end_date', timezone.now().date().isoformat()))
                    if start_date and end_date:
                        delta = (end_date - start_date).days
                        command_kwargs['date_range_days'] = max(1, delta)
                except:
                    pass  # Let individual command handle validation
            
            if options.get('use_legacy_tasks'):
                # Map to individual command equivalent (if available)
                pass  # Individual command may have different flag name
        
        elif entity_type == 'entities':
            if options.get('crew_members_mode'):
                command_kwargs['include_relationships'] = True
        
        # Capture output from the individual command
        output_buffer = StringIO()
        
        try:
            # Call the individual Django management command
            call_command(
                command_name,
                *command_args,
                stdout=output_buffer,
                stderr=output_buffer,
                **command_kwargs
            )
            
            output = output_buffer.getvalue()
            
            # Parse basic success from output (simple approach)
            return {
                'success': True,
                'command': command_name,
                'output': output,
                'processed': self._extract_metric_from_output(output, 'processed'),
                'created': self._extract_metric_from_output(output, 'created'),
                'updated': self._extract_metric_from_output(output, 'updated'),
                'failed': self._extract_metric_from_output(output, 'failed')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': command_name,
                'output': output_buffer.getvalue()
            }
        finally:
            output_buffer.close()
    
    def _extract_metric_from_output(self, output: str, metric: str) -> int:
        """
        Extract numeric metric from command output
        
        Args:
            output: Command output text
            metric: Metric name to extract
            
        Returns:
            Numeric value or 0 if not found
        """
        import re
        
        # Look for patterns like "123 processed", "45 created", etc.
        pattern = rf'(\d+)\s+{metric}'
        match = re.search(pattern, output, re.IGNORECASE)
        
        if match:
            return int(match.group(1))
        return 0
    
    def _display_results(self, results: Dict[str, Any], entity_type: str):
        """
        Display orchestration results in a user-friendly format
        
        Args:
            results: Command execution results
            entity_type: Entity type that was processed
        """
        if entity_type == 'all':
            # Display results for all entity types
            self.stdout.write("\n" + "="*70)
            self.stdout.write("ARRIVY SYNC ORCHESTRATION COMPLETE - SUMMARY")
            self.stdout.write("="*70)
            
            total_commands = len(results)
            successful_commands = 0
            failed_commands = 0
            
            for etype, result in results.items():
                if result.get('success', False):
                    successful_commands += 1
                    processed = result.get('processed', 'N/A')
                    created = result.get('created', 'N/A') 
                    updated = result.get('updated', 'N/A')
                    failed = result.get('failed', 'N/A')
                    
                    self.stdout.write(
                        f"✅ {etype.upper()}: {processed} processed, "
                        f"{created} created, {updated} updated, {failed} failed"
                    )
                else:
                    failed_commands += 1
                    error_msg = result.get('error', 'Unknown error')
                    command = result.get('command', f'sync_arrivy_{etype}')
                    self.stdout.write(f"❌ {etype.upper()}: ERROR in {command} - {error_msg}")
            
            self.stdout.write("-" * 70)
            self.stdout.write(
                f"ORCHESTRATION SUMMARY: {successful_commands}/{total_commands} commands successful, "
                f"{failed_commands} failed"
            )
            
            if failed_commands > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  {failed_commands} commands failed. Check individual command logs for details."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("🎉 All Arrivy sync commands completed successfully!")
                )
                
        else:
            # Display results for single entity type
            if not results.get('success', False):
                command = results.get('command', f'sync_arrivy_{entity_type}')
                error_msg = results.get('error', 'Unknown error')
                self.stdout.write(
                    self.style.ERROR(f"❌ Command {command} failed: {error_msg}")
                )
                
                # Show command output if available
                if results.get('output'):
                    self.stdout.write("\nCommand output:")
                    self.stdout.write(results['output'])
            else:
                command = results.get('command', f'sync_arrivy_{entity_type}')
                processed = results.get('processed', 'N/A')
                created = results.get('created', 'N/A')
                updated = results.get('updated', 'N/A')
                failed = results.get('failed', 'N/A')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {command} completed: "
                        f"{processed} processed, {created} created, "
                        f"{updated} updated, {failed} failed"
                    )
                )
                
                # Show partial command output (just the summary)
                if results.get('output'):
                    lines = results['output'].strip().split('\n')
                    # Show last few lines which typically contain the summary
                    summary_lines = [line for line in lines[-5:] if line.strip()]
                    if summary_lines:
                        self.stdout.write("\nCommand summary:")
                        for line in summary_lines:
                            self.stdout.write(f"  {line}")
