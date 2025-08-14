"""
Unified Arrivy Sync Management Command

Replaces all individual sync_arrivy_*.py commands with a single, enterprise-grade command
following crm_sync_guide.md patterns and SyncHistory integration.

Usage:
    python manage.py sync_arrivy --entity-type=entities
    python manage.py sync_arrivy --entity-type=tasks --full
    python manage.py sync_arrivy --entity-type=groups --since=2025-01-01
    python manage.py sync_arrivy --entity-type=all --dry-run
"""

import asyncio
import logging
from typing import Dict, Any, List
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines import (
    ArrivyEntitiesSyncEngine,
    ArrivyTasksSyncEngine, 
    ArrivyGroupsSyncEngine
)

logger = logging.getLogger(__name__)

class Command(BaseSyncCommand):
    help = "Unified sync command for all Arrivy entities (replaces individual sync_arrivy_*.py commands)"
    
    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force-overwrite, --since, --dry-run, --batch-size, etc.)
        super().add_arguments(parser)
        
        # Add Arrivy-specific arguments
        parser.add_argument(
            '--entity-type',
            choices=['entities', 'tasks', 'groups', 'all'],
            default='all',
            help='Type of Arrivy entities to sync (default: all)'
        )
        
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
        """Main command handler following enterprise patterns"""
        
        # Configure logging
        if options.get('debug'):
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger('arrivy').setLevel(logging.DEBUG)
        
        # Validate entity type
        entity_type = options['entity_type']
        
        try:
            if entity_type == 'all':
                # Sync all entity types
                results = self._sync_all_entities(options)
            else:
                # Sync specific entity type
                results = self._sync_single_entity(entity_type, options)
            
            self._display_results(results, entity_type)
            
        except Exception as e:
            logger.exception(f"Error during Arrivy sync")
            raise CommandError(f"Sync failed: {str(e)}")
    
    def _sync_all_entities(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync all Arrivy entity types
        
        Args:
            options: Command options
            
        Returns:
            Combined sync results
        """
        self.stdout.write("Starting comprehensive Arrivy sync (all entities)...")
        
        entity_types = ['entities', 'tasks', 'groups']
        all_results = {}
        
        for entity_type in entity_types:
            self.stdout.write(f"\n--- Syncing {entity_type} ---")
            
            try:
                results = self._sync_single_entity(entity_type, options)
                all_results[entity_type] = results
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {entity_type}: {results['processed']} processed, "
                        f"{results['created']} created, {results['updated']} updated"
                    )
                )
                
            except Exception as e:
                logger.error(f"Error syncing {entity_type}: {str(e)}")
                all_results[entity_type] = {'error': str(e)}
                
                self.stdout.write(
                    self.style.ERROR(f"❌ {entity_type}: {str(e)}")
                )
        
        return all_results
    
    def _sync_single_entity(self, entity_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync a specific entity type
        
        Args:
            entity_type: Type of entity to sync
            options: Command options
            
        Returns:
            Sync results
        """
        # Get appropriate sync engine
        engine_class = self._get_engine_class(entity_type)
        
        # Create engine instance with options
        engine = engine_class(
            batch_size=options.get('batch_size', 100),
            max_records=options.get('max_records', 0),
            dry_run=options.get('dry_run', False),
            force_overwrite=options.get('force_overwrite', False),
            debug=options.get('debug', False)
        )
        
        # Prepare sync options
        sync_options = {
            'force_full': options.get('full', False),
            'since_param': options.get('since'),
        }
        
        # Add entity-specific options
        if entity_type == 'tasks':
            if options.get('start_date'):
                sync_options['start_date'] = self._parse_date(options['start_date'])
            if options.get('end_date'):
                sync_options['end_date'] = self._parse_date(options['end_date'])
            sync_options['use_legacy_endpoint'] = options.get('use_legacy_tasks', False)
        
        elif entity_type == 'entities':
            sync_options['crew_members_mode'] = options.get('crew_members_mode', True)
        
        # Execute sync
        return asyncio.run(engine.execute_sync(**sync_options))
    
    def _get_engine_class(self, entity_type: str):
        """
        Get sync engine class for entity type
        
        Args:
            entity_type: Type of entity
            
        Returns:
            Sync engine class
        """
        engine_map = {
            'entities': ArrivyEntitiesSyncEngine,
            'tasks': ArrivyTasksSyncEngine,
            'groups': ArrivyGroupsSyncEngine
        }
        
        engine_class = engine_map.get(entity_type)
        if not engine_class:
            raise CommandError(f"Unknown entity type: {entity_type}")
        
        return engine_class
    
    def _parse_date(self, date_str: str):
        """
        Parse date string to datetime object
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Datetime object
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
    
    def _display_results(self, results: Dict[str, Any], entity_type: str):
        """
        Display sync results in a user-friendly format
        
        Args:
            results: Sync results
            entity_type: Entity type that was synced
        """
        if entity_type == 'all':
            # Display results for all entity types
            self.stdout.write("\n" + "="*60)
            self.stdout.write("ARRIVY SYNC COMPLETE - SUMMARY")
            self.stdout.write("="*60)
            
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_failed = 0
            
            for etype, result in results.items():
                if 'error' in result:
                    self.stdout.write(f"{etype.upper()}: ERROR - {result['error']}")
                else:
                    processed = result.get('processed', 0)
                    created = result.get('created', 0)
                    updated = result.get('updated', 0)
                    failed = result.get('failed', 0)
                    
                    self.stdout.write(
                        f"{etype.upper()}: {processed} processed, "
                        f"{created} created, {updated} updated, {failed} failed"
                    )
                    
                    total_processed += processed
                    total_created += created
                    total_updated += updated
                    total_failed += failed
            
            self.stdout.write("-" * 60)
            self.stdout.write(
                f"TOTAL: {total_processed} processed, "
                f"{total_created} created, {total_updated} updated, {total_failed} failed"
            )
            
        else:
            # Display results for single entity type
            if 'error' in results:
                self.stdout.write(
                    self.style.ERROR(f"❌ Sync failed: {results['error']}")
                )
            else:
                duration = results.get('duration_seconds', 0)
                rate = results.get('records_per_second', 0)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {entity_type.upper()} sync complete: "
                        f"{results['processed']} processed, "
                        f"{results['created']} created, "
                        f"{results['updated']} updated, "
                        f"{results['failed']} failed "
                        f"in {duration:.2f}s ({rate:.1f} records/sec)"
                    )
                )
