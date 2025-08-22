"""
Division sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.divisions import GeniusDivisionClient
from ..processors.divisions import GeniusDivisionProcessor
from ingestion.models import Genius_Division, Genius_DivisionGroup

logger = logging.getLogger(__name__)


class GeniusDivisionSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius division data"""
    
    def __init__(self):
        super().__init__('divisions')
        self.client = GeniusDivisionClient()
        self.processor = GeniusDivisionProcessor(Genius_Division)
    
    async def sync_divisions(self, since_date=None, force_overwrite=False, 
                           dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for divisions"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get divisions from source
            raw_divisions = await sync_to_async(self.client.get_divisions)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_divisions)} divisions from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process divisions but making no changes")
                return stats
            
            # Process divisions in batches
            batch_size = 500
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_divisions), batch_size):
                batch = raw_divisions[i:i + batch_size]
                batch_stats = await self._process_division_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Division sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Division sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_division_batch(self, batch: List[tuple], field_mapping: List[str], 
                               force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of division records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Preload division groups for FK validation
        division_groups = {
            dg.genius_id: dg for dg in Genius_DivisionGroup.objects.all()
        }
        
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
                        logger.warning("Skipping division with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Get or create division
                    division, created = Genius_Division.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created division {division.genius_id}: {division.name}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_division(division, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(division, field, value)
                            division.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated division {division.genius_id}: {division.name}")
                        else:
                            stats['skipped'] += 1
                    
                    # Set division group relationship if exists
                    if validated_data.get('division_group_id'):
                        division_group = division_groups.get(validated_data['division_group_id'])
                        if division_group:
                            division.division_group = division_group
                            division.save(update_fields=['division_group'])
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing division record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_division(self, existing: Genius_Division, new_data: Dict[str, Any]) -> bool:
        """Check if division should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['name', 'code', 'active', 'division_group_id']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
