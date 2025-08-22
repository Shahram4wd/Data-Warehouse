"""
Division Group sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.division_groups import GeniusDivisionGroupClient
from ..processors.division_groups import GeniusDivisionGroupProcessor
from ingestion.models import Genius_DivisionGroup

logger = logging.getLogger(__name__)


class GeniusDivisionGroupSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius division group data"""
    
    def __init__(self):
        super().__init__('division_groups')
        self.client = GeniusDivisionGroupClient()
        self.processor = GeniusDivisionGroupProcessor(Genius_DivisionGroup)
    
    async def sync_division_groups(self, since_date=None, force_overwrite=False, 
                                 dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for division groups"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get division groups from source
            raw_division_groups = await sync_to_async(self.client.get_division_groups)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_division_groups)} division groups from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process division groups but making no changes")
                return stats
            
            # Process division groups in batches
            batch_size = 500
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_division_groups), batch_size):
                batch = raw_division_groups[i:i + batch_size]
                batch_stats = await self._process_division_group_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Division group sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Division group sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_division_group_batch(self, batch: List[tuple], field_mapping: List[str], 
                                    force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of division group records"""
        
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
                        logger.warning("Skipping division group with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Get or create division group
                    division_group, created = Genius_DivisionGroup.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created division group {division_group.genius_id}: {division_group.name}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_division_group(division_group, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(division_group, field, value)
                            division_group.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated division group {division_group.genius_id}: {division_group.name}")
                        else:
                            stats['skipped'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing division group record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_division_group(self, existing: Genius_DivisionGroup, new_data: Dict[str, Any]) -> bool:
        """Check if division group should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['name', 'code', 'active']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
