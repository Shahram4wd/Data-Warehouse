"""
HubSpot appointments processor
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from ingestion.base.exceptions import ValidationException
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor
from ingestion.models.hubspot import Hubspot_Appointment

logger = logging.getLogger(__name__)

class HubSpotAppointmentProcessor(HubSpotBaseProcessor):
    """Process HubSpot appointment data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_Appointment, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return comprehensive field mappings from HubSpot to model"""
        return {
            # Core appointment fields
            'id': 'id',
            'properties.appointment_id': 'appointment_id',
            'properties.genius_appointment_id': 'genius_appointment_id',
            'properties.marketsharp_id': 'marketsharp_id',
            'properties.hs_appointment_name': 'hs_appointment_name',
            'properties.hs_appointment_start': 'hs_appointment_start',
            'properties.hs_appointment_end': 'hs_appointment_end',
            'properties.hs_duration': 'hs_duration',
            'properties.hs_object_id': 'hs_object_id',
            'properties.hs_createdate': 'hs_createdate',
            'properties.hs_lastmodifieddate': 'hs_lastmodifieddate',
            'properties.hs_pipeline': 'hs_pipeline',
            'properties.hs_pipeline_stage': 'hs_pipeline_stage',
            
            # Contact information
            'properties.first_name': 'first_name',
            'properties.last_name': 'last_name',
            'properties.email': 'email',
            'properties.phone1': 'phone1',
            'properties.phone2': 'phone2',
            'properties.address1': 'address1',
            'properties.address2': 'address2',
            'properties.city': 'city',
            'properties.state': 'state',
            'properties.zip': 'zip',
            
            # Appointment scheduling
            'properties.date': 'date',
            'properties.time': 'time',
            'properties.duration': 'duration',
            'properties.appointment_status': 'appointment_status',
            'properties.appointment_confirmed': 'appointment_confirmed',
            'properties.appointment_response': 'appointment_response',
            'properties.is_complete': 'is_complete',
            
            # Cancel reasons
            'properties.cancel_reason': 'cancel_reason',
            'properties.div_cancel_reasons': 'div_cancel_reasons',
            'properties.qc_cancel_reasons': 'qc_cancel_reasons',
            'properties.appointment_services': 'appointment_services',
            'properties.lead_services': 'lead_services',
            'properties.type_id': 'type_id',
            'properties.type_id_text': 'type_id_text',
            'properties.marketsharp_appt_type': 'marketsharp_appt_type',
            
            # User and assignment
            'properties.user_id': 'user_id',
            'properties.canvasser': 'canvasser',
            'properties.canvasser_id': 'canvasser_id',
            'properties.canvasser_email': 'canvasser_email',
            'properties.hubspot_owner_id': 'hubspot_owner_id',
            'properties.hubspot_owner_assigneddate': 'hubspot_owner_assigneddate',
            'properties.hubspot_team_id': 'hubspot_team_id',
            'properties.division_id': 'division_id',
            'properties.division': 'division',
            'properties.primary_source': 'primary_source',
            'properties.secondary_source': 'secondary_source',
            'properties.prospect_id': 'prospect_id',
            'properties.prospect_source_id': 'prospect_source_id',
            'properties.hscontact_id': 'hscontact_id',
            'properties.sourcefield': 'sourcefield',
            
            # Completion and confirmation
            'properties.complete_date': 'complete_date',
            'properties.complete_outcome_id': 'complete_outcome_id',
            'properties.complete_outcome_id_text': 'complete_outcome_id_text',
            'properties.complete_user_id': 'complete_user_id',
            'properties.confirm_date': 'confirm_date',
            'properties.confirm_user_id': 'confirm_user_id',
            'properties.confirm_with': 'confirm_with',
            'properties.assign_date': 'assign_date',
            'properties.add_date': 'add_date',
            'properties.add_user_id': 'add_user_id',
            
            # Arrivy integration fields
            'properties.arrivy_appt_date': 'arrivy_appt_date',
            'properties.arrivy_confirm_date': 'arrivy_confirm_date',
            'properties.arrivy_confirm_user': 'arrivy_confirm_user',
            'properties.arrivy_created_by': 'arrivy_created_by',
            'properties.arrivy_details': 'arrivy_details',
            'properties.arrivy_notes': 'arrivy_notes',
            'properties.arrivy_object_id': 'arrivy_object_id',
            'properties.arrivy_result_full_string': 'arrivy_result_full_string',
            'properties.arrivy_salesrep_first_name': 'arrivy_salesrep_first_name',
            'properties.arrivy_salesrep_last_name': 'arrivy_salesrep_last_name',
            'properties.arrivy_status': 'arrivy_status',
            'properties.arrivy_status_title': 'arrivy_status_title',
            'properties.arrivy_user': 'arrivy_user',
            'properties.arrivy_user_divison_id': 'arrivy_user_divison_id',
            'properties.arrivy_user_external_id': 'arrivy_user_external_id',
            'properties.arrivy_username': 'arrivy_username',
            
            # SalesPro integration fields
            'properties.salespro_both_homeowners': 'salespro_both_homeowners',
            'properties.salespro_consider_solar': 'salespro_consider_solar',
            'properties.salespro_customer_id': 'salespro_customer_id',
            'properties.salespro_deadline': 'salespro_deadline',
            'properties.salespro_deposit_type': 'salespro_deposit_type',
            'properties.salespro_estimate_id': 'salespro_estimate_id',
            'properties.salespro_fileurl_contract': 'salespro_fileurl_contract',
            'properties.salespro_fileurl_estimate': 'salespro_fileurl_estimate',
            'properties.salespro_financing': 'salespro_financing',
            'properties.salespro_job_size': 'salespro_job_size',
            'properties.salespro_job_type': 'salespro_job_type',
            'properties.salespro_last_price_offered': 'salespro_last_price_offered',
            'properties.salespro_notes': 'salespro_notes',
            'properties.salespro_one_year_price': 'salespro_one_year_price',
            'properties.salespro_preferred_payment': 'salespro_preferred_payment',
            'properties.salespro_requested_start': 'salespro_requested_start',
            'properties.salespro_result': 'salespro_result',
            'properties.salespro_result_notes': 'salespro_result_notes',
            'properties.salespro_result_reason_demo': 'salespro_result_reason_demo',
            'properties.salespro_result_reason_no_demo': 'salespro_result_reason_no_demo',
            
            # Notes and additional fields
            'properties.notes': 'notes',
            'properties.log': 'log',
            'properties.title': 'title',
            'properties.marketing_task_id': 'marketing_task_id',
            'properties.leap_estimate_id': 'leap_estimate_id',
            'properties.spouses_present': 'spouses_present',
            'properties.year_built': 'year_built',
            'properties.error_details': 'error_details',
            'properties.tester_test': 'tester_test',
            'properties.created_by_make': 'created_by_make',
            'properties.f9_tfuid': 'f9_tfuid',
            'properties.set_date': 'set_date',
            
            # Genius integration fields
            'properties.genius_quote_id': 'genius_quote_id',
            'properties.genius_quote_response': 'genius_quote_response',
            'properties.genius_quote_response_status': 'genius_quote_response_status',
            'properties.genius_response': 'genius_response',
            'properties.genius_response_status': 'genius_response_status',
            'properties.genius_resubmit': 'genius_resubmit',
        }
    
    def get_field_types(self) -> Dict[str, str]:
        """Return field type mappings for validation"""
        return {
            # String fields with length constraints - will be handled by validate_field with max_length
            'appointment_id': 'string',
            'genius_appointment_id': 'string', 
            'marketsharp_id': 'string',
            'hs_appointment_name': 'string',
            'hs_object_id': 'object_id',
            'hs_pipeline': 'string',
            'hs_pipeline_stage': 'string',
            'first_name': 'string',
            'last_name': 'string',
            'email': 'email',
            'phone1': 'phone',
            'phone2': 'phone',
            'address1': 'string',
            'address2': 'string',
            'city': 'string',
            'state': 'state',
            'zip': 'zip_code',
            'appointment_status': 'string',
            'appointment_confirmed': 'string',
            'appointment_response': 'string',
            'cancel_reason': 'string',
            'div_cancel_reasons': 'string',
            'qc_cancel_reasons': 'string',
            'type_id_text': 'string',
            'marketsharp_appt_type': 'string',
            'user_id': 'string',
            'canvasser': 'string',
            'canvasser_id': 'string',
            'canvasser_email': 'email',
            'hubspot_owner_id': 'string',
            'hubspot_team_id': 'string',
            'division_id': 'string',
            'division': 'string',
            'primary_source': 'string',
            'secondary_source': 'string',
            'prospect_id': 'string',
            'prospect_source_id': 'string',
            'hscontact_id': 'string',
            'sourcefield': 'string',
            'complete_outcome_id_text': 'string',
            'confirm_with': 'string',
            'title': 'string',
            'leap_estimate_id': 'string',
            'tester_test': 'string',
            'created_by_make': 'string',
            'f9_tfuid': 'string',
            
            # DateTime fields
            'hs_appointment_start': 'datetime',
            'hs_appointment_end': 'datetime', 
            'hs_createdate': 'datetime',
            'hs_lastmodifieddate': 'datetime',
            'hubspot_owner_assigneddate': 'datetime',
            'complete_date': 'datetime',
            'confirm_date': 'datetime',
            'assign_date': 'datetime',
            'add_date': 'datetime',
            'arrivy_appt_date': 'datetime',
            'arrivy_confirm_date': 'datetime',
            
            # Date fields (not datetime)
            'date': 'date',
            'salespro_deadline': 'string',  # Changed from 'date' to 'string' to match CharField model
            'salespro_requested_start': 'string',  # Changed from 'date' to 'string' to match CharField model
            'set_date': 'date',
            
            # Time fields
            'time': 'time',
            
            # Integer fields
            'type_id': 'integer',
            'complete_outcome_id': 'integer',
            'complete_user_id': 'integer',
            'confirm_user_id': 'integer',
            'add_user_id': 'integer',
            'marketing_task_id': 'integer',
            'duration': 'integer',
            'hs_duration': 'integer',
            'year_built': 'integer',
            
            # Boolean fields
            'is_complete': 'boolean',
            'salespro_both_homeowners': 'string',  # Changed from 'boolean' to 'string' to match CharField model
            'spouses_present': 'integer',  # Changed from 'boolean' to 'integer' to match IntegerField model
            
            # URL fields  
            'salespro_fileurl_contract': 'url',
            'salespro_fileurl_estimate': 'url',
            
            # Text fields (no validation needed)
            'appointment_services': 'text',
            'lead_services': 'text',
            'notes': 'text',
            'log': 'text',
            'error_details': 'text',
            'arrivy_details': 'text',
            'arrivy_notes': 'text',
            'salespro_financing': 'text',
            'salespro_notes': 'text',
            'salespro_result_notes': 'text',
            'genius_quote_response': 'text',
            'genius_response': 'text',
            
            # Other string fields (Arrivy, SalesPro, Genius with length limits)
            'arrivy_confirm_user': 'string',
            'arrivy_created_by': 'string',
            'arrivy_object_id': 'string',
            'arrivy_result_full_string': 'string',
            'arrivy_salesrep_first_name': 'string',
            'arrivy_salesrep_last_name': 'string',
            'arrivy_status': 'string',
            'arrivy_status_title': 'string',
            'arrivy_user': 'string',
            'arrivy_user_divison_id': 'string',
            'arrivy_user_external_id': 'string',
            'arrivy_username': 'string',
            'salespro_consider_solar': 'string',
            'salespro_customer_id': 'string',
            'salespro_deposit_type': 'string',
            'salespro_estimate_id': 'string',
            'salespro_job_size': 'string',
            'salespro_job_type': 'string',
            'salespro_last_price_offered': 'string',
            'salespro_one_year_price': 'string',
            'salespro_preferred_payment': 'string',
            'salespro_result': 'string',
            'salespro_result_reason_demo': 'string',
            'salespro_result_reason_no_demo': 'string',
            'genius_quote_id': 'string',
            'genius_quote_response_status': 'string',
            'genius_response_status': 'string',
            'genius_resubmit': 'string',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot appointment record to model format"""
        properties = record.get('properties', {})
        record_id = record.get('id', 'UNKNOWN')
        
        return {
            'id': record.get('id'),
            'appointment_id': self._truncate_field(properties.get('appointment_id'), 255, 'appointment_id', record_id),
            'genius_appointment_id': self._truncate_field(properties.get('genius_appointment_id'), 255, 'genius_appointment_id', record_id),
            'marketsharp_id': self._truncate_field(properties.get('marketsharp_id'), 255, 'marketsharp_id', record_id),
            'hs_appointment_name': self._truncate_field(properties.get('hs_appointment_name'), 255, 'hs_appointment_name', record_id),
            'hs_appointment_start': self._parse_datetime(properties.get('hs_appointment_start')),
            'hs_appointment_end': self._parse_datetime(properties.get('hs_appointment_end')),
            'hs_duration': self.parse_duration(properties.get('hs_duration')),
            'hs_object_id': self._truncate_field(properties.get('hs_object_id'), 255, 'hs_object_id', record_id),
            'hs_createdate': self._parse_datetime(properties.get('hs_createdate')),
            'hs_lastmodifieddate': self._parse_datetime(properties.get('hs_lastmodifieddate')),
            'hs_pipeline': self._truncate_field(properties.get('hs_pipeline'), 255, 'hs_pipeline', record_id),
            'hs_pipeline_stage': self._truncate_field(properties.get('hs_pipeline_stage'), 255, 'hs_pipeline_stage', record_id),
            # Contact info
            'first_name': self._truncate_field(properties.get('first_name'), 255, 'first_name', record_id),
            'last_name': self._truncate_field(properties.get('last_name'), 255, 'last_name', record_id),
            'email': self._truncate_field(properties.get('email'), 255, 'email', record_id),  # EmailField but has max_length
            'phone1': self._truncate_field(properties.get('phone1'), 20, 'phone1', record_id),
            'phone2': self._truncate_field(properties.get('phone2'), 20, 'phone2', record_id),
            'address1': self._truncate_field(properties.get('address1'), 255, 'address1', record_id),
            'address2': self._truncate_field(properties.get('address2'), 255, 'address2', record_id),
            'city': self._truncate_field(properties.get('city'), 100, 'city', record_id),
            'state': self._truncate_field(properties.get('state'), 50, 'state', record_id),
            'zip': self._truncate_field(properties.get('zip'), 20, 'zip', record_id),
            # Appointment details
            'date': self._parse_datetime(properties.get('date')),
            'time': self._parse_time(properties.get('time'), record_id, 'time'),
            'duration': self.parse_duration(properties.get('duration')),
            'appointment_status': self._truncate_field(properties.get('appointment_status'), 100, 'appointment_status', record_id),
            'appointment_confirmed': self._truncate_field(properties.get('appointment_confirmed'), 100, 'appointment_confirmed', record_id),
            'appointment_response': self._truncate_field(properties.get('appointment_response'), 100, 'appointment_response', record_id),
            'is_complete': self._parse_boolean_not_null(properties.get('is_complete')),
            # Cancel reasons - Added missing fields
            'cancel_reason': self._truncate_field(properties.get('cancel_reason'), 255, 'cancel_reason', record_id),
            'div_cancel_reasons': self._truncate_field(properties.get('div_cancel_reasons'), 255, 'div_cancel_reasons', record_id),
            'qc_cancel_reasons': self._truncate_field(properties.get('qc_cancel_reasons'), 255, 'qc_cancel_reasons', record_id),
            'appointment_services': properties.get('appointment_services'),  # TextField - no truncation needed
            'lead_services': properties.get('lead_services'),  # TextField - no truncation needed
            'type_id': self._parse_integer(properties.get('type_id'), record_id, 'type_id'),  # Fixed: Convert to integer
            'type_id_text': self._truncate_field(properties.get('type_id_text'), 255, 'type_id_text', record_id),
            'marketsharp_appt_type': self._truncate_field(properties.get('marketsharp_appt_type'), 255, 'marketsharp_appt_type', record_id),
            # User and assignment
            'user_id': self._truncate_field(properties.get('user_id'), 255, 'user_id', record_id),
            'canvasser': self._truncate_field(properties.get('canvasser'), 255, 'canvasser', record_id),
            'canvasser_id': self._truncate_field(properties.get('canvasser_id'), 255, 'canvasser_id', record_id),
            'canvasser_email': self._truncate_field(properties.get('canvasser_email'), 255, 'canvasser_email', record_id),
            'hubspot_owner_id': self._truncate_field(properties.get('hubspot_owner_id'), 255, 'hubspot_owner_id', record_id),
            'hubspot_owner_assigneddate': self._parse_datetime(properties.get('hubspot_owner_assigneddate')),
            'hubspot_team_id': self._truncate_field(properties.get('hubspot_team_id'), 255, 'hubspot_team_id', record_id),
            'division_id': self._truncate_field(properties.get('division_id'), 255, 'division_id', record_id),
            'division': self._truncate_field(properties.get('division'), 255, 'division', record_id),
            'primary_source': self._truncate_field(properties.get('primary_source'), 255, 'primary_source', record_id),
            'secondary_source': self._truncate_field(properties.get('secondary_source'), 255, 'secondary_source', record_id),
            'prospect_id': self._truncate_field(properties.get('prospect_id'), 255, 'prospect_id', record_id),
            'prospect_source_id': self._truncate_field(properties.get('prospect_source_id'), 255, 'prospect_source_id', record_id),
            'hscontact_id': self._truncate_field(properties.get('hscontact_id'), 255, 'hscontact_id', record_id),
            'sourcefield': self._truncate_field(properties.get('sourcefield'), 255, 'sourcefield', record_id),
            # Completion and confirmation
            'complete_date': self._parse_datetime(properties.get('complete_date')),
            'complete_outcome_id': self._parse_integer(properties.get('complete_outcome_id'), record_id, 'complete_outcome_id'),  # Fixed: Convert to integer
            'complete_outcome_id_text': self._truncate_field(properties.get('complete_outcome_id_text'), 255, 'complete_outcome_id_text', record_id),
            'complete_user_id': self._parse_integer(properties.get('complete_user_id'), record_id, 'complete_user_id'),  # Fixed: Convert to integer
            'confirm_date': self._parse_datetime(properties.get('confirm_date')),
            'confirm_user_id': self._parse_integer(properties.get('confirm_user_id'), record_id, 'confirm_user_id'),  # Fixed: Convert to integer
            'confirm_with': self._truncate_field(properties.get('confirm_with'), 255, 'confirm_with', record_id),
            'assign_date': self._parse_datetime(properties.get('assign_date')),
            'add_date': self._parse_datetime(properties.get('add_date')),
            'add_user_id': self._parse_integer(properties.get('add_user_id'), record_id, 'add_user_id'),  # Fixed: Convert to integer
            # Arrivy integration fields - Added missing fields
            'arrivy_appt_date': self._parse_datetime(properties.get('arrivy_appt_date')),
            'arrivy_confirm_date': self._parse_datetime(properties.get('arrivy_confirm_date')),
            'arrivy_confirm_user': self._truncate_field(properties.get('arrivy_confirm_user'), 255, 'arrivy_confirm_user', record_id),
            'arrivy_created_by': self._truncate_field(properties.get('arrivy_created_by'), 255, 'arrivy_created_by', record_id),
            'arrivy_details': properties.get('arrivy_details'),  # TextField - no truncation needed
            'arrivy_notes': properties.get('arrivy_notes'),  # TextField - no truncation needed
            'arrivy_object_id': self._truncate_field(properties.get('arrivy_object_id'), 255, 'arrivy_object_id', record_id),
            'arrivy_result_full_string': properties.get('arrivy_result_full_string'),
            'arrivy_salesrep_first_name': properties.get('arrivy_salesrep_first_name'),
            'arrivy_salesrep_last_name': properties.get('arrivy_salesrep_last_name'),
            'arrivy_status': properties.get('arrivy_status'),
            'arrivy_status_title': properties.get('arrivy_status_title'),
            'arrivy_user': properties.get('arrivy_user'),
            'arrivy_user_divison_id': properties.get('arrivy_user_divison_id'),
            'arrivy_user_external_id': properties.get('arrivy_user_external_id'),
            'arrivy_username': properties.get('arrivy_username'),
            # SalesPro integration fields - Added missing fields
            'salespro_both_homeowners': self._parse_boolean(properties.get('salespro_both_homeowners')),
            'salespro_consider_solar': self._truncate_field(properties.get('salespro_consider_solar'), 255, 'salespro_consider_solar', record_id),
            'salespro_customer_id': self._truncate_field(properties.get('salespro_customer_id'), 255, 'salespro_customer_id', record_id),
            'salespro_deadline': self._parse_date(properties.get('salespro_deadline'), record_id, 'salespro_deadline'),
            'salespro_deposit_type': self._truncate_field(properties.get('salespro_deposit_type'), 255, 'salespro_deposit_type', record_id),
            'salespro_estimate_id': self._truncate_field(properties.get('salespro_estimate_id'), 255, 'salespro_estimate_id', record_id),
            'salespro_fileurl_contract': properties.get('salespro_fileurl_contract'),  # URLField - no truncation needed
            'salespro_fileurl_estimate': properties.get('salespro_fileurl_estimate'),  # URLField - no truncation needed
            'salespro_financing': properties.get('salespro_financing'),  # TextField - no truncation needed
            'salespro_job_size': self._truncate_field(properties.get('salespro_job_size'), 255, 'salespro_job_size', record_id),
            'salespro_job_type': self._truncate_field(properties.get('salespro_job_type'), 255, 'salespro_job_type', record_id),
            'salespro_last_price_offered': self._truncate_field(properties.get('salespro_last_price_offered'), 255, 'salespro_last_price_offered', record_id),
            'salespro_notes': properties.get('salespro_notes'),  # TextField - no truncation needed
            'salespro_one_year_price': self._truncate_field(properties.get('salespro_one_year_price'), 255, 'salespro_one_year_price', record_id),
            'salespro_preferred_payment': self._truncate_field(properties.get('salespro_preferred_payment'), 255, 'salespro_preferred_payment', record_id),
            'salespro_requested_start': self._parse_date(properties.get('salespro_requested_start'), record_id, 'salespro_requested_start'),
            'salespro_result': self._truncate_field(properties.get('salespro_result'), 255, 'salespro_result', record_id),
            'salespro_result_notes': properties.get('salespro_result_notes'),  # TextField - no truncation needed
            'salespro_result_reason_demo': self._truncate_field(properties.get('salespro_result_reason_demo'), 255, 'salespro_result_reason_demo', record_id),
            'salespro_result_reason_no_demo': self._truncate_field(properties.get('salespro_result_reason_no_demo'), 255, 'salespro_result_reason_no_demo', record_id),
            # Notes and additional fields
            'notes': properties.get('notes'),  # TextField - no truncation needed
            'log': properties.get('log'),  # TextField - no truncation needed
            'title': self._truncate_field(properties.get('title'), 255, 'title', record_id),
            'marketing_task_id': self._parse_integer(properties.get('marketing_task_id'), record_id, 'marketing_task_id'),  # Fixed: Convert to integer
            'leap_estimate_id': self._truncate_field(properties.get('leap_estimate_id'), 255, 'leap_estimate_id', record_id),
            'spouses_present': self._parse_boolean(properties.get('spouses_present')),
            'year_built': properties.get('year_built'),  # IntegerField - no truncation needed
            'error_details': properties.get('error_details'),  # TextField - no truncation needed
            'tester_test': self._truncate_field(properties.get('tester_test'), 255, 'tester_test', record_id),
            # Additional missing fields
            'created_by_make': self._truncate_field(properties.get('created_by_make'), 255, 'created_by_make', record_id),
            'f9_tfuid': self._truncate_field(properties.get('f9_tfuid'), 255, 'f9_tfuid', record_id),
            'set_date': self._parse_date(properties.get('set_date'), record_id, 'set_date'),
            # Genius integration fields - Added missing fields
            'genius_quote_id': self._truncate_field(properties.get('genius_quote_id'), 255, 'genius_quote_id', record_id),
            'genius_quote_response': properties.get('genius_quote_response'),  # TextField - no truncation needed
            'genius_quote_response_status': self._truncate_field(properties.get('genius_quote_response_status'), 255, 'genius_quote_response_status', record_id),
            'genius_response': properties.get('genius_response'),  # TextField - no truncation needed
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot appointment record using field mappings and validation framework"""
        # Use the architectural pattern: apply field mappings first
        transformed = self.apply_field_mappings(record)
        
        # Get field types for validation
        field_types = self.get_field_types()
        
        # Apply validation framework to all fields
        for field_name, value in transformed.items():
            if value is not None and field_name in field_types:
                field_type = field_types[field_name]
                
                # Skip text fields as they don't need validation
                if field_type == 'text':
                    continue
                    
                try:
                    # Special handling for duration fields
                    if field_name in ['duration', 'hs_duration']:
                        transformed[field_name] = self.parse_duration(value)
                    # Special handling for is_complete (convert None to False)
                    elif field_name == 'is_complete':
                        validated = self.validate_field(field_name, value, field_type, record)
                        transformed[field_name] = validated if validated is not None else False
                    else:
                        transformed[field_name] = self.validate_field(field_name, value, field_type, record)
                        
                except ValidationException as e:
                    # Use fallback parsing for problematic fields with logging
                    record_id = record.get('id', 'UNKNOWN')
                    logger.warning(f"Validation failed for field '{field_name}' with value '{value}' for appointment {record_id}: {e}")
                    
                    # Keep original value for most fields, but apply safe fallbacks for critical types
                    if field_type == 'boolean' and field_name == 'is_complete':
                        transformed[field_name] = False
                    elif field_type == 'integer':
                        try:
                            transformed[field_name] = int(value) if value else None
                        except (ValueError, TypeError):
                            transformed[field_name] = None
                    # For other fields, keep original value (will be handled by validate_record if needed)
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate appointment record using validation framework"""
        record_id = record.get('id', 'UNKNOWN')
        
        if not record.get('id'):
            raise ValidationException("Appointment ID is required")
        
        # The validation framework handles all field validation through transform_record
        # This method is kept for any record-level validation that needs to happen
        # after field-level validation
        
        return record
        
        return record
