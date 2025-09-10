"""
Job Status sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

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
            raw_data = await sync_to_async(self.client.get_job_statuses)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_data)} job statuses from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process job statuses but making no changes")
                stats['total_processed'] = len(raw_data)
                return stats
            
            # Process job statuses in batches
            batch_size = 100
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i + batch_size]
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
                logger.error(f"Error processing job status record {raw_record}: {e}")
                stats['errors'] += 1
                continue
        
        if validated_records:
            # Perform bulk upsert
            upsert_stats = self._bulk_upsert_records(validated_records, force_overwrite)
            stats['created'] += upsert_stats['created']
            stats['updated'] += upsert_stats['updated']
        
        return stats
    
    def _bulk_upsert_records(self, records: List[Dict[str, Any]], force: bool = False) -> Dict[str, int]:
        """Bulk upsert records with conflict resolution"""
        created_count = 0
        updated_count = 0
        
        if not records:
            return {'created': created_count, 'updated': updated_count}
        
        logger.info(f"Bulk upserting {len(records)} job status records (force={force})")
        
        # Prepare model instances
        model_instances = []
        for record in records:
            instance = Genius_JobStatus(**record)
            model_instances.append(instance)
        
        with transaction.atomic():
            # Get existing IDs BEFORE the operation to calculate created vs updated
            existing_ids = set(
                Genius_JobStatus.objects.filter(
                    id__in=[r['id'] for r in records]
                ).values_list('id', flat=True)
            )
            
            if force:
                # Force mode: overwrite all fields including sync timestamps
                logger.info("Force mode: completely overwriting records")
                Genius_JobStatus.objects.bulk_create(
                    model_instances,
                    batch_size=100,
                    update_conflicts=True,
                    unique_fields=['id'],
                    update_fields=[
                        'label', 'is_system', 'sync_created_at', 'sync_updated_at'
                    ]
                )
            else:
                # Normal mode: standard upsert, preserve sync timestamps for existing records
                Genius_JobStatus.objects.bulk_create(
                    model_instances,
                    batch_size=100,
                    update_conflicts=True,
                    unique_fields=['id'],
                    update_fields=[
                        'label', 'is_system'
                    ]
                )
            
            # Calculate created vs updated counts
            created_count = len([r for r in records if r['id'] not in existing_ids])
            updated_count = len(records) - created_count
        
        logger.info(f"Bulk upsert completed: {created_count} created, {updated_count} updated")
        return {'created': created_count, 'updated': updated_count}
