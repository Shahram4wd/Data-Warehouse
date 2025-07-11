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
        """Save contact data to database with enterprise monitoring and bulk operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not validated_data:
            return results
        
        try:
            # Try bulk operations first for better performance
            results = await self._bulk_save_contacts(validated_data)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed, falling back to individual saves: {bulk_error}")
            # Fallback to individual saves
            results = await self._individual_save_contacts(validated_data)
        
        # Calculate and report enterprise metrics
        total_processed = len(validated_data)
        success_count = results['created'] + results['updated']
        success_rate = success_count / total_processed if total_processed > 0 else 0
        
        # Report metrics to enterprise monitoring system
        await self.report_sync_metrics({
            'entity_type': 'contacts',
            'processed': total_processed,
            'success_rate': success_rate,
            'data_quality_score': self._calculate_data_quality_score(validated_data, results),
            'results': results,
            'processing_efficiency': self._calculate_processing_efficiency(validated_data),
            'validation_errors': results['failed']
        })
        
        logger.info(f"Contact sync completed - Created: {results['created']}, "
                   f"Updated: {results['updated']}, Failed: {results['failed']}, "
                   f"Success Rate: {success_rate:.2%}")
        
        return results
    
    async def _bulk_save_contacts(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Attempt bulk save operation for better performance"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        # Separate existing vs new contacts
        contact_ids = [record['id'] for record in validated_data if record.get('id')]
        existing_contacts = await sync_to_async(list)(
            Hubspot_Contact.objects.filter(id__in=contact_ids).values_list('id', flat=True)
        )
        existing_set = set(existing_contacts)
        
        to_create = []
        to_update = []
        
        for record in validated_data:
            if record.get('id') in existing_set:
                to_update.append(record)
            else:
                to_create.append(record)
        
        # Bulk create new contacts
        if to_create:
            try:
                contact_objects = [Hubspot_Contact(**record) for record in to_create]
                created_contacts = await sync_to_async(Hubspot_Contact.objects.bulk_create)(
                    contact_objects, batch_size=self.batch_size
                )
                results['created'] = len(created_contacts)
            except Exception as e:
                logger.error(f"Bulk create failed: {e}")
                # Fall back to individual saves for create batch
                for record in to_create:
                    try:
                        await sync_to_async(Hubspot_Contact.objects.create)(**record)
                        results['created'] += 1
                    except Exception:
                        results['failed'] += 1
        
        # Bulk update existing contacts
        if to_update:
            try:
                await self._bulk_update_contacts(to_update)
                results['updated'] = len(to_update)
            except Exception as e:
                logger.error(f"Bulk update failed: {e}")
                # Fall back to individual saves for update batch
                for record in to_update:
                    try:
                        contact = await sync_to_async(Hubspot_Contact.objects.get)(id=record['id'])
                        for field, value in record.items():
                            if hasattr(contact, field):
                                setattr(contact, field, value)
                        await sync_to_async(contact.save)()
                        results['updated'] += 1
                    except Exception:
                        results['failed'] += 1
        
        return results
    
    async def _bulk_update_contacts(self, update_data: List[Dict]) -> None:
        """Perform bulk update operation"""
        # This is a simplified bulk update - in production you'd use bulk_update
        for record in update_data:
            contact = await sync_to_async(Hubspot_Contact.objects.get)(id=record['id'])
            for field, value in record.items():
                if hasattr(contact, field):
                    setattr(contact, field, value)
            await sync_to_async(contact.save)()
    
    async def _individual_save_contacts(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Fallback individual save operation with detailed error handling"""
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
                
                # Report individual contact errors to enterprise error handling
                await self.handle_sync_error(e, {
                    'operation': 'save_contact',
                    'contact_id': record.get('id'),
                    'record': record
                })
        
        return results
    
    def _calculate_data_quality_score(self, validated_data: List[Dict], results: Dict[str, int]) -> float:
        """Calculate data quality score based on validation results"""
        if not validated_data:
            return 1.0
        
        total_records = len(validated_data)
        successful_records = results['created'] + results['updated']
        
        # Base score from success rate
        success_score = successful_records / total_records
        
        # Additional quality factors
        quality_factors = []
        
        for record in validated_data:
            record_quality = 0.0
            total_checks = 0
            
            # Check for key field completeness
            if record.get('email'):
                record_quality += 1
                total_checks += 1
            if record.get('phone'):
                record_quality += 1
                total_checks += 1
            if record.get('firstname') or record.get('lastname'):
                record_quality += 1
                total_checks += 1
            if record.get('address') and record.get('city') and record.get('state'):
                record_quality += 1
                total_checks += 1
            
            # Avoid division by zero
            if total_checks > 0:
                quality_factors.append(record_quality / total_checks)
            else:
                quality_factors.append(0.5)  # Default score for records with no key fields
        
        # Average quality across all records
        avg_quality = sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
        
        # Combine success rate and data completeness
        final_score = (success_score * 0.7) + (avg_quality * 0.3)
        
        return min(final_score, 1.0)
    
    def _calculate_processing_efficiency(self, validated_data: List[Dict]) -> float:
        """Calculate processing efficiency based on batch size and complexity"""
        if not validated_data:
            return 1.0
        
        # Basic efficiency based on batch size vs optimal size
        batch_size = len(validated_data)
        optimal_size = 100  # Target batch size for contacts
        
        if batch_size <= optimal_size:
            size_efficiency = batch_size / optimal_size
        else:
            # Penalty for oversized batches
            size_efficiency = optimal_size / batch_size
        
        # Factor in record complexity (number of populated fields)
        avg_field_count = sum(len([v for v in record.values() if v is not None]) for record in validated_data) / len(validated_data)
        complexity_factor = min(avg_field_count / 20, 1.0)  # Normalize to 20 fields max
        
        return (size_efficiency * 0.6) + (complexity_factor * 0.4)
