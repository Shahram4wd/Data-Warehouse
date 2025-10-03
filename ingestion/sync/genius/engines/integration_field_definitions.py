"""
Integration Field Definition sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.integration_field_definitions import GeniusIntegrationFieldDefinitionClient
from ..processors.integration_field_definitions import GeniusIntegrationFieldDefinitionProcessor
from ingestion.models import Genius_IntegrationFieldDefinition, SyncHistory

logger = logging.getLogger(__name__)


class GeniusIntegrationFieldDefinitionsSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius integration field definition data"""
    
    def __init__(self):
        super().__init__('integration_field_definitions')
        self.client = GeniusIntegrationFieldDefinitionClient()
        self.processor = GeniusIntegrationFieldDefinitionProcessor(Genius_IntegrationFieldDefinition)
    
    def sync_integration_field_definitions(self, since_date=None, force_overwrite=False, 
                                   dry_run=False, max_records=0, full_sync=False, **kwargs) -> Dict[str, Any]:
        """Main sync method for integration field definitions
        
        Note: This table doesn't have timestamps, so delta sync is not available.
        Always performs full sync.
        """
        
        # Create sync history record
        sync_history = SyncHistory.objects.create(
            crm_source='genius',
            sync_type='integration_field_definitions',
            start_time=timezone.now(),
            status='running'
        )
        
        # This table has no timestamps, so we always do full sync
        logger.info(f"🚀 Starting integration field definitions sync")
        logger.info(f"   ⚠️  Note: This table has no timestamps - always performing full sync")
        logger.info(f"   🔄 Force overwrite: {force_overwrite}")
        logger.info(f"   🧪 Dry run: {dry_run}")
        logger.info(f"   📊 Max records: {max_records or 'unlimited'}")
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get total count for progress tracking  
            total_count = self.client.count_records()
            logger.info(f"Total integration field definitions to process: {total_count:,}")
            
            if total_count == 0:
                logger.info("No integration field definitions to sync")
                # Update sync history
                if not dry_run:
                    self.complete_sync_record(sync_history, stats)
                return stats
            
            if dry_run:
                logger.info("DRY RUN: Would process integration field definitions but making no changes")
                stats['total_processed'] = total_count
                return stats

            logger.info(f"Processing {total_count} integration field definitions using streaming approach")
            
            # Get field mapping for data transformation
            field_mapping = self.client.get_field_mapping()
            
            # Process chunks directly from the generator (streaming approach)
            batch_size = 1000  # Smaller batch size for better memory management
            records_processed = 0
            
            for chunk_num, chunk in enumerate(self.client.get_chunked_items(chunk_size=10000), 1):
                logger.info(f"📦 Processing chunk {chunk_num} ({len(chunk)} items)")
                
                if max_records and records_processed >= max_records:
                    logger.info(f"Reached max_records limit of {max_records}")
                    break
                
                try:
                    # Transform raw tuples to dictionaries using field mapping
                    transformed_batch = []
                    for raw_record in chunk:
                        if max_records and records_processed >= max_records:
                            break
                            
                        try:
                            # Convert tuple to dictionary using field mapping
                            record_dict = {}
                            for column_index, field_name in enumerate(field_mapping):
                                if column_index < len(raw_record):
                                    record_dict[field_name] = raw_record[column_index]
                            
                            transformed_batch.append(record_dict)
                            
                        except Exception as e:
                            logger.error(f"Transform failed for record {raw_record}: {e}")
                            stats['errors'] += 1
                            continue
                    
                    # Process the batch
                    if transformed_batch:
                        # Process in smaller sub-batches for better performance
                        for i in range(0, len(transformed_batch), batch_size):
                            sub_batch = transformed_batch[i:i + batch_size]
                            sub_batch_num = i // batch_size + 1
                            total_sub_batches = (len(transformed_batch) + batch_size - 1) // batch_size
                            
                            logger.info(f"  Processing sub-batch {sub_batch_num}/{total_sub_batches} ({len(sub_batch)} items)")
                            
                            logger.info(f"Bulk processing {len(sub_batch)} integration field definitions (force_overwrite={force_overwrite})")
                            batch_stats = self.processor.process_batch(sub_batch, force_overwrite=force_overwrite)
                            logger.info(f"Bulk operation completed - Created: {batch_stats['created']}, Updated: {batch_stats['updated']}")
                            
                            stats['created'] += batch_stats['created']
                            stats['updated'] += batch_stats['updated']
                            stats['errors'] += batch_stats['errors']
                            
                            records_processed += len(sub_batch)
                            
                            # Progress logging
                            if total_count > 0:
                                progress = (records_processed / total_count) * 100
                                logger.info(f"  Progress: {records_processed}/{total_count} ({progress:.1f}%)")
                    
                    stats['total_processed'] = records_processed
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_num}: {e}")
                    stats['errors'] += len(chunk)
                    
            logger.info(f"✅ Integration field definitions sync completed. Stats: {stats}")
            
            # Update sync history
            if not dry_run:
                self.complete_sync_record(sync_history, stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Integration field definition sync failed: {str(e)}")
            # Mark sync as failed
            sync_history.end_time = timezone.now()
            sync_history.status = 'failed'
            sync_history.error_message = str(e)
            sync_history.save()
            raise