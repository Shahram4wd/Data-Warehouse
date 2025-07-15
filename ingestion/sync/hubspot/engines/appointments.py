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
            # Try bulk operations first for better performance
            results = await self._bulk_save_appointments(validated_data)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed, falling back to individual saves: {bulk_error}")
            # Fallback to individual saves
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
