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
        self.force_overwrite = kwargs.get('force_overwrite', False)
        
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
            # Check if force overwrite is enabled
            if self.force_overwrite:
                logger.info("Force overwrite mode - all records will be updated regardless of timestamps")
                results = await self._force_overwrite_contacts(validated_data)
            else:
                # Try bulk operations first for better performance
                results = await self._bulk_save_contacts(validated_data)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed, falling back to individual saves: {bulk_error}")
            # Fallback to individual saves
            if self.force_overwrite:
                results = await self._individual_force_save_contacts(validated_data)
            else:
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
        """True bulk upsert for contacts using bulk_create with update_conflicts=True"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        # Prepare objects
        contact_objects = [Hubspot_Contact(**record) for record in validated_data]
        try:
            created_contacts = await sync_to_async(Hubspot_Contact.objects.bulk_create)(
                contact_objects,
                batch_size=self.batch_size,
                update_conflicts=True,
                update_fields=[
                    "address", "adgroupid", "ap_leadid", "campaign_content", "campaign_name", "city", "clickcheck", "clicktype", "comments", "createdate", "division", "email", "firstname", "hs_google_click_id", "hs_object_id", "lastmodifieddate", "lastname", "lead_salesrabbit_lead_id", "marketsharp_id", "msm_source", "original_lead_source", "original_lead_source_created", "phone", "price", "reference_code", "search_terms", "state", "tier", "trustedform_cert_url", "vendorleadid", "vertical", "zip", "archived", "updated_at"
                ],
                unique_fields=["id"]
            )
            results['created'] = len([obj for obj in created_contacts if obj._state.adding])
            results['updated'] = len(validated_data) - results['created']
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            results['failed'] = len(validated_data)
            
            # Log detailed information about the failed batch for debugging
            logger.error(f"Failed batch details: {len(validated_data)} contacts")
            for record in validated_data:
                record_id = record.get('id', 'UNKNOWN')
                hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-1/{record_id}"
                logger.error(f"Failed record in batch - Contact ID: {record_id} - HubSpot URL: {hubspot_url}")
                
                # Check for potential field length issues
                long_fields = []
                for field_name, field_value in record.items():
                    if field_value and isinstance(field_value, str):
                        if len(field_value) > 255:
                            long_fields.append(f"{field_name}({len(field_value)} chars): '{field_value[:50]}...'")
                        elif len(field_value) > 100:
                            long_fields.append(f"{field_name}({len(field_value)} chars): '{field_value[:30]}...'")
                
                if long_fields:
                    logger.error(f"Record {record_id} potential long fields: {'; '.join(long_fields)}")
            
            # Attempt individual record processing to save what we can
            logger.info(f"Attempting individual record processing for {len(validated_data)} failed records")
            individual_results = await self._individual_save_contacts(validated_data)
            
            # Update results with individual processing outcomes
            results['created'] = individual_results['created']
            results['updated'] = individual_results['updated']
            results['failed'] = individual_results['failed']
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
                contact_id = record.get('id')
                if not contact_id:
                    logger.error(f"Contact record missing ID: {record}")
                    results['failed'] += 1
                    continue

                hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-1/{contact_id}"
                
                # Check if contact exists
                contact_exists = await sync_to_async(Hubspot_Contact.objects.filter(id=contact_id).exists)()
                
                if contact_exists:
                    # Update existing contact
                    try:
                        existing_contact = await sync_to_async(Hubspot_Contact.objects.get)(id=contact_id)
                        
                        # Validate field lengths before saving to prevent database errors
                        validated_record = self._validate_field_lengths(record, contact_id)
                        
                        for field, value in validated_record.items():
                            if hasattr(existing_contact, field):
                                setattr(existing_contact, field, value)
                        
                        await sync_to_async(existing_contact.save)()
                        results['updated'] += 1
                        logger.debug(f"Updated contact {contact_id}")
                        
                    except Exception as save_error:
                        logger.error(f"Database save failed for contact {contact_id}: {save_error} - HubSpot URL: {hubspot_url}")
                        
                        # Log specific field information for database errors
                        if hasattr(self.processor, 'log_database_error'):
                            self.processor.log_database_error(save_error, record, "update")
                        
                        results['failed'] += 1
                else:
                    # Create new contact
                    try:
                        # Validate field lengths before creating
                        validated_record = self._validate_field_lengths(record, contact_id)
                        
                        contact = Hubspot_Contact(**validated_record)
                        await sync_to_async(contact.save)()
                        results['created'] += 1
                        logger.debug(f"Created contact {contact_id}")
                        
                    except Exception as save_error:
                        logger.error(f"Database save failed for new contact {contact_id}: {save_error} - HubSpot URL: {hubspot_url}")
                        
                        # Log specific field information for database errors
                        if hasattr(self.processor, 'log_database_error'):
                            self.processor.log_database_error(save_error, record, "create")
                        
                        results['failed'] += 1
                    
            except Exception as e:
                record_id = record.get('id', 'UNKNOWN')
                hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-1/{record_id}"
                logger.error(f"Error processing contact {record_id}: {e} - HubSpot URL: {hubspot_url}")
                results['failed'] += 1
                
        return results

    def _validate_field_lengths(self, record: Dict[str, Any], record_id: str) -> Dict[str, Any]:
        """Validate and truncate field lengths to prevent database errors"""
        validated_record = record.copy()
        
        # Define field length limits based on database schema
        field_limits = {
            'state': 10,
            'zip': 10,
            'phone': 50,
            'email': 100,
            'firstname': 100,
            'lastname': 100,
            'city': 100,
            'address': 255,
            'campaign_name': 255,
            'campaign_content': 255,
            'comments': 500,
            'original_lead_source': 100,
            'search_terms': 255,
            'reference_code': 100,
            'trustedform_cert_url': 500,
            'tier': 50,
            'vertical': 100,
            'division': 100,
        }
        
        hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-1/{record_id}"
        
        for field_name, max_length in field_limits.items():
            if field_name in validated_record and validated_record[field_name]:
                field_value = str(validated_record[field_name])
                if len(field_value) > max_length:
                    logger.warning(f"Field '{field_name}' too long ({len(field_value)} chars), truncating to {max_length} for contact {record_id}: '{field_value[:50]}{'...' if len(field_value) > 50 else ''}' - HubSpot URL: {hubspot_url}")
                    validated_record[field_name] = field_value[:max_length]
        
        return validated_record
        
        return results
    
    async def _force_overwrite_contacts(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite all contacts using bulk operations, ignoring timestamps"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        # Get all existing contact IDs that we're about to process
        contact_ids = [record['id'] for record in validated_data if record.get('id')]
        
        try:
            # Get existing contacts to determine which are updates vs creates
            existing_contacts = await sync_to_async(list)(
                Hubspot_Contact.objects.filter(id__in=contact_ids).values_list('id', flat=True)
            )
            existing_contact_set = set(existing_contacts)
            
            # Separate new vs existing records
            new_records = [record for record in validated_data if record.get('id') not in existing_contact_set]
            update_records = [record for record in validated_data if record.get('id') in existing_contact_set]
            
            # Force create new records
            if new_records:
                new_contact_objects = [Hubspot_Contact(**record) for record in new_records]
                await sync_to_async(Hubspot_Contact.objects.bulk_create)(
                    new_contact_objects,
                    batch_size=self.batch_size
                )
                results['created'] = len(new_records)
                logger.info(f"Force created {results['created']} new contacts")
            
            # Force update existing records - delete and recreate for true overwrite
            if update_records:
                # Delete existing records first
                await sync_to_async(Hubspot_Contact.objects.filter(id__in=[r['id'] for r in update_records]).delete)()
                
                # Recreate with new data
                update_contact_objects = [Hubspot_Contact(**record) for record in update_records]
                await sync_to_async(Hubspot_Contact.objects.bulk_create)(
                    update_contact_objects,
                    batch_size=self.batch_size
                )
                results['updated'] = len(update_records)
                logger.info(f"Force overwritten {results['updated']} existing contacts")
                
        except Exception as e:
            logger.error(f"Force bulk overwrite failed: {e}")
            results['failed'] = len(validated_data)
            
        return results
    
    async def _individual_force_save_contacts(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite contacts individually, ignoring timestamps"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                contact_id = record.get('id')
                if not contact_id:
                    logger.error(f"Contact record missing ID: {record}")
                    results['failed'] += 1
                    continue
                
                # Check if contact exists
                contact_exists = await sync_to_async(Hubspot_Contact.objects.filter(id=contact_id).exists)()
                
                if contact_exists:
                    # Force delete and recreate for complete overwrite
                    await sync_to_async(Hubspot_Contact.objects.filter(id=contact_id).delete)()
                    contact = Hubspot_Contact(**record)
                    await sync_to_async(contact.save)()
                    results['updated'] += 1
                    logger.debug(f"Force overwritten contact {contact_id}")
                else:
                    # Create new contact
                    contact = Hubspot_Contact(**record)
                    await sync_to_async(contact.save)()
                    results['created'] += 1
                    logger.debug(f"Force created contact {contact_id}")
                    
            except Exception as e:
                logger.error(f"Error force saving contact {record.get('id')}: {e}")
                results['failed'] += 1
                
                # Report individual contact errors to enterprise error handling
                await self.handle_sync_error(e, {
                    'operation': 'force_save_contact',
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
