"""
Engine for syncing HubSpot Genius Users
Follows import_refactoring.md enterprise architecture standards
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from asgiref.sync import sync_to_async
from django.utils import timezone
from ingestion.models.hubspot import Hubspot_GeniusUser
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.base.sync_engine import BaseSyncEngine
from ..clients.genius_users_client import HubSpotGeniusUsersClient
from ..processors.genius_users_processor import HubSpotGeniusUsersProcessor

logger = logging.getLogger(__name__)

class HubSpotGeniusUsersSyncEngine(BaseSyncEngine):
    def __init__(self, api_token=None, batch_size=100, dry_run=False, stdout=None, max_records=0, full=False, force_overwrite=False):
        super().__init__('hubspot', 'genius_users', batch_size=batch_size, dry_run=dry_run, force_overwrite=force_overwrite)
        self.api_token = api_token
        self.stdout = stdout
        self.max_records = max_records
        self.full = full

    def get_default_batch_size(self) -> int:
        return 100

    async def initialize_client(self):
        """Initialize client and processor"""
        # Initialize enterprise features if available
        try:
            await self.initialize_enterprise_features()
        except AttributeError:
            # Base class doesn't have enterprise features
            pass
        
        self.client = HubSpotGeniusUsersClient(api_token=self.api_token)
        self.processor = HubSpotGeniusUsersProcessor()

    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch genius users data from HubSpot with delta sync support"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        max_records = kwargs.get('max_records', self.max_records)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            records_fetched = 0
            async for batch in self.client.fetch_genius_users(
                last_sync=last_sync,
                limit=limit
            ):
                # If max_records is set, limit the records returned
                if max_records > 0:
                    if records_fetched >= max_records:
                        break
                    
                    # If this batch would exceed max_records, truncate it
                    if records_fetched + len(batch) > max_records:
                        batch = batch[:max_records - records_fetched]
                
                records_fetched += len(batch)
                yield batch
                
                # If we've reached max_records, stop fetching
                if max_records > 0 and records_fetched >= max_records:
                    break
                    
        except Exception as e:
            logger.error(f"Error fetching genius users: {e}")
            try:
                await self.handle_sync_error(e, {
                    'operation': 'fetch_data',
                    'entity_type': 'genius_users',
                    'records_fetched': records_fetched
                })
            except AttributeError:
                # Base class doesn't have enterprise error handling
                pass
            raise SyncException(f"Failed to fetch genius users: {e}")

    async def transform_data(self, raw_data):
        """Transform genius users data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        for record in raw_data:
            try:
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming genius user record {record.get('id')}: {e}")
                # Continue processing other records
                
        return transformed_data

    async def validate_data(self, data):
        """Validate genius users data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        validated_data = []
        for record in data:
            try:
                validated = self.processor.validate_record(record)
                validated_data.append(validated)
            except ValidationException as e:
                logger.error(f"Validation error for genius user {record.get('id')}: {e}")
                # Continue processing other records
                
        return validated_data

    async def save_data(self, validated_data):
        """Save genius users data to database with enterprise monitoring"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not validated_data:
            return results
        
        try:
            # Check if force overwrite is enabled
            if self.force_overwrite:
                logger.info("Force overwrite mode - all records will be updated regardless of timestamps")
                results = await self._force_overwrite_users(validated_data)
            else:
                # Try bulk operations first for better performance
                results = await self._bulk_save_users(validated_data)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed, falling back to individual saves: {bulk_error}")
            # Fallback to individual saves
            if self.force_overwrite:
                results = await self._individual_force_save_users(validated_data)
            else:
                results = await self._individual_save_users(validated_data)
        
        return results

    async def save_data_bulk(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Bulk save method for better performance"""
        results = await self.save_data(validated_data)
        
        # Don't add 'processed' here - the base class handles that
        # Just return the created/updated/failed counts from save_data
        return results

    async def _bulk_save_users(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Bulk upsert for genius users using bulk_create with update_conflicts=True"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        # Prepare objects
        user_objects = [Hubspot_GeniusUser(**record) for record in validated_data]
        try:
            created_users = await sync_to_async(Hubspot_GeniusUser.objects.bulk_create)(
                user_objects,
                batch_size=self.batch_size,
                update_conflicts=True,
                update_fields=[
                    "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "archived",
                    "arrivy_user_id", "division", "division_id", "email", "job_title", "name", "title_id",
                    "user_account_type", "user_id", "user_status_inactive", "sync_updated_at"
                ],
                unique_fields=["id"]
            )
            
            # For bulk_create with update_conflicts, we can't easily distinguish created vs updated
            # So we'll estimate based on existing records
            existing_ids = set(await sync_to_async(list)(
                Hubspot_GeniusUser.objects.filter(
                    id__in=[rec['id'] for rec in validated_data]
                ).values_list('id', flat=True)
            ))
            
            results['updated'] = len(existing_ids)
            results['created'] = len(validated_data) - len(existing_ids)
            
            logger.info(f"Bulk saved {len(validated_data)} genius users: {results['created']} created, {results['updated']} updated")
            
        except Exception as e:
            logger.error(f"Bulk save failed: {e}")
            raise
            
        return results

    async def _force_overwrite_users(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite users - delete and recreate for true overwrite"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        record_ids = [rec['id'] for rec in validated_data if rec.get('id')]
        if record_ids:
            deleted_count = await sync_to_async(Hubspot_GeniusUser.objects.filter(id__in=record_ids).delete)()
            logger.info(f"Force overwrite: deleted {deleted_count[0]} existing genius users")
        
        # Recreate all records
        objs = [Hubspot_GeniusUser(**rec) for rec in validated_data]
        await sync_to_async(Hubspot_GeniusUser.objects.bulk_create)(objs, batch_size=self.batch_size)
        
        results['created'] = len(validated_data)
        logger.info(f"Force overwrite: created {results['created']} genius users")
        
        return results

    async def _individual_save_users(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Individual save for genius users (fallback)"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                user, created = await sync_to_async(Hubspot_GeniusUser.objects.update_or_create)(
                    id=record['id'],
                    defaults=record
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving genius user {record.get('id')}: {e}")
                results['failed'] += 1
        
        return results

    async def _individual_force_save_users(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Individual force save for genius users"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                # Delete existing record
                await sync_to_async(Hubspot_GeniusUser.objects.filter(id=record['id']).delete)()
                
                # Create new record
                await sync_to_async(Hubspot_GeniusUser.objects.create)(**record)
                results['created'] += 1
                
            except Exception as e:
                logger.error(f"Error force saving genius user {record.get('id')}: {e}")
                results['failed'] += 1
        
        return results

    async def cleanup(self):
        """Clean up resources"""
        pass

    async def estimate_total_records(self, **kwargs) -> int:
        """Estimate total number of records to be synced"""
        # For now, return 0 (unknown) - could be enhanced to query HubSpot API for count
        return 0

    # Legacy compatibility methods
    async def run_sync(self, **kwargs):
        """Legacy run_sync method for backward compatibility"""
        # Always delegate to the base class which properly handles SyncHistory
        return await super().run_sync(**kwargs)

    @sync_to_async
    def bulk_upsert(self, records):
        # Check if force_overwrite is enabled
        if self.force_overwrite:
            # Force overwrite - delete and recreate for true overwrite
            record_ids = [rec['id'] for rec in records if rec.get('id')]
            if record_ids:
                Hubspot_GeniusUser.objects.filter(id__in=record_ids).delete()
            
            # Recreate all records
            objs = [Hubspot_GeniusUser(**rec) for rec in records]
            Hubspot_GeniusUser.objects.bulk_create(objs, batch_size=self.batch_size)
        else:
            # Normal upsert by id (primary key)
            objs = [Hubspot_GeniusUser(**rec) for rec in records]
            Hubspot_GeniusUser.objects.bulk_create(
                objs,
                update_conflicts=True,
                update_fields=[
                    "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "archived",
                    "arrivy_user_id", "division", "division_id", "email", "job_title", "name", "title_id",
                    "user_account_type", "user_id", "user_status_inactive", "sync_updated_at"
                ],
                unique_fields=["id"]
            )
