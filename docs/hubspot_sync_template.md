# HubSpot Sync Command Template

This template shows how to implement HubSpot sync commands following the unified architecture with force overwrite support.

## Base Command Structure

```python
# ingestion/management/commands/sync_hubspot_[entity].py
from ingestion.management.commands.base_hubspot_sync import BaseHubSpotSyncCommand
from ingestion.sync.hubspot.engines.[entity] import HubSpot[Entity]SyncEngine

class Command(BaseHubSpotSyncCommand):
    """Sync [entity] from HubSpot using new architecture
    
    Examples:
        # Standard incremental sync
        python manage.py sync_hubspot_[entity]
        
        # Full sync (fetch all records, but respect local timestamps)
        python manage.py sync_hubspot_[entity] --full
        
        # Force overwrite ALL records (fetch all + ignore local timestamps)
        python manage.py sync_hubspot_[entity] --full --force-overwrite
        
        # Force overwrite recent records only
        python manage.py sync_hubspot_[entity] --since=2025-01-01 --force-overwrite
    """
    
    help = """Sync [entity] from HubSpot API using the new unified architecture.
    
Use --force-overwrite to completely overwrite existing records, ignoring timestamps.
This ensures all data is replaced with the latest from HubSpot."""
    
    def get_sync_engine(self, **options):
        """Get the [entity] sync engine"""
        return HubSpot[Entity]SyncEngine(
            batch_size=options.get('batch_size', 100),
            dry_run=options.get('dry_run', False),
            force_overwrite=options.get('force_overwrite', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "[entity]"
```

## Sync Engine Structure

```python
# ingestion/sync/hubspot/engines/[entity].py
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.clients.[entity] import HubSpot[Entity]Client
from ingestion.sync.hubspot.processors.[entity] import HubSpot[Entity]Processor
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
from ingestion.models.hubspot import Hubspot_[Entity]

logger = logging.getLogger(__name__)

class HubSpot[Entity]SyncEngine(HubSpotBaseSyncEngine):
    """Sync engine for HubSpot [entity]"""
    
    def __init__(self, **kwargs):
        super().__init__('[entity]', **kwargs)
        self.force_overwrite = kwargs.get('force_overwrite', False)
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot [entity] client and processor"""
        await self.initialize_enterprise_features()
        
        self.client = HubSpot[Entity]Client()
        await self.create_authenticated_session(self.client)
        self.processor = HubSpot[Entity]Processor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch [entity] data from HubSpot"""
        # Implementation specific to entity
        pass
        
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform [entity] data"""
        # Implementation specific to entity
        pass
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate [entity] data"""
        # Implementation specific to entity
        pass
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save [entity] data to database with force overwrite support"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not validated_data:
            return results
        
        try:
            if self.force_overwrite:
                logger.info("Force overwrite mode - all records will be updated regardless of timestamps")
                results = await self._force_overwrite_[entity](validated_data)
            else:
                results = await self._bulk_save_[entity](validated_data)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed, falling back to individual saves: {bulk_error}")
            if self.force_overwrite:
                results = await self._individual_force_save_[entity](validated_data)
            else:
                results = await self._individual_save_[entity](validated_data)
        
        return results
    
    async def _force_overwrite_[entity](self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite all [entity] using bulk operations, ignoring timestamps"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        # Get all existing [entity] IDs that we're about to process
        [entity]_ids = [record['id'] for record in validated_data if record.get('id')]
        
        try:
            # Get existing [entity] to determine which are updates vs creates
            existing_[entity] = await sync_to_async(list)(
                Hubspot_[Entity].objects.filter(id__in=[entity]_ids).values_list('id', flat=True)
            )
            existing_[entity]_set = set(existing_[entity])
            
            # Separate new vs existing records
            new_records = [record for record in validated_data if record.get('id') not in existing_[entity]_set]
            update_records = [record for record in validated_data if record.get('id') in existing_[entity]_set]
            
            # Force create new records
            if new_records:
                new_[entity]_objects = [Hubspot_[Entity](**record) for record in new_records]
                await sync_to_async(Hubspot_[Entity].objects.bulk_create)(
                    new_[entity]_objects,
                    batch_size=self.batch_size
                )
                results['created'] = len(new_records)
                logger.info(f"Force created {results['created']} new [entity]")
            
            # Force update existing records - delete and recreate for true overwrite
            if update_records:
                # Delete existing records first
                await sync_to_async(Hubspot_[Entity].objects.filter(id__in=[r['id'] for r in update_records]).delete)()
                
                # Recreate with new data
                update_[entity]_objects = [Hubspot_[Entity](**record) for record in update_records]
                await sync_to_async(Hubspot_[Entity].objects.bulk_create)(
                    update_[entity]_objects,
                    batch_size=self.batch_size
                )
                results['updated'] = len(update_records)
                logger.info(f"Force overwritten {results['updated']} existing [entity]")
                
        except Exception as e:
            logger.error(f"Force bulk overwrite failed: {e}")
            results['failed'] = len(validated_data)
            
        return results
    
    async def _individual_force_save_[entity](self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite [entity] individually, ignoring timestamps"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                [entity]_id = record.get('id')
                if not [entity]_id:
                    logger.error(f"[Entity] record missing ID: {record}")
                    results['failed'] += 1
                    continue
                
                # Check if [entity] exists
                [entity]_exists = await sync_to_async(Hubspot_[Entity].objects.filter(id=[entity]_id).exists)()
                
                if [entity]_exists:
                    # Force delete and recreate for complete overwrite
                    await sync_to_async(Hubspot_[Entity].objects.filter(id=[entity]_id).delete)()
                    [entity] = Hubspot_[Entity](**record)
                    await sync_to_async([entity].save)()
                    results['updated'] += 1
                    logger.debug(f"Force overwritten [entity] {[entity]_id}")
                else:
                    # Create new [entity]
                    [entity] = Hubspot_[Entity](**record)
                    await sync_to_async([entity].save)()
                    results['created'] += 1
                    logger.debug(f"Force created [entity] {[entity]_id}")
                    
            except Exception as e:
                logger.error(f"Error force saving [entity] {record.get('id')}: {e}")
                results['failed'] += 1
                
                await self.handle_sync_error(e, {
                    'operation': 'force_save_[entity]',
                    '[entity]_id': record.get('id'),
                    'record': record
                })
        
        return results
    
    # Standard save methods (non-force)
    async def _bulk_save_[entity](self, validated_data: List[Dict]) -> Dict[str, int]:
        """Standard bulk save operation"""
        # Implementation for normal bulk saves
        pass
    
    async def _individual_save_[entity](self, validated_data: List[Dict]) -> Dict[str, int]:
        """Standard individual save operation"""
        # Implementation for normal individual saves
        pass
```

## Usage Examples

```bash
# Standard incremental sync
python manage.py sync_hubspot_[entity]

# Full sync (may skip unchanged records)
python manage.py sync_hubspot_[entity] --full

# Force overwrite ALL records
python manage.py sync_hubspot_[entity] --full --force-overwrite

# Force overwrite recent records only
python manage.py sync_hubspot_[entity] --since=2025-01-01 --force-overwrite

# Test force overwrite without saving
python manage.py sync_hubspot_[entity] --full --force-overwrite --dry-run
```

## Implementation Checklist

- [ ] Create sync command using base template
- [ ] Implement sync engine with force overwrite methods
- [ ] Create client for API interaction
- [ ] Create processor for data transformation
- [ ] Add appropriate error handling
- [ ] Test with dry-run mode
- [ ] Verify force overwrite functionality
- [ ] Add documentation
