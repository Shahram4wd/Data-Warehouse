"""
HubSpot appointments sync engine
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from django.utils import timezone
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.clients.appointments import HubSpotAppointmentsClient
from ingestion.sync.hubspot.processors.appointments import HubSpotAppointmentProcessor
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
from ingestion.models.hubspot import Hubspot_Appointment
from ingestion.config.appointment_field_config import APPOINTMENT_FIELD_LIMITS

logger = logging.getLogger(__name__)

class HubSpotAppointmentSyncEngine(HubSpotBaseSyncEngine):
    """Sync engine for HubSpot appointments with enhanced monitoring"""
    
    def __init__(self, **kwargs):
        super().__init__('appointments', **kwargs)
        self.force_overwrite = kwargs.get('force_overwrite', False)
        self.sync_start_time = None
        self.last_progress_log = None
        self.processed_appointment_ids = set()  # Track processed IDs to detect loops
        
    async def initialize_client(self) -> None:
        """Initialize HubSpot appointments client and processor"""
        # Initialize enterprise features first
        await self.initialize_enterprise_features()
        
        self.client = HubSpotAppointmentsClient()
        await self.create_authenticated_session(self.client)
        self.processor = HubSpotAppointmentProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch appointment data from HubSpot with progress tracking"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', self.batch_size)
        max_records = kwargs.get('max_records', 0)
        
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            records_fetched = 0
            batches_processed = 0
            
            async for batch in self.client.fetch_appointments(
                last_sync=last_sync,
                limit=limit
            ):
                # If max_records is set, limit the records returned
                if max_records > 0:
                    if records_fetched >= max_records:
                        logger.info(f"Reached max_records limit ({max_records}), stopping fetch")
                        break
                    
                    # If this batch would exceed max_records, truncate it
                    if records_fetched + len(batch) > max_records:
                        batch = batch[:max_records - records_fetched]
                
                records_fetched += len(batch)
                batches_processed += 1
                
                # Log progress every 10 batches to avoid log spam
                if batches_processed % 10 == 0:
                    logger.info(f"Progress: {batches_processed} batches, {records_fetched} appointments fetched")
                
                yield batch
                
                # If we've reached max_records, stop fetching
                if max_records > 0 and records_fetched >= max_records:
                    logger.info(f"Reached max_records limit ({max_records}), stopping fetch")
                    break
            
            logger.info(f"Fetch completed: {batches_processed} batches, {records_fetched} total appointments")
                    
        except Exception as e:
            logger.error(f"Error fetching appointments: {e}")
            # Use enterprise error handling
            await self.handle_sync_error(e, {
                'operation': 'fetch_data',
                'entity_type': 'appointments',
                'records_fetched': records_fetched,
                'batches_processed': batches_processed
            })
            raise SyncException(f"Failed to fetch appointments: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform appointment data with loop detection"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        loop_detected_count = 0
        
        for record in raw_data:
            try:
                # Check for processing loops
                record_id = record.get('id') or record.get('hs_object_id')
                if record_id and record_id in self.processed_appointment_ids:
                    loop_detected_count += 1
                    logger.warning(f"Loop detected: Appointment ID {record_id} already processed - skipping")
                    continue
                
                if record_id:
                    self.processed_appointment_ids.add(record_id)
                
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming appointment record {record.get('id')}: {e}")
                # Continue processing other records
        
        if loop_detected_count > 0:
            logger.warning(f"Loop detection: Skipped {loop_detected_count} duplicate appointments in this batch")
                
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
                
            # If bulk operation had failures, retry only the failed records individually
            if results['failed'] > 0 and 'failed_records' in results and results['failed_records']:
                failed_records = results['failed_records']
                logger.warning(f"Bulk operation had {results['failed']} failures, retrying {len(failed_records)} records individually")
                
                # Retry only the failed records individually
                retry_results = await self._individual_save_appointments(failed_records) if not self.force_overwrite else await self._individual_force_save_appointments(failed_records)
                
                # Update results by combining successful bulk + successful individual retries
                results['created'] += retry_results['created']
                results['updated'] += retry_results['updated']
                results['failed'] = retry_results['failed']  # Only count the ones that still failed after retry
                
                if retry_results['failed'] < len(failed_records):
                    recovered_count = len(failed_records) - retry_results['failed']
                    logger.info(f"Individual retry recovered {recovered_count} records from bulk failures")
                    
        except Exception as bulk_error:
            logger.warning(f"Bulk save operation threw exception, falling back to individual saves: {bulk_error}")
            # Fallback to individual saves for all records
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
        
        # Log comprehensive sync statistics
        total_unique_processed = len(self.processed_appointment_ids)
        logger.info(f"Sync Statistics - Total unique appointments processed: {total_unique_processed}")
        
        if total_unique_processed != total_processed:
            logger.warning(f"Duplicate detection: {total_processed - total_unique_processed} duplicate records were filtered during processing")

        return results

    async def _bulk_save_appointments(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Improved bulk upsert for appointments with better error handling and failed record tracking"""
        results = {'created': 0, 'updated': 0, 'failed': 0, 'failed_records': []}
        if not validated_data:
            return results

        # Deduplicate records by ID to avoid PostgreSQL "cannot affect row a second time" error
        # Keep the last occurrence of each ID (most recent data)
        seen_ids = set()
        deduplicated_data = []
        for record in reversed(validated_data):  # Reverse to keep last occurrence
            record_id = record.get('id')
            if record_id and record_id not in seen_ids:
                seen_ids.add(record_id)
                deduplicated_data.append(record)
        
        deduplicated_data.reverse()  # Restore original order
        
        if len(deduplicated_data) != len(validated_data):
            duplicates_count = len(validated_data) - len(deduplicated_data)
            logger.warning(f"Removed {duplicates_count} duplicate appointment IDs from batch of {len(validated_data)} records")

        # Truncate long field values to prevent database errors
        for record in deduplicated_data:
            self._truncate_long_fields(record)

        # Try to prepare objects and catch individual record errors
        appointment_objects = []
        failed_records = []
        
        for record in deduplicated_data:
            try:
                # Set sync timestamp fields since bulk_create bypasses auto_now/auto_now_add
                now = timezone.now()
                record['sync_created_at'] = now
                record['sync_updated_at'] = now
                
                appointment_obj = Hubspot_Appointment(**record)
                appointment_objects.append(appointment_obj)
            except Exception as e:
                logger.error(f"Error creating appointment object for record {record.get('id')}: {e}")
                failed_records.append(record)
        
        # If we have valid objects, try bulk create
        if appointment_objects:
            try:
                created_appointments = await sync_to_async(Hubspot_Appointment.objects.bulk_create)(
                    appointment_objects,
                    batch_size=self.batch_size,
                    update_conflicts=True,
                    update_fields=[
                        "appointment_id", "genius_appointment_id", "genius_prospect_id", "marketsharp_id", "hs_appointment_name", "hs_appointment_start", "hs_appointment_end", "hs_duration", "hs_object_id", "hs_createdate", "hs_lastmodifieddate", "hs_pipeline", "hs_pipeline_stage", "hs_all_accessible_team_ids", "hs_all_assigned_business_unit_ids", "hs_all_owner_ids", "hs_all_team_ids", "hs_created_by_user_id", "hs_merged_object_ids", "hs_object_source", "hs_object_source_detail_1", "hs_object_source_detail_2", "hs_object_source_detail_3", "hs_object_source_id", "hs_object_source_label", "hs_object_source_user_id", "hs_owning_teams", "hs_read_only", "hs_shared_team_ids", "hs_shared_user_ids", "hs_unique_creation_key", "hs_updated_by_user_id", "hs_user_ids_of_all_notification_followers", "hs_user_ids_of_all_notification_unfollowers", "hs_user_ids_of_all_owners", "hs_was_imported", "first_name", "last_name", "email", "phone1", "phone2", "address1", "address2", "city", "state", "zip", "date", "time", "duration", "appointment_status", "appointment_confirmed", "appointment_response", "is_complete", "cancel_reason", "div_cancel_reasons", "qc_cancel_reasons", "appointment_services", "lead_services", "product_interest_primary", "product_interest_secondary", "user_id", "canvasser", "canvasser_id", "canvasser_email", "hubspot_owner_id", "hubspot_owner_assigneddate", "hubspot_team_id", "division_id", "division", "primary_source", "secondary_source", "prospect_id", "prospect_source_id", "hscontact_id", "sourcefield", "type_id", "type_id_text", "marketsharp_appt_type", "complete_date", "complete_outcome_id", "complete_outcome_id_text", "complete_user_id", "confirm_date", "confirm_user_id", "confirm_with", "assign_date", "add_date", "add_user_id", "arrivy_appt_date", "arrivy_confirm_date", "arrivy_confirm_user", "arrivy_created_by", "arrivy_details", "arrivy_notes", "arrivy_object_id", "arrivy_result_full_string", "arrivy_salesrep_first_name", "arrivy_salesrep_last_name", "arrivy_status", "arrivy_status_title", "arrivy_user", "arrivy_user_divison_id", "arrivy_user_external_id", "arrivy_username", "salespro_both_homeowners", "salespro_consider_solar", "salespro_customer_id", "salespro_deadline", "salespro_deposit_type", "salespro_estimate_id", "salespro_fileurl_contract", "salespro_fileurl_estimate", "salespro_financing", "salespro_job_size", "salespro_job_type", "salespro_last_price_offered", "salespro_notes", "salespro_one_year_price", "salespro_preferred_payment", "salespro_requested_start", "salespro_result", "salespro_result_notes", "salespro_result_reason_demo", "salespro_result_reason_no_demo", "notes", "log", "title", "marketing_task_id", "leap_estimate_id", "spouses_present", "year_built", "error_details", "tester_test", "created_by_make", "f9_tfuid", "set_date", "genius_quote_id", "genius_quote_response", "genius_quote_response_status", "genius_response", "genius_response_status", "genius_resubmit", "archived", "sync_created_at", "sync_updated_at"
                    ],
                    unique_fields=["id"]
                )
                results['created'] = len([obj for obj in created_appointments if obj._state.adding])
                results['updated'] = len(appointment_objects) - results['created']
            except Exception as e:
                logger.error(f"Bulk upsert failed: {e}")
                # Log specific field issues if they exist
                if "value too long" in str(e):
                    logger.error(f"Field length validation error - check field lengths in appointment data")
                # If bulk create fails, all objects become failed records
                failed_records.extend([dict(obj.__dict__) for obj in appointment_objects])
        
        # Track failed records for individual retry
        results['failed'] = len(failed_records)
        results['failed_records'] = failed_records
        
        return results

    def _truncate_long_fields(self, record: Dict[str, Any]) -> None:
        """Truncate fields that are too long for database constraints"""
        for field_name, max_length in APPOINTMENT_FIELD_LIMITS.items():
            if field_name in record and record[field_name] is not None:
                field_value = str(record[field_name])
                if len(field_value) > max_length:
                    original_length = len(field_value)
                    record[field_name] = field_value[:max_length]
                    logger.warning(f"Truncated field '{field_name}' from {original_length} to {max_length} chars for record {record.get('id')}")

    def reset_progress_tracking(self) -> None:
        """Reset progress tracking for new sync operations"""
        self.processed_appointment_ids.clear()
        self.sync_start_time = None
        self.last_progress_log = None
        logger.info("Progress tracking reset for new sync operation")

    async def _individual_save_appointments(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Fallback individual save operation with detailed error handling and recovery"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        error_categories = {'missing_id': 0, 'field_errors': 0, 'constraint_errors': 0, 'other_errors': 0}
        
        for record in validated_data:
            try:
                appointment_id = record.get('id')
                if not appointment_id:
                    logger.error(f"Appointment record missing ID: {record}")
                    results['failed'] += 1
                    error_categories['missing_id'] += 1
                    continue
                
                # Clean and truncate fields before attempting save
                cleaned_record = record.copy()
                self._truncate_long_fields(cleaned_record)
                
                # Try to clean problematic fields
                self._clean_record_fields(cleaned_record)
                
                appointment, created = await sync_to_async(Hubspot_Appointment.objects.get_or_create)(
                    id=appointment_id,
                    defaults=cleaned_record
                )
                if not created:
                    # Update existing record
                    for field, value in cleaned_record.items():
                        if hasattr(appointment, field):
                            setattr(appointment, field, value)
                    await sync_to_async(appointment.save)()
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                error_str = str(e)
                logger.error(f"Error saving appointment {record.get('id')}: {e}")
                results['failed'] += 1
                
                # Categorize errors for better debugging
                if "duplicate key" in error_str:
                    error_categories['constraint_errors'] += 1
                elif "value too long" in error_str:
                    error_categories['field_errors'] += 1
                    logger.error(f"Field length error for appointment {record.get('id')}: {e}")
                elif "invalid input syntax" in error_str:
                    error_categories['field_errors'] += 1
                    logger.error(f"Field format error for appointment {record.get('id')}: {e}")
                else:
                    error_categories['other_errors'] += 1
        
        # Log error summary
        if results['failed'] > 0:
            logger.warning(f"Individual save errors breakdown: {error_categories}")
            
        return results

    def _clean_record_fields(self, record: Dict[str, Any]) -> None:
        """Clean problematic field values that commonly cause database errors"""
        # Clean email fields
        if 'email' in record and record['email']:
            email = str(record['email']).strip()
            if email == '.' or email == '' or len(email) < 3 or '@' not in email:
                record['email'] = None
        
        # Clean phone fields
        for phone_field in ['phone1', 'phone2']:
            if phone_field in record and record[phone_field]:
                phone = str(record[phone_field]).strip()
                if phone in ['(No value)', '.', '', 'N/A'] or len(phone) < 3:
                    record[phone_field] = None
        
        # Clean URL fields
        for url_field in ['salespro_fileurl_contract', 'salespro_fileurl_estimate']:
            if url_field in record and record[url_field]:
                url = str(record[url_field]).strip()
                if url in ['N', 'n/a', '', '.'] or not url.startswith(('http://', 'https://')):
                    record[url_field] = None
        
        # Clean zip codes
        if 'zip' in record and record['zip']:
            zip_code = str(record['zip']).strip()
            if len(zip_code) < 4 or not zip_code.replace('-', '').isdigit():
                record['zip'] = None
        
        # Clean numeric fields that might have invalid values
        for numeric_field in ['type_id', 'complete_outcome_id', 'complete_user_id', 'confirm_user_id', 'add_user_id']:
            if numeric_field in record and record[numeric_field]:
                try:
                    int(record[numeric_field])
                except (ValueError, TypeError):
                    record[numeric_field] = None

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
