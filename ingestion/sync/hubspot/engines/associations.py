"""
HubSpot associations sync engine
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from ingestion.base.exceptions import SyncException
from ingestion.sync.hubspot.clients.associations import HubSpotAssociationsClient
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine

logger = logging.getLogger(__name__)

class HubSpotAssociationSyncEngine(HubSpotBaseSyncEngine):
    """Sync engine for HubSpot associations between objects"""
    
    def __init__(self, **kwargs):
        super().__init__('associations', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot associations client"""
        self.client = HubSpotAssociationsClient()
        await self.create_authenticated_session(self.client)
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch association data from HubSpot"""
        from_object_type = kwargs.get('from_object_type', 'contacts')
        to_object_type = kwargs.get('to_object_type', 'deals')
        limit = kwargs.get('limit', self.batch_size)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            # First, get object IDs from the source object type
            object_ids = []
            
            # Get object IDs based on the from_object_type
            if from_object_type == 'contacts':
                # Get contact IDs
                from ingestion.sync.hubspot.clients.contacts import HubSpotContactsClient
                contacts_client = HubSpotContactsClient()
                await self.create_authenticated_session(contacts_client)
                
                async for batch in contacts_client.fetch_contacts(limit=limit):
                    object_ids.extend([str(contact.get('id')) for contact in batch if contact.get('id')])
                    
                await contacts_client.close()
                
            elif from_object_type == 'deals':
                # Get deal IDs
                from ingestion.sync.hubspot.clients.deals import HubSpotDealsClient
                deals_client = HubSpotDealsClient()
                await self.create_authenticated_session(deals_client)
                
                async for batch in deals_client.fetch_deals(limit=limit):
                    object_ids.extend([str(deal.get('id')) for deal in batch if deal.get('id')])
                    
                await deals_client.close()
                
            elif from_object_type == 'appointments':
                # Get appointment IDs (custom objects)
                from ingestion.sync.hubspot.clients.appointments import HubSpotAppointmentsClient
                appointments_client = HubSpotAppointmentsClient()
                await self.create_authenticated_session(appointments_client)
                
                async for batch in appointments_client.fetch_appointments(limit=limit):
                    object_ids.extend([str(appointment.get('id')) for appointment in batch if appointment.get('id')])
                    
                await appointments_client.close()
            
            # Now fetch associations for these object IDs
            if object_ids:
                # Process in batches of 100 (API limit)
                for i in range(0, len(object_ids), 100):
                    batch_ids = object_ids[i:i+100]
                    associations = await self.client.fetch_associations(
                        from_object_type=from_object_type,
                        to_object_type=to_object_type,
                        object_ids=batch_ids
                    )
                    if associations:
                        yield associations
            else:
                logger.warning(f"No {from_object_type} found to fetch associations from")
                
        except Exception as e:
            logger.error(f"Error fetching associations: {e}")
            raise SyncException(f"Failed to fetch associations: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform association data"""
        # Associations are relatively simple - just return as is
        return raw_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate association data"""
        validated_data = []
        for record in data:
            if record.get('from_object_id') and record.get('to_object_id'):
                validated_data.append(record)
            else:
                logger.warning(f"Invalid association record: {record}")
                
        return validated_data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save association data to database"""
        # For now, just log associations - you can extend this to save to a specific model
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                logger.info(f"Association: {record.get('from_object_type')} {record.get('from_object_id')} -> "
                           f"{record.get('to_object_type')} {record.get('to_object_id')}")
                results['created'] += 1
            except Exception as e:
                logger.error(f"Error processing association {record}: {e}")
                results['failed'] += 1
                
        return results
