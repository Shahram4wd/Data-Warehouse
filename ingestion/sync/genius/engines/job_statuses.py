"""
Job Status sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.job_statuses import GeniusJobStatusClient
from ..processors.job_statuses import GeniusJobStatusProcessor
from ingestion.models import Genius_JobStatus

logger = logging.getLogger(__name__)


class GeniusJobStatusSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius job status data"""
    
    def __init__(self):
        super().__init__('job_statuses')
        self.client = GeniusJobStatusClient()
        self.processor = GeniusJobStatusProcessor(Genius_JobStatus)
    
    async def sync_job_statuses(self, since_date=None, force_overwrite=False, 
                               dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for job statuses"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get job statuses from source
            raw_job_statuses = await sync_to_async(self.client.get_job_statuses)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_job_statuses)} job statuses from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process job statuses but making no changes")
                return stats
            
            # Process job statuses in batches (smaller batch for lookup tables)
            batch_size = 100
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_job_statuses), batch_size):
                batch = raw_job_statuses[i:i + batch_size]
                batch_stats = await self._process_job_status_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Job status sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Job status sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_job_status_batch(self, batch: List[tuple], field_mapping: List[str], 
                                 force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of job status records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        with transaction.atomic():
            for raw_record in batch:
                try:
                    stats['total_processed'] += 1
                    
                    # Transform raw data to dict
                    record_data = self.processor.transform_record(raw_record, field_mapping)
                    
                    # Validate record
                    validated_data = self.processor.validate_record(record_data)
                    
                    # Skip if required data missing
                    if not validated_data.get('genius_id'):
                        logger.warning("Skipping job status with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Get or create job status
                    job_status, created = Genius_JobStatus.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created job status {job_status.genius_id}: {job_status.name}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_job_status(job_status, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(job_status, field, value)
                            job_status.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated job status {job_status.genius_id}: {job_status.name}")
                        else:
                            stats['skipped'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing job status record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_job_status(self, existing: Genius_JobStatus, new_data: Dict[str, Any]) -> bool:
        """Check if job status should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['name', 'code', 'active', 'sort_order']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
