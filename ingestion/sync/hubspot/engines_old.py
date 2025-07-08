"""
HubSpot sync engines for different entity types
"""
import logging
import aiohttp
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
        # First authenticate to set up headers
        await self.client.authenticate()
        # Then create session with the authenticated headers
        self.client.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.client.timeout),
            headers=self.client.headers
        )
        self.processor = HubSpotContactProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch contact data from HubSpot"""
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
        
    async def save_data_bulk(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save contact data to database using bulk operations"""
        if not validated_data:
            return {'created': 0, 'updated': 0, 'failed': 0}
            
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            # Get existing contact IDs to determine which are updates vs creates
            contact_ids = [record['id'] for record in validated_data]
            existing_contacts = await sync_to_async(
                lambda: set(Hubspot_Contact.objects.filter(id__in=contact_ids).values_list('id', flat=True)),
                thread_sensitive=True
            )()
            
            # Separate into creates and updates
            creates = []
            updates = []
            
            for record in validated_data:
                if record['id'] in existing_contacts:
                    updates.append(record)
                else:
                    creates.append(record)
            
            # Bulk create new contacts
            if creates:
                contact_objects = [Hubspot_Contact(**record) for record in creates]
                await sync_to_async(
                    Hubspot_Contact.objects.bulk_create,
                    thread_sensitive=True
                )(contact_objects, batch_size=500, ignore_conflicts=True)
                results['created'] = len(creates)
            
            # Bulk update existing contacts
            if updates:
                # For updates, we need to use individual update_or_create since bulk_update
                # requires knowing which fields changed
                for record in updates:
                    try:
                        await sync_to_async(
                            Hubspot_Contact.objects.filter(id=record['id']).update,
                            thread_sensitive=True
                        )(**{k: v for k, v in record.items() if k != 'id'})
                        results['updated'] += 1
                    except Exception as e:
                        logger.error(f"Error updating contact {record['id']}: {e}")
                        results['failed'] += 1
                        
        except Exception as e:
            logger.error(f"Error in bulk save operation: {e}")
            # Fallback to individual saves
            return await self.save_data(validated_data)
        
        return results
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save contact data to database (fallback method)"""
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
        # First authenticate to set up headers
        await self.client.authenticate()
        # Then create session with the authenticated headers
        self.client.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.client.timeout),
            headers=self.client.headers
        )
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
        # First authenticate to set up headers
        await self.client.authenticate()
        # Then create session with the authenticated headers
        self.client.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.client.timeout),
            headers=self.client.headers
        )
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
        # First authenticate to set up headers
        await self.client.authenticate()
        # Then create session with the authenticated headers
        self.client.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.client.timeout),
            headers=self.client.headers
        )
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
        # First authenticate to set up headers
        await self.client.authenticate()
        # Then create session with the authenticated headers
        self.client.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.client.timeout),
            headers=self.client.headers
        )
        
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
                async for batch in self.client.fetch_contacts(limit=limit):
                    object_ids.extend([str(contact.get('id')) for contact in batch if contact.get('id')])
            elif from_object_type == 'deals':
                # Get deal IDs
                async for batch in self.client.fetch_deals(limit=limit):
                    object_ids.extend([str(deal.get('id')) for deal in batch if deal.get('id')])
            elif from_object_type == 'appointments':
                # Get appointment IDs (custom objects)
                async for batch in self.client.fetch_appointments(limit=limit):
                    object_ids.extend([str(appointment.get('id')) for appointment in batch if appointment.get('id')])
            
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
