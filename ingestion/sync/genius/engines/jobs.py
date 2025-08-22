"""
Job sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.jobs import GeniusJobClient
from ..processors.jobs import GeniusJobProcessor
from ingestion.models import Genius_Job, Genius_Prospect, Genius_Division, Genius_JobStatus

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
            raw_jobs = await sync_to_async(self.client.get_jobs)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_jobs)} jobs from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process jobs but making no changes")
                return stats
            
            # Process jobs in batches
            batch_size = 500
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_jobs), batch_size):
                batch = raw_jobs[i:i + batch_size]
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
        
        # Preload lookup data for FK validation
        prospects = {p.genius_id: p for p in Genius_Prospect.objects.all()}
        divisions = {d.genius_id: d for d in Genius_Division.objects.all()}
        job_statuses = {js.genius_id: js for js in Genius_JobStatus.objects.all()}
        
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
                        logger.warning("Skipping job with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Validate FK relationships exist
                    if validated_data.get('prospect_id') and validated_data['prospect_id'] not in prospects:
                        logger.warning(f"Job {validated_data['genius_id']} references non-existent prospect {validated_data['prospect_id']}")
                        stats['skipped'] += 1
                        continue
                    
                    if validated_data.get('division_id') and validated_data['division_id'] not in divisions:
                        logger.warning(f"Job {validated_data['genius_id']} references non-existent division {validated_data['division_id']}")
                        stats['skipped'] += 1
                        continue
                    
                    # Get or create job
                    job, created = Genius_Job.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created job {job.genius_id}: {job.job_number}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_job(job, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(job, field, value)
                            job.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated job {job.genius_id}: {job.job_number}")
                        else:
                            stats['skipped'] += 1
                    
                    # Set relationships
                    if validated_data.get('prospect_id'):
                        job.prospect = prospects[validated_data['prospect_id']]
                    
                    if validated_data.get('division_id'):
                        job.division = divisions[validated_data['division_id']]
                    
                    if validated_data.get('job_status_id') and validated_data['job_status_id'] in job_statuses:
                        job.job_status = job_statuses[validated_data['job_status_id']]
                    
                    job.save()
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing job record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_job(self, existing: Genius_Job, new_data: Dict[str, Any]) -> bool:
        """Check if job should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['job_number', 'contract_amount', 'start_date', 'completion_date', 
                          'prospect_id', 'division_id', 'job_status_id', 'notes']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
