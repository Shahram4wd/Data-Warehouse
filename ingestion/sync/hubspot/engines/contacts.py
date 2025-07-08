"""
HubSpot contacts sync engine
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.clients.contacts import HubSpotContactsClient
from ingestion.sync.hubspot.processors.contacts import HubSpotContactProcessor
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
from ingestion.models.hubspot import Hubspot_Contact

logger = logging.getLogger(__name__)

class HubSpotContactSyncEngine(HubSpotBaseSyncEngine):
    """Sync engine for HubSpot contacts"""
    
    def __init__(self, **kwargs):
        super().__init__('contacts', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot contacts client and processor"""
        # Initialize enterprise features first
        await self.initialize_enterprise_features()
        
        self.client = HubSpotContactsClient()
        await self.create_authenticated_session(self.client)
        self.processor = HubSpotContactProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch contact data from HubSpot with enterprise monitoring"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        max_records = kwargs.get('max_records', 0)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            records_fetched = 0
            async for batch in self.client.fetch_contacts(
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
            logger.error(f"Error fetching contacts: {e}")
            # Use enterprise error handling
            await self.handle_sync_error(e, {
                'operation': 'fetch_data',
                'entity_type': 'contacts',
                'records_fetched': records_fetched
            })
            raise SyncException(f"Failed to fetch contacts: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform contact data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        for record in raw_data:
            try:
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming contact record {record.get('id')}: {e}")
                # Continue processing other records
                
        return transformed_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate contact data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        validated_data = []
        for record in data:
            try:
                validated = self.processor.validate_record(record)
                validated_data.append(validated)
            except ValidationException as e:
                logger.error(f"Validation error for contact {record.get('id')}: {e}")
                # Continue processing other records
                
        return validated_data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save contact data to database with enterprise monitoring"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                # Check if contact exists
                contact_id = record.get('id')
                if not contact_id:
                    logger.error(f"Contact record missing ID: {record}")
                    results['failed'] += 1
                    continue
                
                # Use get_or_create to handle duplicates
                contact, created = await sync_to_async(Hubspot_Contact.objects.get_or_create)(
                    id=contact_id,
                    defaults=record
                )
                
                # Update existing contact with new data
                if not created:
                    for field, value in record.items():
                        if hasattr(contact, field):
                            setattr(contact, field, value)
                    await sync_to_async(contact.save)()
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving contact {record.get('id')}: {e}")
                results['failed'] += 1
                
        # Report metrics to enterprise monitoring
        await self.report_sync_metrics({
            'entity_type': 'contacts',
            'processed': len(validated_data),
            'success_rate': (results['created'] + results['updated']) / len(validated_data) if validated_data else 0,
            'results': results
        })
        
        return results
