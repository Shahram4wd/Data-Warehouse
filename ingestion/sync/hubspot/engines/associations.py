"""
HubSpot associations sync engine
Following import_refactoring.md enterprise architecture standards
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.clients.associations import HubSpotAssociationsClient
from ingestion.sync.hubspot.processors.associations import (
    HubSpotAssociationProcessor,
    HubSpotAppointmentContactAssociationProcessor,
    HubSpotContactDivisionAssociationProcessor
)
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
from ingestion.models.hubspot import (
    Hubspot_AppointmentContactAssociation,
    Hubspot_ContactDivisionAssociation
)

logger = logging.getLogger(__name__)

class HubSpotAssociationSyncEngine(HubSpotBaseSyncEngine):
    """
    Sync engine for HubSpot associations between objects
    Supports both contact-appointment and contact-division associations
    Follows enterprise architecture standards from import_refactoring.md
    """
    
    def __init__(self, association_type: str = "contact_appointment", **kwargs):
        """
        Initialize association sync engine
        
        Args:
            association_type: Type of association to sync ('contact_appointment' or 'contact_division')
        """
        self.association_type = association_type
        super().__init__(f'associations_{association_type}', **kwargs)
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot associations client and processor"""
        # Initialize enterprise features first
        await self.initialize_enterprise_features()
        
        self.client = HubSpotAssociationsClient()
        await self.create_authenticated_session(self.client)
        
        # Initialize appropriate processor based on association type
        if self.association_type == "contact_appointment":
            self.processor = HubSpotAppointmentContactAssociationProcessor()
        elif self.association_type == "contact_division":
            self.processor = HubSpotContactDivisionAssociationProcessor()
        else:
            raise SyncException(f"Unsupported association type: {self.association_type}")
            
    def get_association_config(self) -> Dict[str, str]:
        """Get association configuration based on type"""
        if self.association_type == "contact_appointment":
            return {
                'from_object_type': 'contacts',
                'to_object_type': '0-421',  # Custom object for appointments
                'description': 'Contact to Appointment associations'
            }
        elif self.association_type == "contact_division":
            return {
                'from_object_type': 'contacts',
                'to_object_type': '2-37778609',  # Custom object for divisions
                'description': 'Contact to Division associations'
            }
        else:
            raise SyncException(f"Unsupported association type: {self.association_type}")
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch association data from HubSpot based on association type"""
        limit = kwargs.get('limit', self.batch_size)
        max_records = kwargs.get('max_records', 0)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        # Get association configuration
        config = self.get_association_config()
        from_object_type = config['from_object_type']
        to_object_type = config['to_object_type']
        
        logger.info(f"Fetching {config['description']} ({from_object_type} -> {to_object_type})")
        
        try:
            records_fetched = 0
            
            # Use the specific client method based on association type
            if self.association_type == "contact_appointment":
                async for batch in self.client.fetch_contact_appointment_associations_batch(
                    batch_size=limit,
                    max_records=max_records
                ):
                    if max_records > 0 and records_fetched >= max_records:
                        break
                    
                    records_fetched += len(batch)
                    yield batch
                    
                    if max_records > 0 and records_fetched >= max_records:
                        break
                        
            elif self.association_type == "contact_division":
                async for batch in self.client.fetch_contact_division_associations_batch(
                    batch_size=limit,
                    max_records=max_records
                ):
                    if max_records > 0 and records_fetched >= max_records:
                        break
                    
                    records_fetched += len(batch)
                    yield batch
                    
                    if max_records > 0 and records_fetched >= max_records:
                        break
            else:
                raise SyncException(f"Unsupported association type: {self.association_type}")
                
        except Exception as e:
            logger.error(f"Error fetching {self.association_type} associations: {e}")
            # Use enterprise error handling
            await self.handle_sync_error(e, {
                'operation': 'fetch_data',
                'entity_type': f'associations_{self.association_type}',
                'records_fetched': records_fetched
            })
            raise SyncException(f"Failed to fetch {self.association_type} associations: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform association data using specialized processor"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        for record in raw_data:
            try:
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming {self.association_type} association record {record.get('id', 'unknown')}: {e}")
                # Continue processing other records
                
        return transformed_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate association data using specialized processor"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        validated_data = []
        for record in data:
            try:
                validated = self.processor.validate_record(record)
                validated_data.append(validated)
            except ValidationException as e:
                logger.error(f"Validation error for {self.association_type} association {record.get('id', 'unknown')}: {e}")
                # Continue processing other records
                
        return validated_data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save association data to appropriate model based on association type"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not validated_data:
            return results
            
        # Import sync_to_async here to avoid import errors
        try:
            from asgiref.sync import sync_to_async
        except ImportError:
            # Fallback for environments without asgiref
            logger.warning("asgiref not available, using synchronous database operations")
            return await self._save_data_sync(validated_data)
        
        # Get the appropriate model class
        if self.association_type == "contact_appointment":
            model_class = Hubspot_AppointmentContactAssociation
        elif self.association_type == "contact_division":
            model_class = Hubspot_ContactDivisionAssociation
        else:
            raise SyncException(f"Unsupported association type: {self.association_type}")
        
        # Try bulk operations first for better performance
        try:
            return await self._bulk_save_associations(validated_data, model_class, sync_to_async)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed for {self.association_type} associations: {bulk_error}")
            logger.info("Falling back to individual record saves")
            return await self._individual_save_associations(validated_data, model_class, sync_to_async)
    
    async def _bulk_save_associations(self, validated_data: List[Dict], model_class, sync_to_async) -> Dict[str, int]:
        """Attempt bulk save operation for better performance"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        # Prepare objects for bulk create
        objects_to_create = []
        for record in validated_data:
            try:
                # Remove created_at if present as it will be auto-set
                record_data = {k: v for k, v in record.items() if k != 'created_at'}
                obj = model_class(**record_data)
                objects_to_create.append(obj)
            except Exception as e:
                logger.error(f"Error preparing {self.association_type} association for bulk create: {e}")
                results['failed'] += 1
        
        if objects_to_create:
            try:
                # Use bulk_create with ignore_conflicts to handle duplicates
                created_objects = await sync_to_async(model_class.objects.bulk_create)(
                    objects_to_create, 
                    batch_size=self.batch_size,
                    ignore_conflicts=True
                )
                results['created'] = len(created_objects)
                logger.info(f"Bulk created {results['created']} {self.association_type} associations")
            except Exception as e:
                logger.error(f"Bulk create failed for {self.association_type} associations: {e}")
                # Fallback to individual saves
                return await self._individual_save_associations(validated_data, model_class, sync_to_async)
        
        # Report metrics to enterprise monitoring
        await self.report_sync_metrics({
            'entity_type': f'associations_{self.association_type}',
            'processed': len(validated_data),
            'success_rate': (results['created'] + results['updated']) / len(validated_data) if validated_data else 0,
            'results': results
        })
        
        return results
    
    async def _individual_save_associations(self, validated_data: List[Dict], model_class, sync_to_async) -> Dict[str, int]:
        """Fallback to individual record saves"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                # Remove created_at if present as it will be auto-set
                record_data = {k: v for k, v in record.items() if k != 'created_at'}
                
                # Use get_or_create to handle duplicates
                if self.association_type == "contact_appointment":
                    obj, created = await sync_to_async(model_class.objects.get_or_create)(
                        contact_id=record_data.get('contact_id'),
                        appointment_id=record_data.get('appointment_id'),
                        defaults=record_data
                    )
                elif self.association_type == "contact_division":
                    obj, created = await sync_to_async(model_class.objects.get_or_create)(
                        contact_id=record_data.get('contact_id'),
                        division_id=record_data.get('division_id'),
                        defaults=record_data
                    )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving {self.association_type} association {record}: {e}")
                results['failed'] += 1
        
        # Report metrics to enterprise monitoring
        await self.report_sync_metrics({
            'entity_type': f'associations_{self.association_type}',
            'processed': len(validated_data),
            'success_rate': (results['created'] + results['updated']) / len(validated_data) if validated_data else 0,
            'results': results
        })
        
        return results
    
    async def _save_data_sync(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Synchronous fallback for environments without asgiref"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        # Get the appropriate model class
        if self.association_type == "contact_appointment":
            model_class = Hubspot_AppointmentContactAssociation
        elif self.association_type == "contact_division":
            model_class = Hubspot_ContactDivisionAssociation
        else:
            raise SyncException(f"Unsupported association type: {self.association_type}")
        
        for record in validated_data:
            try:
                # Remove created_at if present as it will be auto-set
                record_data = {k: v for k, v in record.items() if k != 'created_at'}
                
                # Use get_or_create to handle duplicates
                if self.association_type == "contact_appointment":
                    obj, created = model_class.objects.get_or_create(
                        contact_id=record_data.get('contact_id'),
                        appointment_id=record_data.get('appointment_id'),
                        defaults=record_data
                    )
                elif self.association_type == "contact_division":
                    obj, created = model_class.objects.get_or_create(
                        contact_id=record_data.get('contact_id'),
                        division_id=record_data.get('division_id'),
                        defaults=record_data
                    )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving {self.association_type} association {record}: {e}")
                results['failed'] += 1
        
        return results
