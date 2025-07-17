"""
HubSpot appointments sync engine
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.clients.appointments import HubSpotAppointmentsClient
from ingestion.sync.hubspot.processors.appointments import HubSpotAppointmentProcessor
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
from ingestion.models.hubspot import Hubspot_Appointment

logger = logging.getLogger(__name__)

class HubSpotAppointmentSyncEngine(HubSpotBaseSyncEngine):
    """Sync engine for HubSpot appointments"""
    
    def __init__(self, **kwargs):
        super().__init__('appointments', **kwargs)
        self.force_overwrite = kwargs.get('force_overwrite', False)
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot appointments client and processor"""
        # Initialize enterprise features first
        await self.initialize_enterprise_features()
        
        self.client = HubSpotAppointmentsClient()
        await self.create_authenticated_session(self.client)
        self.processor = HubSpotAppointmentProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch appointment data from HubSpot"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        max_records = kwargs.get('max_records', 0)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            records_fetched = 0
            async for batch in self.client.fetch_appointments(
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
            logger.error(f"Error fetching appointments: {e}")
            # Use enterprise error handling
            await self.handle_sync_error(e, {
                'operation': 'fetch_data',
                'entity_type': 'appointments',
                'records_fetched': records_fetched
            })
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
        """Save appointment data to database with enterprise monitoring and bulk operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        try:
            # Check if force overwrite is enabled
            if self.force_overwrite:
                logger.info("Force overwrite mode - all records will be updated regardless of timestamps")
                results = await self._force_overwrite_appointments(validated_data)
            else:
                # Try bulk operations first for better performance
                results = await self._bulk_save_appointments(validated_data)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed, falling back to individual saves: {bulk_error}")
            # Fallback to individual saves
            if self.force_overwrite:
                results = await self._individual_force_save_appointments(validated_data)
            else:
                results = await self._individual_save_appointments(validated_data)

        # Calculate and report enterprise metrics
        total_processed = len(validated_data)
        success_count = results['created'] + results['updated']
        success_rate = success_count / total_processed if total_processed > 0 else 0

        # Report metrics to enterprise monitoring system
        await self.report_sync_metrics({
            'entity_type': 'appointments',
            'processed': total_processed,
            'success_rate': success_rate,
            'results': results
        })

        logger.info(f"Appointment sync completed - Created: {results['created']}, "
                   f"Updated: {results['updated']}, Failed: {results['failed']}, "
                   f"Success Rate: {success_rate:.2%}")

        return results

    async def _bulk_save_appointments(self, validated_data: List[Dict]) -> Dict[str, int]:
        """True bulk upsert for appointments using bulk_create with update_conflicts=True"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        # Prepare objects
        appointment_objects = [Hubspot_Appointment(**record) for record in validated_data]
        try:
            created_appointments = await sync_to_async(Hubspot_Appointment.objects.bulk_create)(
                appointment_objects,
                batch_size=self.batch_size,
                update_conflicts=True,
                update_fields=[
                    "appointment_id", "genius_appointment_id", "marketsharp_id", "hs_appointment_name", "hs_appointment_start", "hs_appointment_end", "hs_duration", "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "hs_pipeline", "hs_pipeline_stage", "hs_all_accessible_team_ids", "hs_all_assigned_business_unit_ids", "hs_all_owner_ids", "hs_all_team_ids", "hs_created_by_user_id", "hs_merged_object_ids", "hs_object_source", "hs_object_source_detail_1", "hs_object_source_detail_2", "hs_object_source_detail_3", "hs_object_source_id", "hs_object_source_label", "hs_object_source_user_id", "hs_owning_teams", "hs_read_only", "hs_shared_team_ids", "hs_shared_user_ids", "hs_unique_creation_key", "hs_updated_by_user_id", "hs_user_ids_of_all_notification_followers", "hs_user_ids_of_all_notification_unfollowers", "hs_user_ids_of_all_owners", "hs_was_imported", "first_name", "last_name", "email", "phone1", "phone2", "address1", "address2", "city", "state", "zip", "date", "time", "duration", "appointment_status", "appointment_response", "is_complete", "appointment_services", "lead_services", "product_interest_primary", "product_interest_secondary", "user_id", "canvasser", "canvasser_id", "canvasser_email", "hubspot_owner_id", "hubspot_owner_assigneddate", "hubspot_team_id", "division_id", "primary_source", "secondary_source", "prospect_id", "prospect_source_id", "hscontact_id", "type_id", "type_id_text", "marketsharp_appt_type", "complete_date", "complete_outcome_id", "complete_outcome_id_text", "complete_user_id", "confirm_date", "confirm_user_id", "confirm_with", "assign_date", "add_date", "add_user_id", "arrivy_appt_date", "arrivy_confirm_date", "arrivy_confirm_user", "arrivy_created_by", "arrivy_object_id", "arrivy_status", "arrivy_user", "arrivy_user_divison_id", "arrivy_user_external_id", "arrivy_username", "salespro_both_homeowners", "salespro_deadline", "salespro_deposit_type", "salespro_fileurl_contract", "salespro_fileurl_estimate", "salespro_financing", "salespro_job_size", "salespro_job_type", "salespro_last_price_offered", "salespro_notes", "salespro_one_year_price", "salespro_preferred_payment", "salespro_requested_start", "salespro_result", "salespro_result_notes", "salespro_result_reason_demo", "salespro_result_reason_no_demo", "notes", "log", "title", "marketing_task_id", "leap_estimate_id", "spouses_present", "year_built", "error_details", "tester_test", "created_at", "updated_at", "archived"
                ],
                unique_fields=["id"]
            )
            results['created'] = len([obj for obj in created_appointments if obj._state.adding])
            results['updated'] = len(validated_data) - results['created']
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            results['failed'] = len(validated_data)
            
            # Log detailed information about the failed batch for debugging
            logger.error(f"Failed batch details: {len(validated_data)} appointments")
            for record in validated_data:
                record_id = record.get('id', 'UNKNOWN')
                hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-421/{record_id}"
                logger.error(f"Failed record in batch - Appointment ID: {record_id} - HubSpot URL: {hubspot_url}")
                
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
            individual_results = await self._individual_save_appointments(validated_data)
            
            # Update results with individual processing outcomes
            results['created'] = individual_results['created']
            results['updated'] = individual_results['updated']
            results['failed'] = individual_results['failed']
        return results

    async def _individual_save_appointments(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Fallback individual save operation with detailed error handling"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                appointment_id = record.get('id')
                if not appointment_id:
                    logger.error(f"Appointment record missing ID: {record}")
                    results['failed'] += 1
                    continue

                hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-421/{appointment_id}"
                
                # Check if appointment exists
                appointment_exists = await sync_to_async(Hubspot_Appointment.objects.filter(id=appointment_id).exists)()
                
                if appointment_exists:
                    # Update existing appointment
                    try:
                        existing_appointment = await sync_to_async(Hubspot_Appointment.objects.get)(id=appointment_id)
                        
                        # Validate field lengths before saving to prevent database errors
                        validated_record = self._validate_field_lengths(record, appointment_id)
                        
                        for field, value in validated_record.items():
                            if hasattr(existing_appointment, field):
                                setattr(existing_appointment, field, value)
                        
                        await sync_to_async(existing_appointment.save)()
                        results['updated'] += 1
                        logger.debug(f"Updated appointment {appointment_id}")
                        
                    except Exception as save_error:
                        logger.error(f"Database save failed for appointment {appointment_id}: {save_error} - HubSpot URL: {hubspot_url}")
                        
                        # Log specific field information for database errors
                        if hasattr(self.processor, 'log_database_error'):
                            self.processor.log_database_error(save_error, record, "update")
                        
                        results['failed'] += 1
                else:
                    # Create new appointment
                    try:
                        # Validate field lengths before creating
                        validated_record = self._validate_field_lengths(record, appointment_id)
                        
                        appointment = Hubspot_Appointment(**validated_record)
                        await sync_to_async(appointment.save)()
                        results['created'] += 1
                        logger.debug(f"Created appointment {appointment_id}")
                        
                    except Exception as save_error:
                        logger.error(f"Database save failed for new appointment {appointment_id}: {save_error} - HubSpot URL: {hubspot_url}")
                        
                        # Log specific field information for database errors
                        if hasattr(self.processor, 'log_database_error'):
                            self.processor.log_database_error(save_error, record, "create")
                        
                        results['failed'] += 1
                    
            except Exception as e:
                record_id = record.get('id', 'UNKNOWN')
                hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-421/{record_id}"
                logger.error(f"Error processing appointment {record_id}: {e} - HubSpot URL: {hubspot_url}")
                results['failed'] += 1
                
        return results

    def _validate_field_lengths(self, record: Dict[str, Any], record_id: str) -> Dict[str, Any]:
        """Validate and truncate field lengths to prevent database errors"""
        validated_record = record.copy()
        
        # Define field length limits based on database schema
        field_limits = {
            'state': 10,
            'zip': 10,
            'phone1': 50,
            'phone2': 50,
            'email': 100,
            'canvasser_email': 100,
            'first_name': 100,
            'last_name': 100,
            'city': 100,
            'address1': 255,
            'address2': 255,
            'appointment_status': 50,
            'cancel_reason': 255,
            'div_cancel_reasons': 255,
            'qc_cancel_reasons': 255,
            'division': 100,
            'sourcefield': 100,
        }
        
        hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-421/{record_id}"
        
        for field_name, max_length in field_limits.items():
            if field_name in validated_record and validated_record[field_name]:
                field_value = str(validated_record[field_name])
                if len(field_value) > max_length:
                    logger.warning(f"Field '{field_name}' too long ({len(field_value)} chars), truncating to {max_length} for appointment {record_id}: '{field_value[:50]}{'...' if len(field_value) > 50 else ''}' - HubSpot URL: {hubspot_url}")
                    validated_record[field_name] = field_value[:max_length]
        
        return validated_record
        for record in validated_data:
            try:
                appointment_id = record.get('id')
                if not appointment_id:
                    logger.error(f"Appointment record missing ID: {record}")
                    results['failed'] += 1
                    continue
                appointment, created = await sync_to_async(Hubspot_Appointment.objects.get_or_create)(
                    id=appointment_id,
                    defaults=record
                )
                if not created:
                    for field, value in record.items():
                        if hasattr(appointment, field):
                            setattr(appointment, field, value)
                    await sync_to_async(appointment.save)()
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
            except Exception as e:
                logger.error(f"Error saving appointment {record.get('id')}: {e}")
                results['failed'] += 1
        return results

    async def _force_overwrite_appointments(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite all appointments using bulk operations, ignoring timestamps"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        # Get all existing appointment IDs that we're about to process
        appointment_ids = [record['id'] for record in validated_data if record.get('id')]
        
        try:
            # Get existing appointments to determine which are updates vs creates
            existing_appointments = await sync_to_async(list)(
                Hubspot_Appointment.objects.filter(id__in=appointment_ids).values_list('id', flat=True)
            )
            existing_appointment_set = set(existing_appointments)
            
            # Separate new vs existing records
            new_records = [record for record in validated_data if record.get('id') not in existing_appointment_set]
            update_records = [record for record in validated_data if record.get('id') in existing_appointment_set]
            
            # Force create new records
            if new_records:
                new_appointment_objects = [Hubspot_Appointment(**record) for record in new_records]
                await sync_to_async(Hubspot_Appointment.objects.bulk_create)(
                    new_appointment_objects,
                    batch_size=self.batch_size
                )
                results['created'] = len(new_records)
                logger.info(f"Force created {results['created']} new appointments")
            
            # Force update existing records - delete and recreate for true overwrite
            if update_records:
                # Delete existing records first
                await sync_to_async(Hubspot_Appointment.objects.filter(id__in=[r['id'] for r in update_records]).delete)()
                
                # Recreate with new data
                update_appointment_objects = [Hubspot_Appointment(**record) for record in update_records]
                await sync_to_async(Hubspot_Appointment.objects.bulk_create)(
                    update_appointment_objects,
                    batch_size=self.batch_size
                )
                results['updated'] = len(update_records)
                logger.info(f"Force overwritten {results['updated']} existing appointments")
                
        except Exception as e:
            logger.error(f"Force bulk overwrite failed: {e}")
            results['failed'] = len(validated_data)
            
            # Log problematic records with HubSpot URLs for debugging
            for record in validated_data:
                record_id = record.get('id', 'UNKNOWN')
                hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-421/{record_id}"
                logger.error(f"Failed record in batch - Appointment ID: {record_id} - HubSpot URL: {hubspot_url}")
                
                # Log key field values for debugging database constraint issues
                debug_fields = ['first_name', 'last_name', 'email', 'phone1', 'state', 'zip', 'city', 'address1']
                field_values = []
                for field in debug_fields:
                    if field in record and record[field]:
                        value = str(record[field])
                        display_value = value[:30] + ('...' if len(value) > 30 else '')
                        field_values.append(f"{field}='{display_value}'")
                
                if field_values:
                    logger.error(f"Record {record_id} debug fields: {', '.join(field_values)}")
            
            # Attempt individual record processing to save what we can
            logger.info(f"Attempting individual record processing for {len(validated_data)} failed records")
            individual_results = await self._individual_force_save_appointments(validated_data)
            
            # Update results with individual processing outcomes
            results['created'] = individual_results['created']
            results['updated'] = individual_results['updated'] 
            results['failed'] = individual_results['failed']
            
        return results

    async def _individual_force_save_appointments(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite appointments individually, ignoring timestamps"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                appointment_id = record.get('id')
                if not appointment_id:
                    logger.error(f"Appointment record missing ID: {record}")
                    results['failed'] += 1
                    continue
                
                # Check if appointment exists
                try:
                    existing_appointment = await sync_to_async(Hubspot_Appointment.objects.get)(id=appointment_id)
                    # Delete existing and recreate for true overwrite
                    await sync_to_async(existing_appointment.delete)()
                    appointment = Hubspot_Appointment(**record)
                    await sync_to_async(appointment.save)()
                    results['updated'] += 1
                    logger.debug(f"Force overwritten appointment {appointment_id}")
                except Hubspot_Appointment.DoesNotExist:
                    # Create new appointment
                    appointment = Hubspot_Appointment(**record)
                    await sync_to_async(appointment.save)()
                    results['created'] += 1
                    logger.debug(f"Force created appointment {appointment_id}")
                    
            except Exception as e:
                logger.error(f"Error force saving appointment {record.get('id')}: {e}")
                results['failed'] += 1
                
                # Report individual appointment errors to enterprise error handling
                await self.handle_sync_error(e, {
                    'operation': 'force_save_appointment',
                    'appointment_id': record.get('id'),
                    'record': record
                })
        
        return results
