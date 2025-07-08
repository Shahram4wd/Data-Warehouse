"""
HubSpot sync engines for different entity types
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator
from django.utils import timezone
from asgiref.sync import sync_to_async
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.client import HubSpotClient
from ingestion.sync.hubspot.processors import (
    HubSpotContactProcessor,
    HubSpotAppointmentProcessor,
    HubSpotDivisionProcessor,
    HubSpotDealProcessor
)
from ingestion.models.hubspot import (
    Hubspot_Contact,
    Hubspot_Appointment,
    Hubspot_Division,
    Hubspot_Deal
)

logger = logging.getLogger(__name__)

class HubSpotContactSyncEngine(BaseSyncEngine):
    """Sync engine for HubSpot contacts"""
    
    def __init__(self, **kwargs):
        super().__init__('hubspot', 'contacts', **kwargs)
        self.client = None
        self.processor = None
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for contacts"""
        return 100
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot client and processor"""
        self.client = HubSpotClient()
        await self.client.authenticate()
        self.processor = HubSpotContactProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch contact data from HubSpot"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            async for batch in self.client.fetch_contacts(
                last_sync=last_sync,
                limit=limit
            ):
                yield batch
        except Exception as e:
            logger.error(f"Error fetching contacts: {e}")
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
        """Save contact data to database"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                contact, created = await sync_to_async(
                    Hubspot_Contact.objects.update_or_create,
                    thread_sensitive=True
                )(
                    id=record['id'],
                    defaults=record
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving contact {record.get('id')}: {e}")
                results['failed'] += 1
                
        return results
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.client:
            await self.client.close()

class HubSpotAppointmentSyncEngine(BaseSyncEngine):
    """Sync engine for HubSpot appointments"""
    
    def __init__(self, **kwargs):
        super().__init__('hubspot', 'appointments', **kwargs)
        self.client = None
        self.processor = None
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for appointments"""
        return 100
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot client and processor"""
        self.client = HubSpotClient()
        await self.client.authenticate()
        self.processor = HubSpotAppointmentProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch appointment data from HubSpot"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            async for batch in self.client.fetch_appointments(
                last_sync=last_sync,
                limit=limit
            ):
                yield batch
        except Exception as e:
            logger.error(f"Error fetching appointments: {e}")
            raise SyncException(f"Failed to fetch appointments: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform appointment data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        for record in raw_data:
            try:
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming appointment record {record.get('id')}: {e}")
                # Continue processing other records
                
        return transformed_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate appointment data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        validated_data = []
        for record in data:
            try:
                validated = self.processor.validate_record(record)
                validated_data.append(validated)
            except ValidationException as e:
                logger.error(f"Validation error for appointment {record.get('id')}: {e}")
                # Continue processing other records
                
        return validated_data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save appointment data to database"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                appointment, created = await sync_to_async(
                    Hubspot_Appointment.objects.update_or_create,
                    thread_sensitive=True
                )(
                    id=record['id'],
                    defaults=record
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving appointment {record.get('id')}: {e}")
                results['failed'] += 1
                
        return results
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.client:
            await self.client.close()

class HubSpotDivisionSyncEngine(BaseSyncEngine):
    """Sync engine for HubSpot divisions"""
    
    def __init__(self, **kwargs):
        super().__init__('hubspot', 'divisions', **kwargs)
        self.client = None
        self.processor = None
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for divisions"""
        return 50
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot client and processor"""
        self.client = HubSpotClient()
        await self.client.authenticate()
        self.processor = HubSpotDivisionProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch division data from HubSpot"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            async for batch in self.client.fetch_divisions(
                last_sync=last_sync,
                limit=limit
            ):
                yield batch
        except Exception as e:
            logger.error(f"Error fetching divisions: {e}")
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
        
        for record in validated_data:
            try:
                division, created = await sync_to_async(
                    Hubspot_Division.objects.update_or_create,
                    thread_sensitive=True
                )(
                    id=record['id'],
                    defaults=record
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving division {record.get('id')}: {e}")
                results['failed'] += 1
                
        return results
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.client:
            await self.client.close()

class HubSpotDealSyncEngine(BaseSyncEngine):
    """Sync engine for HubSpot deals"""
    
    def __init__(self, **kwargs):
        super().__init__('hubspot', 'deals', **kwargs)
        self.client = None
        self.processor = None
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for deals"""
        return 100
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot client and processor"""
        self.client = HubSpotClient()
        await self.client.authenticate()
        self.processor = HubSpotDealProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch deal data from HubSpot"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            async for batch in self.client.fetch_deals(
                last_sync=last_sync,
                limit=limit
            ):
                yield batch
        except Exception as e:
            logger.error(f"Error fetching deals: {e}")
            raise SyncException(f"Failed to fetch deals: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform deal data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        for record in raw_data:
            try:
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming deal record {record.get('id')}: {e}")
                # Continue processing other records
                
        return transformed_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate deal data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        validated_data = []
        for record in data:
            try:
                validated = self.processor.validate_record(record)
                validated_data.append(validated)
            except ValidationException as e:
                logger.error(f"Validation error for deal {record.get('id')}: {e}")
                # Continue processing other records
                
        return validated_data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save deal data to database"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                deal, created = await sync_to_async(
                    Hubspot_Deal.objects.update_or_create,
                    thread_sensitive=True
                )(
                    id=record['id'],
                    defaults=record
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving deal {record.get('id')}: {e}")
                results['failed'] += 1
                
        return results
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.client:
            await self.client.close()

class HubSpotAssociationSyncEngine(BaseSyncEngine):
    """Sync engine for HubSpot associations between objects"""
    
    def __init__(self, **kwargs):
        super().__init__('hubspot', 'associations', **kwargs)
        self.client = None
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for associations"""
        return 100
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot client"""
        self.client = HubSpotClient()
        await self.client.authenticate()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch association data from HubSpot"""
        from_object_type = kwargs.get('from_object_type', 'contacts')
        to_object_type = kwargs.get('to_object_type', 'deals')
        limit = kwargs.get('limit', self.batch_size)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            async for batch in self.client.fetch_associations(
                from_object_type=from_object_type,
                to_object_type=to_object_type,
                limit=limit
            ):
                yield batch
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
                logger.info(f"Association: {record['from_object_type']} {record['from_object_id']} -> "
                           f"{record['to_object_type']} {record['to_object_id']}")
                results['created'] += 1
            except Exception as e:
                logger.error(f"Error processing association {record}: {e}")
                results['failed'] += 1
                
        return results
        
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.client:
            await self.client.close()
