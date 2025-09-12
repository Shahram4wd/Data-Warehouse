"""
Django management command for syncing Genius marketing sources using the new sync engine architecture.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.clients.marketing_sources import GeniusMarketingSourceClient
from ingestion.sync.genius.processors.marketing_sources import GeniusMarketingSourceProcessor
from ingestion.models.genius import Genius_MarketingSource
from ingestion.models import SyncHistory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius marketing sources data using the standardized sync engine'

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
            help='Force overwrite mode - completely replace existing records'
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

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Set up logging
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
            self.stdout.write("🐛 DEBUG MODE - Verbose logging enabled")
        
        # Handle dry run
        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No database changes will be made")
        
        # Handle force mode
        if options.get('force'):
            self.stdout.write("🔄 FORCE MODE - Overwriting existing records")
        
        # Parse datetime arguments
        since = self.parse_datetime_arg(options.get('since'))
        start_date = self.parse_datetime_arg(options.get('start_date'))
        end_date = self.parse_datetime_arg(options.get('end_date'))
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Execute sync
        try:
            result = self.execute_sync(
                full=options.get('full', False),
                since=since,
                start_date=start_date,
                end_date=end_date,
                max_records=options.get('max_records'),
                dry_run=options.get('dry_run', False),
                debug=options.get('debug', False)
            )
            
            # Display results
            stats = result['stats']
            self.stdout.write("✅ Sync completed successfully:")
            self.stdout.write(f"   📊 Processed: {stats['processed']} records")
            self.stdout.write(f"   ➕ Created: {stats['created']} records")
            self.stdout.write(f"   📝 Updated: {stats['updated']} records")
            self.stdout.write(f"   ❌ Errors: {stats['errors']} records")
            self.stdout.write(f"   🆔 SyncHistory ID: {result['sync_id']}")
            
        except Exception as e:
            logger.exception("Genius marketing sources sync failed")
            self.stdout.write(
                self.style.ERROR(f"❌ Sync failed: {str(e)}")
            )
            raise

    def execute_sync(self, **kwargs):
        """Execute the sync operation"""
        
        # Extract parameters
        full = kwargs.get('full', False)
        since = kwargs.get('since')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        max_records = kwargs.get('max_records')
        dry_run = kwargs.get('dry_run', False)
        debug = kwargs.get('debug', False)
        
        logger.info(f"Starting marketing sources sync (full={full}, dry_run={dry_run})")
        
        # Initialize stats
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
        }
        
        # Create sync record
        sync_record = self.create_sync_record({
            'full': full,
            'since': since.isoformat() if since else None,
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'max_records': max_records,
            'dry_run': dry_run
        })
        
        try:
            # Initialize client and processor
            client = GeniusMarketingSourceClient()
            processor = GeniusMarketingSourceProcessor(Genius_MarketingSource)
            
            # Determine sync timestamp
            sync_start = start_date or since
            if not sync_start and not full:
                sync_start = self.get_last_sync_timestamp()
            
            if debug:
                logger.info(f"Sync parameters: full={full}, sync_start={sync_start}")
            
            # Fetch data from Genius database
            logger.info("Fetching marketing sources from Genius database...")
            raw_records = client.get_marketing_sources(
                since_date=sync_start,
                limit=max_records or 0
            )
            
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
            
            # Process records in chunks
            chunk_size = 100000  # 100K records per chunk
            batch_size = 500     # 500 records per batch for bulk operations
            
            for chunk_start in range(0, len(records), chunk_size):
                chunk_end = min(chunk_start + chunk_size, len(records))
                chunk_records = records[chunk_start:chunk_end]
                
                if debug:
                    logger.info(f"Processing chunk {chunk_start//chunk_size + 1}: records {chunk_start+1}-{chunk_end}")
                
                # Process chunk in batches
                objects_to_create = []
                objects_to_update = []
                
                for i, record in enumerate(chunk_records, start=chunk_start):
                    try:
                        # Transform and validate record
                        if not processor.validate_record(record):
                            stats['errors'] += 1
                            continue
                        
                        transformed_record = processor.transform_record(record)
                        
                        if debug and i < 3:  # Show first few records in debug mode
                            logger.info(f"Transformed record {i+1}: {transformed_record}")
                        
                        # Prepare for bulk operation
                        record_id = transformed_record.get('id')
                        if record_id:
                            # Check if record exists
                            try:
                                if Genius_MarketingSource.objects.filter(id=record_id).exists():
                                    # Update existing record
                                    obj, created = Genius_MarketingSource.objects.get_or_create(
                                        id=record_id,
                                        defaults=transformed_record
                                    )
                                    if not created:
                                        for field, value in transformed_record.items():
                                            setattr(obj, field, value)
                                        objects_to_update.append(obj)
                                else:
                                    # Create new record
                                    objects_to_create.append(Genius_MarketingSource(**transformed_record))
                            except Exception as e:
                                logger.error(f"Error checking existing record {record_id}: {e}")
                                stats['errors'] += 1
                                continue
                        
                        stats['processed'] += 1
                        
                        # Process batch when it reaches batch_size
                        if len(objects_to_create) + len(objects_to_update) >= batch_size:
                            batch_stats = self._process_batch(objects_to_create, objects_to_update, dry_run, debug)
                            stats['created'] += batch_stats['created']
                            stats['updated'] += batch_stats['updated']
                            stats['errors'] += batch_stats['errors']
                            objects_to_create = []
                            objects_to_update = []
                    
                    except Exception as e:
                        logger.error(f"Error processing record {i+1}: {e}")
                        stats['errors'] += 1
                        continue
                
                # Process remaining records in the chunk
                if objects_to_create or objects_to_update:
                    batch_stats = self._process_batch(objects_to_create, objects_to_update, dry_run, debug)
                    stats['created'] += batch_stats['created']
                    stats['updated'] += batch_stats['updated']
                    stats['errors'] += batch_stats['errors']
            
            # Complete sync record with success
            self.complete_sync_record(sync_record, stats)
            
            logger.info(f"Completed marketing sources sync: {stats['processed']} processed, "
                       f"{stats['created']} created, {stats['updated']} updated, {stats['errors']} errors")
            
            return {
                'stats': stats,
                'sync_id': sync_record.id,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.fail_sync_record(sync_record, str(e))
            raise

    def create_sync_record(self, configuration):
        """Create a new sync record"""
        return SyncHistory.objects.create(
            crm_source='genius',
            sync_type=r'marketing_sources',
            status='running',
            start_time=timezone.now(),
            configuration=configuration
        )
    
    def complete_sync_record(self, sync_record, stats):
        """Mark sync record as completed"""
        sync_record.status = 'success'
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats['processed']
        sync_record.records_created = stats['created'] 
        sync_record.records_updated = stats['updated']
        sync_record.records_failed = stats['errors']
        sync_record.save()
    
    def fail_sync_record(self, sync_record, error_message):
        """Mark sync record as failed"""
        sync_record.status = 'failed'
        sync_record.end_time = timezone.now()
        sync_record.error_message = error_message
        sync_record.save()
    
    def get_last_sync_timestamp(self):
        """Get the timestamp of the last successful sync"""
        last_sync = SyncHistory.objects.filter(
            crm_source='genius',
            sync_type=r'marketing_sources',
            status='success'
        ).order_by('-end_time').first()
        
        return last_sync.end_time if last_sync else None

    def _process_batch(self, objects_to_create, objects_to_update, dry_run, debug):
        """Process a batch of objects for creation/update"""
        batch_stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        if dry_run:
            # In dry-run mode, just count what would be processed
            batch_stats['created'] = len(objects_to_create)
            batch_stats['updated'] = len(objects_to_update)
            if debug:
                logger.info(f"DRY-RUN: Would create {len(objects_to_create)} and update {len(objects_to_update)} records")
            return batch_stats
        
        # Create new records
        if objects_to_create:
            try:
                created_objects = Genius_MarketingSource.objects.bulk_create(
                    objects_to_create, 
                    ignore_conflicts=True
                )
                batch_stats['created'] = len(created_objects)
                if debug:
                    logger.info(f"Created {len(created_objects)} new marketing source records")
                    
            except Exception as e:
                logger.error(f"Error creating marketing source records: {e}")
                batch_stats['errors'] += len(objects_to_create)
        
        # Update existing records
        if objects_to_update:
            try:
                for obj in objects_to_update:
                    obj.save()
                    batch_stats['updated'] += 1
                if debug:
                    logger.info(f"Updated {batch_stats['updated']} existing marketing source records")
                    
            except Exception as e:
                logger.error(f"Error updating marketing source records: {e}")
                batch_stats['errors'] += len(objects_to_update)
        
        return batch_stats

