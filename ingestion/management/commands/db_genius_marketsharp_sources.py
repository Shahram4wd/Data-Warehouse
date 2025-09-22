"""
Django management command for syncing Genius MarketSharp sources using the new sync engine architecture.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.clients.marketsharp_sources import GeniusMarketSharpSourceClient
from ingestion.sync.genius.processors.marketsharp_sources import GeniusMarketSharpSourceProcessor
from ingestion.models.genius import Genius_MarketSharpSource
from ingestion.models import SyncHistory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius MarketSharp sources data using the standardized sync engine'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
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
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite existing records (enables force overwrite mode)'
        )

    def parse_datetime_arg(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string argument"""
        if not date_str:
            return None
            
        # Try parsing as datetime first, then as date
        try:
            parsed = parse_datetime(date_str)
            if parsed:
                return parsed
                
            # If no time component, try parsing as date and add time
            from django.utils.dateparse import parse_date
            date_obj = parse_date(date_str)
            if date_obj:
                return datetime.combine(date_obj, datetime.min.time())
                
            raise ValueError(f"Could not parse datetime: {date_str}")
        except Exception as e:
            raise ValueError(f"Invalid datetime format '{date_str}': {e}")

    def create_sync_record(self, **kwargs):
        """Create a SyncHistory record for tracking the sync operation"""
        sync_record = SyncHistory.objects.create(
            crm_source='genius',
            sync_type='marketsharp_sources',
            status='running',
            start_time=timezone.now(),
            configuration={
                'full': kwargs.get('full', False),
                'since': kwargs.get('since').isoformat() if kwargs.get('since') else None,
                'command_args': kwargs
            }
        )
        logger.info(f"Created SyncHistory record {sync_record.id} for marketsharp sources sync")
        return sync_record

    def complete_sync_record(self, sync_record, stats):
        """Mark a sync operation as completed"""
        sync_record.status = 'success'
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('total_processed', 0)
        sync_record.records_created = stats.get('created', 0)
        sync_record.records_updated = stats.get('updated', 0)
        sync_record.records_failed = stats.get('errors', 0)
        sync_record.save()
        logger.info(f"Completed SyncHistory record {sync_record.id} with {stats.get('total_processed', 0)} records processed")
        return sync_record

    def fail_sync_record(self, sync_record, error_message):
        """Mark a sync operation as failed"""
        sync_record.status = 'failed'
        sync_record.end_time = timezone.now()
        sync_record.error_message = error_message[:500]  # Truncate if too long
        sync_record.save()
        logger.error(f"Failed SyncHistory record {sync_record.id}: {error_message}")
        return sync_record

    def get_last_sync_timestamp(self):
        """Get the timestamp of the last successful sync"""
        last_sync = SyncHistory.objects.filter(
            crm_source='genius',
            sync_type='marketsharp_sources', 
            status='success'
        ).order_by('-end_time').first()
        
        if last_sync:
            logger.info(f"Last successful sync: {last_sync.end_time}")
            return last_sync.end_time
        else:
            logger.info("No previous successful sync found")
            return None

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Set up logging
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        
        # Handle dry run
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Show flag modes
        if options.get('force'):
            self.stdout.write("🔄 FORCE MODE - Overwriting existing records")
        if options.get('full'):
            self.stdout.write("📋 FULL SYNC - Ignoring last sync timestamp")
        
        # Parse datetime arguments
        since = self.parse_datetime_arg(options.get('since'))
        start_date = self.parse_datetime_arg(options.get('start_date'))
        end_date = self.parse_datetime_arg(options.get('end_date'))
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Initialize sync tracking
        sync_record = None
        try:
            sync_record = self.create_sync_record(
                full=options.get('full', False),
                since=since
            )
            
            # Process data in chunks
            client = GeniusMarketSharpSourceClient()
            processor = GeniusMarketSharpSourceProcessor(Genius_MarketSharpSource)
            all_stats = {
                'total_processed': 0,
                'created': 0,
                'updated': 0,
                'errors': 0,
                'skipped': 0
            }
            
            # Get data from database
            debug = options.get('debug', False)
            if debug:
                logger.info("Fetching MarketSharp sources from Genius database...")
                
            raw_records = []
            for chunk in client.get_marketsharp_sources_chunked(
                since_date=since,
                chunk_size=1000
            ):
                raw_records.extend(chunk)
                
                # Respect max_records limit if specified
                if options.get('max_records') and len(raw_records) >= options['max_records']:
                    raw_records = raw_records[:options['max_records']]
                    break
            
            if debug:
                logger.info(f"Retrieved {len(raw_records)} raw records")
            
            # Convert tuples to dictionaries using field mapping
            field_mapping = client.get_field_mapping()
            records = []
            for raw_record in raw_records:
                if len(raw_record) != len(field_mapping):
                    logger.warning(f"Field count mismatch: got {len(raw_record)} fields, expected {len(field_mapping)}")
                    continue
                
                record_dict = dict(zip(field_mapping, raw_record))
                records.append(record_dict)
            
            if debug:
                logger.info(f"Converted to {len(records)} dictionary records")
            
            # Process records individually (following appointment_types pattern)
            for i, record in enumerate(records):
                try:
                    # For now, let's use the validate_record method that returns the processed dict
                    # This handles both validation and transformation in one step
                    processed_record = processor.validate_record(raw_records[i], field_mapping)
                    if not processed_record:
                        all_stats['errors'] += 1
                        continue
                    
                    if debug and i < 3:  # Show first few records in debug mode
                        logger.info(f"Processed record {i+1}: {processed_record}")
                    
                    # Check if record already exists
                    try:
                        existing_obj = processor.model_class.objects.get(id=processed_record['id'])
                        # Update existing record unless we want to skip updates
                        if options.get('force', False) or not existing_obj:
                            for field, value in processed_record.items():
                                if field != 'id':  # Don't update ID field
                                    setattr(existing_obj, field, value)
                            if not options.get('dry_run', False):
                                existing_obj.save()
                            all_stats['updated'] += 1
                        else:
                            all_stats['skipped'] += 1
                            
                    except processor.model_class.DoesNotExist:
                        # Create new record
                        if not options.get('dry_run', False):
                            processor.model_class.objects.create(**processed_record)
                        all_stats['created'] += 1
                    
                    all_stats['total_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing record {i+1}: {e}")
                    all_stats['errors'] += 1
                    continue
            
            # Complete sync tracking
            if sync_record:
                self.complete_sync_record(sync_record, all_stats)
            
            # Display results
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   📊 Processed: {all_stats.get('total_processed', 0)} records")
            self.stdout.write(f"   ➕ Created: {all_stats.get('created', 0)} records")
            self.stdout.write(f"   📝 Updated: {all_stats.get('updated', 0)} records")
            self.stdout.write(f"   ❌ Errors: {all_stats.get('errors', 0)} records")
            self.stdout.write(f"   ⏭️ Skipped: {all_stats.get('skipped', 0)} records")
            
            if sync_record:
                self.stdout.write(f"   🆔 SyncHistory ID: {sync_record.id}")
            else:
                self.stdout.write("   🆔 SyncHistory ID: None")
            
        except Exception as e:
            if sync_record:
                self.fail_sync_record(sync_record, str(e))
            logger.exception("Genius MarketSharp sources sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

