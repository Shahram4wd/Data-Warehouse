"""
Marketing Source Types sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.marketing_source_types import GeniusMarketingSourceTypeClient
from ..processors.marketing_source_types import GeniusMarketingSourceTypeProcessor
from ingestion.models import Genius_MarketingSourceType

logger = logging.getLogger(__name__)


class GeniusMarketingSourceTypesSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius marketing source type data"""
    
    def __init__(self):
        super().__init__('marketing_source_types')
        self.client = GeniusMarketingSourceTypeClient()
        self.processor = GeniusMarketingSourceTypeProcessor(Genius_MarketingSourceType)
    
    async def execute_sync(self, 
                          full: bool = False,
                          force: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the marketing source types sync process"""
        
        # Determine since_date based on full flag  
        since_date = None if full else since
        
        return await self.sync_marketing_source_types(
            since_date=since_date, 
            force_overwrite=force,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
    async def sync_marketing_source_types(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for marketing source types"""
        
        logger.info(f"Starting marketing source types sync - since_date: {since_date}, "
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
            if max_records:
                raw_data = self.client.get_marketing_source_types(since_date, max_records)
            else:
                raw_data = self.client.get_marketing_source_types(since_date)
            
            if not raw_data:
                logger.info("No marketing source types data to process")
                return stats
            
            logger.info(f"Retrieved {len(raw_data)} marketing source types")
            stats['total_processed'] = len(raw_data)
            
            if dry_run:
                logger.info("DRY RUN: Would process marketing source types data")
                return stats
            
            # Process data
            batch_stats = await self._process_marketing_source_type_batch(
                raw_data, self.client.get_field_mapping(), force_overwrite
            )
            
            # Update stats
            stats.update(batch_stats)
            
        except Exception as e:
            logger.error(f"Marketing source types sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
        
        logger.info(f"Marketing source types sync completed - Stats: {stats}")
        return stats
    
    @sync_to_async
    def _process_marketing_source_type_batch(self, batch: List[tuple], field_mapping: List[str], 
                          force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of marketing source type records"""
        
        # Validate and transform records
        validated_records = []
        for record_tuple in batch:
            try:
                record = self.processor.validate_record(record_tuple, field_mapping)
                if record:
                    validated_records.append(record)
            except Exception as e:
                logger.error(f"Error validating marketing source type record: {e}")
                continue
        
        if not validated_records:
            logger.warning("No valid marketing source type records to process")
            return {'created': 0, 'updated': 0}
        
        # Perform bulk upsert
        return self._bulk_upsert_records(validated_records, force_overwrite)
    
    def _bulk_upsert_records(self, validated_records: List[dict], force_overwrite: bool) -> Dict[str, int]:
        """Perform bulk upsert of marketing source type records using modern bulk_create with update_conflicts"""
        
        stats = {'created': 0, 'updated': 0}
        
        if not validated_records:
            return stats
        
        try:
            # Prepare objects for bulk_create
            source_types_to_create = []
            
            for record_data in validated_records:
                # Handle NULL updated_at with current timestamp workaround
                if record_data.get('updated_at') is None:
                    record_data['updated_at'] = timezone.now()
                
                try:
                    source_type_obj = Genius_MarketingSourceType(**record_data)
                    source_types_to_create.append(source_type_obj)
                except Exception as e:
                    logger.error(f"Error creating MarketingSourceType object for id {record_data.get('id')}: {e}")
                    continue
            
            if not source_types_to_create:
                logger.warning("No valid MarketingSourceType objects to process")
                return stats
            
            # Perform bulk upsert using bulk_create with update_conflicts
            if force_overwrite:
                # Force mode: update all fields
                update_fields = ['label', 'description', 'is_active', 'list_order',
                               'created_at', 'updated_at', 'sync_updated_at']
            else:
                # Normal mode: update selective fields
                update_fields = ['updated_at', 'sync_updated_at', 'label', 'description', 
                               'is_active', 'list_order', 'created_at']
            
            # Use bulk_create with update_conflicts for efficient upsert
            with transaction.atomic():
                results = Genius_MarketingSourceType.objects.bulk_create(
                    source_types_to_create,
                    update_conflicts=True,
                    update_fields=update_fields,
                    unique_fields=['id']
                )
                
                # Count creates vs updates (bulk_create returns created objects)
                stats['created'] = len([r for r in results if r._state.adding])
                stats['updated'] = len(results) - stats['created']
                
                logger.info(f"Bulk upsert completed - Created: {stats['created']}, Updated: {stats['updated']}")
                
        except Exception as e:
            logger.error(f"Error in bulk_upsert_records: {e}")
            raise
        
        return stats

