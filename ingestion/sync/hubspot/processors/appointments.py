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
            'time': properties.get('time'),
            'duration': self.parse_duration(properties.get('duration')),
            'appointment_status': properties.get('appointment_status'),
            'appointment_response': properties.get('appointment_response'),
            'is_complete': self._parse_boolean(properties.get('is_complete')),
            'appointment_services': properties.get('appointment_services'),
            'lead_services': properties.get('lead_services'),
            'type_id': properties.get('type_id'),
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
            'primary_source': properties.get('primary_source'),
            'secondary_source': properties.get('secondary_source'),
            'prospect_id': properties.get('prospect_id'),
            'prospect_source_id': properties.get('prospect_source_id'),
            'hscontact_id': properties.get('hscontact_id'),
            # Completion and confirmation
            'complete_date': self._parse_datetime(properties.get('complete_date')),
            'complete_outcome_id': properties.get('complete_outcome_id'),
            'complete_outcome_id_text': properties.get('complete_outcome_id_text'),
            'complete_user_id': properties.get('complete_user_id'),
            'confirm_date': self._parse_datetime(properties.get('confirm_date')),
            'confirm_user_id': properties.get('confirm_user_id'),
            'confirm_with': properties.get('confirm_with'),
            'assign_date': self._parse_datetime(properties.get('assign_date')),
            'add_date': self._parse_datetime(properties.get('add_date')),
            'add_user_id': properties.get('add_user_id'),
            # Notes and additional fields
            'notes': properties.get('notes'),
            'log': properties.get('log'),
            'title': properties.get('title'),
            'marketing_task_id': properties.get('marketing_task_id'),
            'leap_estimate_id': properties.get('leap_estimate_id'),
            'spouses_present': self._parse_boolean(properties.get('spouses_present')),
            'year_built': properties.get('year_built'),
            'error_details': properties.get('error_details'),
            'tester_test': properties.get('tester_test'),
        }
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate appointment record using new validation framework"""
        if not record.get('id'):
            raise ValidationException("Appointment ID is required")
        
        # Validate HubSpot object ID
        if record.get('hs_object_id'):
            record['hs_object_id'] = self.validate_field('hs_object_id', record['hs_object_id'], 'object_id')
        
        # Validate phone numbers
        if record.get('phone1'):
            record['phone1'] = self.validate_field('phone1', record['phone1'], 'phone')
        if record.get('phone2'):
            record['phone2'] = self.validate_field('phone2', record['phone2'], 'phone')
        
        # Validate email format if present
        if record.get('email'):
            record['email'] = self.validate_field('email', record['email'], 'email')
        if record.get('canvasser_email'):
            record['canvasser_email'] = self.validate_field('canvasser_email', record['canvasser_email'], 'email')
        
        # Validate address fields
        if record.get('zip'):
            try:
                record['zip'] = self.validate_field('zip', record['zip'], 'zip_code')
            except ValidationException as e:
                logger.warning(f"Invalid zip code for appointment {record['id']}: {e}")
                # Keep original value if validation fails
        
        if record.get('state'):
            try:
                record['state'] = self.validate_field('state', record['state'], 'state')
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
                    record[field] = self.validate_field(field, record[field], 'datetime')
                except ValidationException as e:
                    # Use legacy parsing as fallback
                    logger.warning(f"Using legacy datetime parsing for {field}: {e}")
                    record[field] = self._parse_datetime(record[field])
        
        # Validate boolean fields
        boolean_fields = ['is_complete', 'spouses_present']
        for field in boolean_fields:
            if record.get(field) is not None:
                try:
                    record[field] = self.validate_field(field, record[field], 'boolean')
                except ValidationException as e:
                    # Use legacy parsing as fallback
                    logger.warning(f"Using legacy boolean parsing for {field}: {e}")
                    record[field] = self._parse_boolean(record[field])
        
        return record
