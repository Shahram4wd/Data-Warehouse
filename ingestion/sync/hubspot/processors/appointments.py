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
        """Return field mappings from HubSpot to model"""
        return {
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
            # New field mappings
            'properties.appointment_confirmed': 'appointment_confirmed',
            'properties.cancel_reason': 'cancel_reason',
            'properties.div_cancel_reasons': 'div_cancel_reasons',
            'properties.qc_cancel_reasons': 'qc_cancel_reasons',
            'properties.division': 'division',
            'properties.sourcefield': 'sourcefield',
            'properties.created_by_make': 'created_by_make',
            'properties.f9_tfuid': 'f9_tfuid',
            'properties.set_date': 'set_date',
            # Arrivy fields
            'properties.arrivy_details': 'arrivy_details',
            'properties.arrivy_notes': 'arrivy_notes',
            'properties.arrivy_result_full_string': 'arrivy_result_full_string',
            'properties.arrivy_salesrep_first_name': 'arrivy_salesrep_first_name',
            'properties.arrivy_salesrep_last_name': 'arrivy_salesrep_last_name',
            'properties.arrivy_status_title': 'arrivy_status_title',
            # SalesPro fields
            'properties.salespro_consider_solar': 'salespro_consider_solar',
            'properties.salespro_customer_id': 'salespro_customer_id',
            'properties.salespro_estimate_id': 'salespro_estimate_id',
            # Genius fields
            'properties.genius_quote_id': 'genius_quote_id',
            'properties.genius_quote_response': 'genius_quote_response',
            'properties.genius_quote_response_status': 'genius_quote_response_status',
            'properties.genius_response': 'genius_response',
            'properties.genius_response_status': 'genius_response_status',
            'properties.genius_resubmit': 'genius_resubmit',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot appointment record to model format"""
        properties = record.get('properties', {})
        
        return {
            'id': record.get('id'),
            'appointment_id': properties.get('appointment_id'),
            'genius_appointment_id': properties.get('genius_appointment_id'),
            'marketsharp_id': properties.get('marketsharp_id'),
            'hs_appointment_name': properties.get('hs_appointment_name'),
            'hs_appointment_start': self._parse_datetime(properties.get('hs_appointment_start')),
            'hs_appointment_end': self._parse_datetime(properties.get('hs_appointment_end')),
            'hs_duration': self.parse_duration(properties.get('hs_duration')),
            'hs_object_id': properties.get('hs_object_id'),
            'hs_createdate': self._parse_datetime(properties.get('hs_createdate')),
            'hs_lastmodifieddate': self._parse_datetime(properties.get('hs_lastmodifieddate')),
            'hs_pipeline': properties.get('hs_pipeline'),
            'hs_pipeline_stage': properties.get('hs_pipeline_stage'),
            # Contact info
            'first_name': properties.get('first_name'),
            'last_name': properties.get('last_name'),
            'email': properties.get('email'),
            'phone1': properties.get('phone1'),
            'phone2': properties.get('phone2'),
            'address1': properties.get('address1'),
            'address2': properties.get('address2'),
            'city': properties.get('city'),
            'state': properties.get('state'),
            'zip': properties.get('zip'),
            # Appointment details
            'date': self._parse_datetime(properties.get('date')),
            'time': self.validate_field('time', properties.get('time'), 'time'),
            'duration': self.parse_duration(properties.get('duration')),
            'appointment_status': properties.get('appointment_status'),
            'appointment_confirmed': properties.get('appointment_confirmed'),  # Added missing field
            'appointment_response': properties.get('appointment_response'),
            'is_complete': self._parse_boolean_not_null(properties.get('is_complete')),
            # Cancel reasons - Added missing fields
            'cancel_reason': properties.get('cancel_reason'),
            'div_cancel_reasons': properties.get('div_cancel_reasons'),
            'qc_cancel_reasons': properties.get('qc_cancel_reasons'),
            'appointment_services': properties.get('appointment_services'),
            'lead_services': properties.get('lead_services'),
            'type_id': self._parse_integer(properties.get('type_id')),  # Fixed: Convert to integer
            'type_id_text': properties.get('type_id_text'),
            'marketsharp_appt_type': properties.get('marketsharp_appt_type'),
            # User and assignment
            'user_id': properties.get('user_id'),
            'canvasser': properties.get('canvasser'),
            'canvasser_id': properties.get('canvasser_id'),
            'canvasser_email': properties.get('canvasser_email'),
            'hubspot_owner_id': properties.get('hubspot_owner_id'),
            'hubspot_owner_assigneddate': self._parse_datetime(properties.get('hubspot_owner_assigneddate')),
            'hubspot_team_id': properties.get('hubspot_team_id'),
            'division_id': properties.get('division_id'),
            'division': properties.get('division'),  # Added missing field
            'primary_source': properties.get('primary_source'),
            'secondary_source': properties.get('secondary_source'),
            'prospect_id': properties.get('prospect_id'),
            'prospect_source_id': properties.get('prospect_source_id'),
            'hscontact_id': properties.get('hscontact_id'),
            'sourcefield': properties.get('sourcefield'),  # Added missing field
            # Completion and confirmation
            'complete_date': self._parse_datetime(properties.get('complete_date')),
            'complete_outcome_id': self._parse_integer(properties.get('complete_outcome_id')),  # Fixed: Convert to integer
            'complete_outcome_id_text': properties.get('complete_outcome_id_text'),
            'complete_user_id': self._parse_integer(properties.get('complete_user_id')),  # Fixed: Convert to integer
            'confirm_date': self._parse_datetime(properties.get('confirm_date')),
            'confirm_user_id': self._parse_integer(properties.get('confirm_user_id')),  # Fixed: Convert to integer
            'confirm_with': properties.get('confirm_with'),
            'assign_date': self._parse_datetime(properties.get('assign_date')),
            'add_date': self._parse_datetime(properties.get('add_date')),
            'add_user_id': self._parse_integer(properties.get('add_user_id')),  # Fixed: Convert to integer
            # Arrivy integration fields - Added missing fields
            'arrivy_appt_date': self._parse_datetime(properties.get('arrivy_appt_date')),
            'arrivy_confirm_date': self._parse_datetime(properties.get('arrivy_confirm_date')),
            'arrivy_confirm_user': properties.get('arrivy_confirm_user'),
            'arrivy_created_by': properties.get('arrivy_created_by'),
            'arrivy_details': properties.get('arrivy_details'),
            'arrivy_notes': properties.get('arrivy_notes'),
            'arrivy_object_id': properties.get('arrivy_object_id'),
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
            'salespro_consider_solar': properties.get('salespro_consider_solar'),
            'salespro_customer_id': properties.get('salespro_customer_id'),
            'salespro_deadline': self._parse_date(properties.get('salespro_deadline')),
            'salespro_deposit_type': properties.get('salespro_deposit_type'),
            'salespro_estimate_id': properties.get('salespro_estimate_id'),
            'salespro_fileurl_contract': properties.get('salespro_fileurl_contract'),
            'salespro_fileurl_estimate': properties.get('salespro_fileurl_estimate'),
            'salespro_financing': properties.get('salespro_financing'),
            'salespro_job_size': properties.get('salespro_job_size'),
            'salespro_job_type': properties.get('salespro_job_type'),
            'salespro_last_price_offered': self._parse_decimal(properties.get('salespro_last_price_offered')),
            'salespro_notes': properties.get('salespro_notes'),
            'salespro_one_year_price': self._parse_decimal(properties.get('salespro_one_year_price')),
            'salespro_preferred_payment': properties.get('salespro_preferred_payment'),
            'salespro_requested_start': self._parse_date(properties.get('salespro_requested_start')),
            'salespro_result': properties.get('salespro_result'),
            'salespro_result_notes': properties.get('salespro_result_notes'),
            'salespro_result_reason_demo': properties.get('salespro_result_reason_demo'),
            'salespro_result_reason_no_demo': properties.get('salespro_result_reason_no_demo'),
            # Notes and additional fields
            'notes': properties.get('notes'),
            'log': properties.get('log'),
            'title': properties.get('title'),
            'marketing_task_id': self._parse_integer(properties.get('marketing_task_id')),  # Fixed: Convert to integer
            'leap_estimate_id': properties.get('leap_estimate_id'),
            'spouses_present': self._parse_boolean(properties.get('spouses_present')),
            'year_built': properties.get('year_built'),
            'error_details': properties.get('error_details'),
            'tester_test': properties.get('tester_test'),
            # Additional missing fields
            'created_by_make': properties.get('created_by_make'),
            'f9_tfuid': properties.get('f9_tfuid'),
            'set_date': self._parse_date(properties.get('set_date')),
            # Genius integration fields - Added missing fields
            'genius_quote_id': properties.get('genius_quote_id'),
            'genius_quote_response': properties.get('genius_quote_response'),
            'genius_quote_response_status': properties.get('genius_quote_response_status'),
            'genius_response': properties.get('genius_response'),
            'genius_response_status': properties.get('genius_response_status'),
            'genius_resubmit': properties.get('genius_resubmit'),
        }
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate appointment record using new validation framework"""
        if not record.get('id'):
            raise ValidationException("Appointment ID is required")
        
        # Validate HubSpot object ID
        if record.get('hs_object_id'):
            record['hs_object_id'] = self.validate_field('hs_object_id', record['hs_object_id'], 'object_id', record)
        
        # Validate phone numbers
        if record.get('phone1'):
            record['phone1'] = self.validate_field('phone1', record['phone1'], 'phone', record)
        if record.get('phone2'):
            record['phone2'] = self.validate_field('phone2', record['phone2'], 'phone', record)
        
        # Validate email format if present
        if record.get('email'):
            record['email'] = self.validate_field('email', record['email'], 'email', record)
        if record.get('canvasser_email'):
            record['canvasser_email'] = self.validate_field('canvasser_email', record['canvasser_email'], 'email', record)
        
        # Validate address fields
        if record.get('zip'):
            try:
                record['zip'] = self.validate_field('zip', record['zip'], 'zip_code', record)
            except ValidationException as e:
                logger.warning(f"Invalid zip code for appointment {record['id']}: {e}")
                # Keep original value if validation fails
        
        if record.get('state'):
            try:
                record['state'] = self.validate_field('state', record['state'], 'state', record)
            except ValidationException as e:
                logger.warning(f"Invalid state code for appointment {record['id']}: {e}")
                # Keep original value if validation fails
        
        # Validate datetime fields
        datetime_fields = [
            'hs_appointment_start', 'hs_appointment_end', 'hs_createdate', 'hs_lastmodifieddate',
            'date', 'hubspot_owner_assigneddate', 'complete_date', 'confirm_date', 'assign_date', 'add_date'
        ]
        for field in datetime_fields:
            if record.get(field):
                try:
                    record[field] = self.validate_field(field, record[field], 'datetime', record)
                except ValidationException as e:
                    # Use legacy parsing as fallback
                    logger.warning(f"Using legacy datetime parsing for {field}: {e}")
                    record[field] = self._parse_datetime(record[field])
        
        # Validate boolean fields
        boolean_fields = ['spouses_present']
        for field in boolean_fields:
            if record.get(field) is not None:
                try:
                    record[field] = self.validate_field(field, record[field], 'boolean', record)
                except ValidationException as e:
                    # Use legacy parsing as fallback
                    logger.warning(f"Using legacy boolean parsing for {field}: {e}")
                    record[field] = self._parse_boolean(record[field])
        
        # Handle is_complete specifically - convert null to False
        if 'is_complete' in record:
            try:
                record['is_complete'] = self.validate_field('is_complete', record['is_complete'], 'boolean', record)
                if record['is_complete'] is None:
                    record['is_complete'] = False
            except ValidationException as e:
                # Use legacy parsing as fallback
                logger.warning(f"Using legacy boolean parsing for is_complete: {e}")
                record['is_complete'] = self._parse_boolean_not_null(record['is_complete'])
        
        return record
    
    def _parse_boolean_not_null(self, value: Any) -> bool:
        """Parse boolean value and convert None/null to False"""
        parsed_value = self._parse_boolean(value)
        return parsed_value if parsed_value is not None else False
    
    def _parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer value safely"""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse integer value: {value}")
            return None
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Parse decimal value safely"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse decimal value: {value}")
            return None
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse date value safely"""
        if value is None or value == '':
            return None
        try:
            # Try to parse as datetime first, then extract date
            parsed_datetime = self._parse_datetime(value)
            return parsed_datetime.date() if parsed_datetime else None
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse date value: {value}")
            return None
