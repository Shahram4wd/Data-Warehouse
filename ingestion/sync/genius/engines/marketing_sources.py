"""
Marketing Sources sync engine for Genius CRM following CRM sync guide architecture
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.marketing_sources import GeniusMarketingSourceClient
from ..processors.marketing_sources import GeniusMarketingSourceProcessor

logger = logging.getLogger(__name__)


class GeniusMarketingSourcesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius marketing source data following established patterns"""
    
    def __init__(self):
        super().__init__('marketing_sources')
        self.client = GeniusMarketingSourceClient()
        
        # Import the model here to avoid circular imports
        from ingestion.models.genius import Genius_MarketingSource
        self.processor = GeniusMarketingSourceProcessor(Genius_MarketingSource)
        
        # Configuration constants (no separate config class needed)
        self.DEFAULT_CHUNK_SIZE = 1000
        self.BATCH_SIZE = 500
    
    async def execute_sync(self, 
                          full: bool = False,
                          force: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False,
                          **kwargs) -> Dict[str, Any]:
        """Execute the marketing sources sync process"""
        
        # Determine since_date based on full flag
        since_date = None if full else since
        
        return await self.sync_marketing_sources(
            since_date=since_date, 
            force_overwrite=force,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
    async def sync_marketing_sources(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for marketing sources"""
        
        logger.info(f"Starting marketing sources sync - since_date: {since_date}, "
                   f"force_overwrite: {force_overwrite}, dry_run: {dry_run}, "
                   f"max_records: {max_records}")
        
        # Initialize stats
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        try:
            # Get data from client
            raw_data = await sync_to_async(self.client.get_marketing_sources)(
                since_date=since_date,
                limit=max_records or 0
            )
            
            if not raw_data:
                logger.info("No marketing sources data retrieved")
                return stats
            
            logger.info(f"Retrieved {len(raw_data)} marketing sources")
            stats['total_processed'] = len(raw_data)
            
            if dry_run:
                logger.info(f"DRY RUN: Would process {len(raw_data)} records")
                return stats
            
            # Process data
            batch_stats = await self._process_marketing_sources_batch(
                raw_data, self.client.get_field_mapping(), force_overwrite
            )
            
            # Update stats
            stats.update(batch_stats)
            
        except Exception as e:
            logger.error(f"Error in sync_marketing_sources: {e}")
            stats['errors'] += 1
            raise
        
        logger.info(f"Marketing sources sync completed - Stats: {stats}")
        return stats

    @sync_to_async
    def _process_marketing_sources_batch(self, batch: List[tuple], field_mapping: List[str], 
                          force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of marketing source records"""
        
        # Validate and transform records
        validated_records = []
        for record_tuple in batch:
            try:
                record = self.processor.validate_record(record_tuple, field_mapping)
                if record:
                    validated_records.append(record)
            except Exception as e:
                logger.error(f"Error validating marketing source record: {e}")
                continue
        
        if not validated_records:
            logger.warning("No valid marketing source records to process")
            return {'created': 0, 'updated': 0}
        
        # Perform bulk upsert
        return self._bulk_upsert_records(validated_records, force_overwrite)

    def _bulk_upsert_records(self, validated_records: List[dict], force_overwrite: bool) -> Dict[str, int]:
        """Perform bulk upsert of marketing source records using modern bulk_create with update_conflicts"""
        
        from ingestion.models.genius import Genius_MarketingSource
        from django.db import transaction
        
        stats = {'created': 0, 'updated': 0}
        
        if not validated_records:
            return stats
        
        try:
            with transaction.atomic():
                # Process in batches
                batch_size = self.BATCH_SIZE
                for i in range(0, len(validated_records), batch_size):
                    batch = validated_records[i:i + batch_size]
                    
                    # Prepare model instances
                    marketing_source_instances = []
                    for record in batch:
                        marketing_source_instances.append(Genius_MarketingSource(**record))
                    
                    # Bulk create with conflict resolution
                    update_fields = [
                        'type_id', 'label', 'description', 'start_date', 'end_date',
                        'add_user_id', 'add_date', 'is_active', 'is_allow_lead_modification',
                        'updated_at', 'sync_updated_at'
                    ]
                    
                    created_marketing_sources = Genius_MarketingSource.objects.bulk_create(
                        marketing_source_instances,
                        update_conflicts=True,
                        update_fields=update_fields,
                        unique_fields=['id']
                    )
                    
                    # Count results
                    batch_created = sum(1 for ms in created_marketing_sources if ms._state.adding)
                    stats['created'] += batch_created
                    stats['updated'] += len(batch) - batch_created
                    
                    logger.info(f"Bulk upsert completed - Created: {batch_created}, "
                              f"Updated: {len(batch) - batch_created}")
                
        except Exception as e:
            logger.error(f"Error in bulk upsert: {e}")
            raise
        
        logger.info(f"Bulk upsert completed - Created: {stats['created']}, "
                   f"Updated: {stats['updated']}")
        return stats

