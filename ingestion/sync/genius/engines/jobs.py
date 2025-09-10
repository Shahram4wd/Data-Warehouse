"""
Job sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.jobs import GeniusJobClient
from ..processors.jobs import GeniusJobProcessor
from ingestion.models import Genius_Job

logger = logging.getLogger(__name__)


class GeniusJobSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius job data"""
    
    def __init__(self):
        super().__init__('jobs')
        self.client = GeniusJobClient()
        self.processor = GeniusJobProcessor(Genius_Job)
    
    async def sync_jobs(self, since_date=None, force_overwrite=False, 
                       dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for jobs"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get jobs from source
            raw_data = await sync_to_async(self.client.get_jobs)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_data)} jobs from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process jobs but making no changes")
                stats['total_processed'] = len(raw_data)
                return stats
            
            # Process jobs in batches
            batch_size = 100
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i + batch_size]
                batch_stats = await self._process_job_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Job sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Job sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_job_batch(self, batch: List[tuple], field_mapping: List[str], 
                          force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of job records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Prepare data for bulk operations
        validated_records = []
        
        # First pass: transform and validate all records
        for raw_record in batch:
            try:
                stats['total_processed'] += 1
                
                # Transform raw data to dict
                record_data = self.processor.transform_record(raw_record, field_mapping)
                
                # Validate the record
                validated_record = self.processor.validate_record(record_data)
                
                validated_records.append(validated_record)
                
            except Exception as e:
                logger.error(f"Error processing job record {raw_record}: {e}")
                stats['errors'] += 1
                continue
        
        if validated_records:
            # Perform bulk upsert
            upsert_stats = self._bulk_upsert_records(validated_records, force_overwrite)
            stats['created'] += upsert_stats['created']
            stats['updated'] += upsert_stats['updated']
        
        return stats
    
    def _bulk_upsert_records(self, validated_records: List[dict], force_overwrite: bool) -> Dict[str, int]:
        """Perform bulk upsert of job records"""
        stats = {'created': 0, 'updated': 0}
        
        if not validated_records:
            return stats
        
        # Get existing records using 'id' field (not 'genius_id')
        record_ids = [record.get('id') for record in validated_records if record.get('id')]
        existing_jobs = {
            job.id: job 
            for job in Genius_Job.objects.filter(id__in=record_ids)
        }
        
        # Prepare records for bulk operations
        records_to_create = []
        records_to_update = []
        
        for record in validated_records:
            record_id = record.get('id')
            if not record_id:
                logger.warning("Skipping record without id")
                continue
            
            if record_id in existing_jobs:
                # Existing record - check if update needed
                existing_job = existing_jobs[record_id]
                if force_overwrite or self._should_update_job(existing_job, record):
                    # Update the existing object
                    for field, value in record.items():
                        if hasattr(existing_job, field):
                            setattr(existing_job, field, value)
                    records_to_update.append(existing_job)
            else:
                # New record
                records_to_create.append(Genius_Job(**record))
        
        # Perform bulk operations
        with transaction.atomic():
            # Bulk create new records
            if records_to_create:
                created_jobs = Genius_Job.objects.bulk_create(
                    records_to_create,
                    batch_size=100,
                    ignore_conflicts=False
                )
                stats['created'] = len(created_jobs)
                logger.info(f"Created {len(created_jobs)} jobs")
            
            # Bulk update existing records
            if records_to_update:
                update_fields = ['status', 'contract_amount', 'start_date', 'end_date', 
                               'add_user_id', 'add_date', 'updated_at', 'service_id']
                # Filter fields that exist on the model
                valid_fields = [f for f in update_fields if hasattr(Genius_Job, f)]
                
                Genius_Job.objects.bulk_update(
                    records_to_update,
                    valid_fields,
                    batch_size=100
                )
                stats['updated'] = len(records_to_update)
                logger.info(f"Updated {len(records_to_update)} jobs")
        
        return stats

    def _should_update_job(self, existing: Genius_Job, new_data: Dict[str, Any]) -> bool:
        """Check if job should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes using correct field names
        fields_to_check = ['status', 'contract_amount', 'start_date', 'end_date', 
                          'prospect_id', 'division_id', 'add_user_id', 'add_date', 'service_id']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
