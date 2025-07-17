"""
HubSpot divisions sync engine
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.clients.divisions import HubSpotDivisionsClient
from ingestion.sync.hubspot.processors.divisions import HubSpotDivisionProcessor
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
from ingestion.models.hubspot import Hubspot_Division

logger = logging.getLogger(__name__)

class HubSpotDivisionSyncEngine(HubSpotBaseSyncEngine):
    """Sync engine for HubSpot divisions"""
    
    def __init__(self, **kwargs):
        super().__init__('divisions', **kwargs)
        self.force_overwrite = kwargs.get('force_overwrite', False)
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot divisions client and processor"""
        # Initialize enterprise features first
        await self.initialize_enterprise_features()
        
        self.client = HubSpotDivisionsClient()
        await self.create_authenticated_session(self.client)
        self.processor = HubSpotDivisionProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch division data from HubSpot"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        max_records = kwargs.get('max_records', 0)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            records_fetched = 0
            async for batch in self.client.fetch_divisions(
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
            logger.error(f"Error fetching divisions: {e}")
            # Use enterprise error handling
            await self.handle_sync_error(e, {
                'operation': 'fetch_data',
                'entity_type': 'divisions',
                'records_fetched': records_fetched
            })
            raise SyncException(f"Failed to fetch divisions: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform division data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        for record in raw_data:
            try:
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming division record {record.get('id')}: {e}")
                # Continue processing other records
                
        return transformed_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate division data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        validated_data = []
        for record in data:
            try:
                validated = self.processor.validate_record(record)
                validated_data.append(validated)
            except ValidationException as e:
                logger.error(f"Validation error for division {record.get('id')}: {e}")
                # Continue processing other records
                
        return validated_data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save division data to database"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        # Check if force overwrite is enabled
        if self.force_overwrite:
            logger.info("Force overwrite mode - all records will be updated regardless of timestamps")
            return await self._force_save_divisions(validated_data)
        
        for record in validated_data:
            try:
                # Check if division exists
                division_id = record.get('id')
                if not division_id:
                    logger.error(f"Division record missing ID: {record}")
                    results['failed'] += 1
                    continue
                
                # Use get_or_create to handle duplicates
                division, created = await sync_to_async(Hubspot_Division.objects.get_or_create)(
                    id=division_id,
                    defaults=record
                )
                
                # Update existing division with new data
                if not created:
                    for field, value in record.items():
                        if hasattr(division, field):
                            setattr(division, field, value)
                    await sync_to_async(division.save)()
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving division {record.get('id')}: {e}")
                results['failed'] += 1
                
        # Report metrics to enterprise monitoring
        await self.report_sync_metrics({
            'entity_type': 'divisions',
            'processed': len(validated_data),
            'success_rate': (results['created'] + results['updated']) / len(validated_data) if validated_data else 0,
            'results': results
        })
        
        return results
    
    async def _force_save_divisions(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite divisions individually, ignoring timestamps"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                division_id = record.get('id')
                if not division_id:
                    logger.error(f"Division record missing ID: {record}")
                    results['failed'] += 1
                    continue
                
                # Check if division exists
                try:
                    existing_division = await sync_to_async(Hubspot_Division.objects.get)(id=division_id)
                    # Delete existing and recreate for true overwrite
                    await sync_to_async(existing_division.delete)()
                    division = Hubspot_Division(**record)
                    await sync_to_async(division.save)()
                    results['updated'] += 1
                    logger.debug(f"Force overwritten division {division_id}")
                except Hubspot_Division.DoesNotExist:
                    # Create new division
                    division = Hubspot_Division(**record)
                    await sync_to_async(division.save)()
                    results['created'] += 1
                    logger.debug(f"Force created division {division_id}")
                    
            except Exception as e:
                logger.error(f"Error force saving division {record.get('id')}: {e}")
                results['failed'] += 1
                
                # Report individual division errors to enterprise error handling
                await self.handle_sync_error(e, {
                    'operation': 'force_save_division',
                    'division_id': record.get('id'),
                    'record': record
                })
        
        return results
