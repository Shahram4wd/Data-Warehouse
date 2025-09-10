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
            dg.id: dg for dg in Genius_DivisionGroup.objects.all()
        }
        
        # Prepare data for bulk operations
        validated_records = []
        
        # First pass: transform and validate all records
        for raw_record in batch:
            try:
                stats['total_processed'] += 1
                
                # Transform raw data to dict
                record_data = self.processor.transform_record(raw_record, field_mapping)
                
                # Validate record
                validated_data = self.processor.validate_record(record_data)
                
                # Skip if required data missing
                if not validated_data.get('id'):
                    logger.warning("Skipping division with no ID")
                    stats['skipped'] += 1
                    continue
                
                validated_records.append(validated_data)
                
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error processing division record: {e}")
                logger.error(f"Record data: {raw_record}")
        
        if not validated_records:
            return stats
        
        with transaction.atomic():
            if force_overwrite:
                # Force overwrite: use bulk_create with update_conflicts
                division_objects = [Genius_Division(**data) for data in validated_records]
                Genius_Division.objects.bulk_create(
                    division_objects,
                    update_conflicts=True,
                    update_fields=['group_id', 'region_id', 'label', 'abbreviation', 'is_utility', 
                                   'is_corp', 'is_omniscient', 'is_inactive', 'account_scheduler_id',
                                   'created_at', 'updated_at'],
                    unique_fields=['id'],
                    batch_size=100
                )
                stats['updated'] = len(validated_records)
                logger.debug(f"Bulk upserted {len(validated_records)} divisions with force overwrite")
            else:
                # Regular upsert: separate new and existing records
                existing_ids = set(Genius_Division.objects.filter(
                    id__in=[r['id'] for r in validated_records]
                ).values_list('id', flat=True))
                
                new_records = [r for r in validated_records if r['id'] not in existing_ids]
                existing_records = [r for r in validated_records if r['id'] in existing_ids]
                
                # Bulk create new records
                if new_records:
                    division_objects = [Genius_Division(**data) for data in new_records]
                    Genius_Division.objects.bulk_create(division_objects, batch_size=100)
                    stats['created'] = len(new_records)
                    logger.debug(f"Bulk created {len(new_records)} new divisions")
                
                # Check existing records for updates
                updated_count = 0
                for validated_data in existing_records:
                    try:
                        division = Genius_Division.objects.get(id=validated_data['id'])
                        if self._should_update_division(division, validated_data):
                            for field, value in validated_data.items():
                                if field != 'id':  # Don't update primary key
                                    setattr(division, field, value)
                            division.save()
                            updated_count += 1
                        else:
                            stats['skipped'] += 1
                    except Genius_Division.DoesNotExist:
                        # Record was deleted between queries, create it
                        Genius_Division.objects.create(**validated_data)
                        stats['created'] += 1
                
                stats['updated'] = updated_count
        
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
