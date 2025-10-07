"""
Django management command for syncing Genius prospect sources using the standardized sync engine.
This command follows the CRM sync guide patterns for consistent data synchronization.
"""
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ingestion.sync.genius.clients.prospect_sources import GeniusProspectSourceClient
from ingestion.sync.genius.processors.prospect_sources import GeniusProspectSourceProcessor
from ingestion.models.genius import Genius_ProspectSource
from ingestion.models import SyncHistory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Genius prospect sources data using the standardized sync engine'

    def add_arguments(self, parser):
        """Add command arguments following CRM sync guide standards"""
        
        # Core sync flags (distinct purposes)
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp) - fetches ALL records'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Completely replace existing records - enables force overwrite mode'
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
        
        # Handle flag combinations
        if options.get('full') and options.get('force'):
            self.stdout.write("🚀 FULL SYNC + FORCE OVERWRITE MODE - Fetching all records and replacing existing data")
        elif options.get('full'):
            self.stdout.write("📊 FULL SYNC MODE - Fetching all records but respecting existing data")
        elif options.get('force'):
            self.stdout.write("💪 FORCE OVERWRITE MODE - Replacing existing records with fetched data")
        
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
            logger.exception("Genius prospect sources sync failed")
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
        
        logger.info(f"Starting prospect sources sync (full={full}, dry_run={dry_run})")
        
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
            client = GeniusProspectSourceClient()
            processor = GeniusProspectSourceProcessor(Genius_ProspectSource)
            
            # Determine sync timestamp
            sync_start = start_date or since
            if not sync_start and not full:
                sync_start = self.get_last_sync_timestamp()
            
            if debug:
                logger.info(f"Sync parameters: full={full}, sync_start={sync_start}")
            
            # Fetch data from Genius database using chunked streaming approach
            logger.info("Fetching prospect sources from Genius database...")
            
            # Initialize counters for progress tracking
            total_chunks_processed = 0
            chunk_size = 1000  # Fetch in smaller chunks for memory efficiency
            
            # Use chunked streaming processing following CRM sync guide
            for chunk_records in client.get_prospect_sources_chunked(
                since_date=sync_start,
                chunk_size=chunk_size
            ):
                total_chunks_processed += 1
                
                if debug:
                    logger.info(f"Processing chunk {total_chunks_processed}: {len(chunk_records)} records")
                
                # Convert tuples to dictionaries using field mapping
                field_mapping = client.get_field_mapping()
                records = []
                for raw_record in chunk_records:
                    if len(raw_record) != len(field_mapping):
                        logger.warning(f"Field count mismatch: got {len(raw_record)} fields, expected {len(field_mapping)}")
                        continue
                    
                    record_dict = dict(zip(field_mapping, raw_record))
                    records.append(record_dict)
                
                if debug:
                    logger.info(f"Converted chunk {total_chunks_processed} to {len(records)} dictionary records")
                
                # Process chunk in batches for optimal database performance
                batch_size = 500     # 500 records per batch for bulk operations
                
                # Collect all records for bulk processing
                records_to_process = []
                
                for i, record in enumerate(records):
                    try:
                        # Transform and validate record
                        if not processor.validate_record(record):
                            stats['errors'] += 1
                            continue
                        
                        transformed_record = processor.transform_record(record)
                        
                        if debug and i < 3 and total_chunks_processed == 1:  # Show first few records in debug mode
                            logger.info(f"Transformed record {i+1}: {transformed_record}")
                        
                        # Add to batch for bulk processing
                        records_to_process.append(transformed_record)
                        stats['processed'] += 1
                        
                        # Process batch when it reaches batch_size
                        if len(records_to_process) >= batch_size:
                            batch_stats = self._process_batch_bulk_upsert(records_to_process, dry_run, debug)
                            stats['created'] += batch_stats['created']
                            stats['updated'] += batch_stats['updated']
                            stats['errors'] += batch_stats['errors']
                            records_to_process = []
                        
                        # Respect max_records limit if specified
                        if max_records and stats['processed'] >= max_records:
                            break
                    
                    except Exception as e:
                        logger.error(f"Error processing record {i+1} in chunk {total_chunks_processed}: {e}")
                        stats['errors'] += 1
                        continue
                
                # Process remaining records in the chunk
                if records_to_process:
                    batch_stats = self._process_batch_bulk_upsert(records_to_process, dry_run, debug)
                    stats['created'] += batch_stats['created']
                    stats['updated'] += batch_stats['updated']
                    stats['errors'] += batch_stats['errors']
                
                # Break if we've reached max_records limit
                if max_records and stats['processed'] >= max_records:
                    logger.info(f"Reached max_records limit of {max_records}, stopping sync")
                    break
            
            # Complete sync record with success
            self.complete_sync_record(sync_record, stats)
            
            logger.info(f"Completed prospect sources sync: {stats['processed']} processed, "
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
            sync_type=r'prospect_sources',
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
            sync_type=r'prospect_sources',
            status='success'
        ).order_by('-end_time').first()
        
        return last_sync.end_time if last_sync else None

    def _process_batch_bulk_upsert(self, records, dry_run, debug):
        """Process a batch of records using efficient bulk upsert operations"""
        from django.db import transaction
        
        batch_stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        if dry_run:
            # In dry-run mode, just count what would be processed
            batch_stats['created'] = len(records)  # Assume all would be processed
            if debug:
                logger.info(f"DRY-RUN: Would process {len(records)} records with bulk upsert")
            return batch_stats
        
        if not records:
            return batch_stats
        
        try:
            with transaction.atomic():
                # Use bulk_create with update_conflicts for efficient upsert
                # This is much faster than individual saves or get_or_create calls
                
                # Get the field names from the model (excluding auto-generated fields)
                model_fields = [f.name for f in Genius_ProspectSource._meta.fields 
                               if not f.auto_created and f.name != 'sync_created_at']
                
                # Create model instances
                objects_to_upsert = []
                for record_data in records:
                    try:
                        obj = Genius_ProspectSource(**record_data)
                        objects_to_upsert.append(obj)
                    except Exception as e:
                        logger.error(f"Error creating model instance: {e}")
                        batch_stats['errors'] += 1
                        continue
                
                if objects_to_upsert:
                    # Use bulk_create with update_conflicts for high performance upsert
                    created_objects = Genius_ProspectSource.objects.bulk_create(
                        objects_to_upsert,
                        update_conflicts=True,
                        update_fields=[f for f in model_fields if f not in ['id', 'sync_created_at']],
                        unique_fields=['id']
                    )
                    
                    # bulk_create with update_conflicts doesn't return created vs updated counts
                    # So we'll track total processed
                    total_processed = len(objects_to_upsert)
                    batch_stats['created'] = total_processed  # This includes both created and updated
                    
                    if debug:
                        logger.info(f"Bulk upserted {total_processed} prospect source records")
                        
        except Exception as e:
            logger.error(f"Error in bulk upsert operation: {e}")
            batch_stats['errors'] += len(records)
        
        return batch_stats

    def _process_batch(self, objects_to_create, objects_to_update, dry_run, debug):
        """Legacy batch processing method - kept for backward compatibility"""
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
                created_objects = Genius_ProspectSource.objects.bulk_create(
                    objects_to_create, 
                    ignore_conflicts=True
                )
                batch_stats['created'] = len(created_objects)
                if debug:
                    logger.info(f"Created {len(created_objects)} new prospect source records")
                    
            except Exception as e:
                logger.error(f"Error creating prospect source records: {e}")
                batch_stats['errors'] += len(objects_to_create)
        
        # Update existing records using bulk_update for better performance
        if objects_to_update:
            try:
                # Use bulk_update instead of individual saves
                update_fields = ['prospect_id', 'marketing_source_id', 'source_date', 'notes', 
                               'add_user_id', 'source_user_id', 'add_date', 'updated_at']
                Genius_ProspectSource.objects.bulk_update(objects_to_update, update_fields)
                batch_stats['updated'] = len(objects_to_update)
                if debug:
                    logger.info(f"Bulk updated {batch_stats['updated']} existing prospect source records")
                    
            except Exception as e:
                logger.error(f"Error updating prospect source records: {e}")
                batch_stats['errors'] += len(objects_to_update)
        
        return batch_stats

