"""
HubSpot data processors for transforming and validating data
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from ingestion.base.processor import BaseDataProcessor
from ingestion.base.exceptions import ValidationException
from ingestion.models.hubspot import (
    Hubspot_Contact, Hubspot_Appointment, Hubspot_Division, Hubspot_Deal
)

logger = logging.getLogger(__name__)

class HubSpotContactProcessor(BaseDataProcessor):
    """Process HubSpot contact data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_Contact, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from HubSpot to model"""
        return {
            'id': 'id',
            'properties.firstname': 'firstname',
            'properties.lastname': 'lastname',
            'properties.email': 'email',
            'properties.phone': 'phone',
            'properties.address': 'address',
            'properties.city': 'city',
            'properties.state': 'state',
            'properties.zip': 'zip',
            'properties.createdate': 'createdate',
            'properties.lastmodifieddate': 'lastmodifieddate',
            'properties.campaign_name': 'campaign_name',
            'properties.hs_google_click_id': 'hs_google_click_id',
            'properties.original_lead_source': 'original_lead_source',
            'properties.division': 'division',
            'properties.marketsharp_id': 'marketsharp_id',
            'properties.hs_object_id': 'hs_object_id',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot contact record to model format"""
        properties = record.get('properties', {})
        
        return {
            'id': record.get('id'),
            'firstname': properties.get('firstname'),
            'lastname': properties.get('lastname'),
            'email': properties.get('email'),
            'phone': properties.get('phone'),
            'address': properties.get('address'),
            'city': properties.get('city'),
            'state': properties.get('state'),
            'zip': properties.get('zip'),
            'createdate': self._parse_datetime(properties.get('createdate')),
            'lastmodifieddate': self._parse_datetime(properties.get('lastmodifieddate')),
            'campaign_name': properties.get('campaign_name'),
            'hs_google_click_id': properties.get('hs_google_click_id'),
            'original_lead_source': properties.get('original_lead_source'),
            'division': properties.get('division'),
            'marketsharp_id': properties.get('marketsharp_id'),
            'hs_object_id': properties.get('hs_object_id'),
            'adgroupid': properties.get('adgroupid'),
            'ap_leadid': properties.get('ap_leadid'),
            'campaign_content': properties.get('campaign_content'),
            'clickcheck': properties.get('clickcheck'),
            'clicktype': properties.get('clicktype'),
            'comments': properties.get('comments'),
            'lead_salesrabbit_lead_id': properties.get('lead_salesrabbit_lead_id'),
            'msm_source': properties.get('msm_source'),
            'original_lead_source_created': self._parse_datetime(properties.get('original_lead_source_created')),
            'price': self._parse_decimal(properties.get('price')),
            'reference_code': properties.get('reference_code'),
            'search_terms': properties.get('search_terms'),
            'tier': properties.get('tier'),
            'trustedform_cert_url': properties.get('trustedform_cert_url'),
            'vendorleadid': properties.get('vendorleadid'),
            'vertical': properties.get('vertical'),
        }
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact record"""
        if not record.get('id'):
            raise ValidationException("Contact ID is required")
        
        # Clean phone number
        if record.get('phone'):
            record['phone'] = self._clean_phone(record['phone'])
        
        # Validate email format if present
        if record.get('email'):
            record['email'] = self._clean_email(record['email'])
        
        return record
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime string"""
        if not value:
            return None
        
        if isinstance(value, str):
            # Try parsing HubSpot timestamp (milliseconds)
            try:
                timestamp = int(value)
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            except (ValueError, TypeError):
                # Try parsing ISO format
                return parse_datetime(value)
        
        return value
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Parse decimal value"""
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number"""
        if not phone:
            return phone
        # Remove non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        return cleaned[:20]  # Limit to field length
    
    def _clean_email(self, email: str) -> str:
        """Clean and validate email"""
        if not email:
            return email
        return email.lower().strip()

class HubSpotAppointmentProcessor(BaseDataProcessor):
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
            'properties.first_name': 'first_name',
            'properties.last_name': 'last_name',
            'properties.email': 'email',
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
            'hs_duration': self._parse_int(properties.get('hs_duration')),
            'hs_object_id': properties.get('hs_object_id'),
            'hs_createdate': self._parse_datetime(properties.get('hs_createdate')),
            'hs_lastmodifieddate': self._parse_datetime(properties.get('hs_lastmodifieddate')),
            'hs_pipeline': properties.get('hs_pipeline'),
            'hs_pipeline_stage': properties.get('hs_pipeline_stage'),
            
            # Contact information
            'first_name': properties.get('first_name'),
            'last_name': properties.get('last_name'),
            'email': properties.get('email'),
            'phone1': properties.get('phone1'),
            'phone2': properties.get('phone2'),
            
            # Address information
            'address1': properties.get('address1'),
            'address2': properties.get('address2'),
            'city': properties.get('city'),
            'state': properties.get('state'),
            'zip': properties.get('zip'),
            
            # Appointment scheduling
            'date': self._parse_date(properties.get('date')),
            'time': self._parse_time(properties.get('time')),
            'duration': self._parse_int(properties.get('duration')),
            
            # Status and completion
            'appointment_status': properties.get('appointment_status'),
            'appointment_response': properties.get('appointment_response'),
            'is_complete': self._parse_bool(properties.get('is_complete')),
            
            # Services and interests
            'appointment_services': properties.get('appointment_services'),
            'lead_services': properties.get('lead_services'),
            'product_interest_primary': properties.get('product_interest_primary'),
            'product_interest_secondary': properties.get('product_interest_secondary'),
            
            # Assignment and ownership
            'user_id': properties.get('user_id'),
            'canvasser': properties.get('canvasser'),
            'canvasser_id': properties.get('canvasser_id'),
            'canvasser_email': properties.get('canvasser_email'),
            'hubspot_owner_id': properties.get('hubspot_owner_id'),
            'hubspot_owner_assigneddate': self._parse_datetime(properties.get('hubspot_owner_assigneddate')),
            'hubspot_team_id': properties.get('hubspot_team_id'),
            
            # Division and sources
            'division_id': properties.get('division_id'),
            'primary_source': properties.get('primary_source'),
            'secondary_source': properties.get('secondary_source'),
            'prospect_id': properties.get('prospect_id'),
            'prospect_source_id': properties.get('prospect_source_id'),
            'hscontact_id': properties.get('hscontact_id'),
            
            # Type information
            'type_id': properties.get('type_id'),
            'type_id_text': properties.get('type_id_text'),
            'marketsharp_appt_type': properties.get('marketsharp_appt_type'),
            
            # Completion details
            'complete_date': self._parse_datetime(properties.get('complete_date')),
            'complete_outcome_id': properties.get('complete_outcome_id'),
            'complete_outcome_id_text': properties.get('complete_outcome_id_text'),
            'complete_user_id': properties.get('complete_user_id'),
            
            # Confirmation details
            'confirm_date': self._parse_datetime(properties.get('confirm_date')),
            'confirm_user_id': properties.get('confirm_user_id'),
            'confirm_with': properties.get('confirm_with'),
            
            # Assignment dates
            'assign_date': self._parse_datetime(properties.get('assign_date')),
            'add_date': self._parse_datetime(properties.get('add_date')),
            'add_user_id': properties.get('add_user_id'),
            
            # Additional fields
            'notes': properties.get('notes'),
            'log': properties.get('log'),
            'title': properties.get('title'),
            'marketing_task_id': properties.get('marketing_task_id'),
            'leap_estimate_id': properties.get('leap_estimate_id'),
            'spouses_present': self._parse_bool(properties.get('spouses_present')),
            'year_built': self._parse_int(properties.get('year_built')),
            'error_details': properties.get('error_details'),
            'tester_test': properties.get('tester_test'),
            
            # HubSpot system fields
            'hs_all_accessible_team_ids': self._parse_json(properties.get('hs_all_accessible_team_ids')),
            'hs_all_assigned_business_unit_ids': self._parse_json(properties.get('hs_all_assigned_business_unit_ids')),
            'hs_all_owner_ids': self._parse_json(properties.get('hs_all_owner_ids')),
            'hs_all_team_ids': self._parse_json(properties.get('hs_all_team_ids')),
        }
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate appointment record"""
        if not record.get('id'):
            raise ValidationException("Appointment ID is required")
        
        # Clean phone numbers
        for phone_field in ['phone1', 'phone2']:
            if record.get(phone_field):
                record[phone_field] = self._clean_phone(record[phone_field])
        
        # Validate email format if present
        if record.get('email'):
            record['email'] = self._clean_email(record['email'])
        
        return record
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime string"""
        if not value:
            return None
        
        if isinstance(value, str):
            try:
                timestamp = int(value)
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            except (ValueError, TypeError):
                return parse_datetime(value)
        
        return value
    
    def _parse_date(self, value: Any) -> Optional[str]:
        """Parse date string"""
        if not value:
            return None
        if isinstance(value, str):
            try:
                dt = self._parse_datetime(value)
                return dt.date() if dt else None
            except:
                return value
        return value
    
    def _parse_time(self, value: Any) -> Optional[str]:
        """Parse time string from various formats"""
        if not value:
            return None
        
        # Convert to string first
        value_str = str(value)
        
        # If it's a full datetime string (ISO format), extract just the time part
        if 'T' in value_str:
            try:
                # Split on 'T' and take the time part
                time_part = value_str.split('T')[1]
                # Remove timezone info if present
                if '+' in time_part:
                    time_part = time_part.split('+')[0]
                if 'Z' in time_part:
                    time_part = time_part.replace('Z', '')
                return time_part
            except (IndexError, ValueError):
                pass
        
        # If it's already in time format (HH:MM or HH:MM:SS), return as is
        if ':' in value_str and len(value_str.split(':')) >= 2:
            return value_str
        
        # Return None if we can't parse it
        return None
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse integer value"""
        if not value:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_bool(self, value: Any) -> bool:
        """Parse boolean value, return False for None/missing values"""
        if value is None:
            return False
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)
    
    def _parse_json(self, value: Any) -> Optional[Any]:
        """Parse JSON value"""
        if not value:
            return None
        if isinstance(value, str):
            try:
                import json
                return json.loads(value)
            except (ValueError, TypeError):
                return value
        return value
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number"""
        if not phone:
            return phone
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        return cleaned[:20]
    
    def _clean_email(self, email: str) -> str:
        """Clean and validate email"""
        if not email:
            return email
        return email.lower().strip()

class HubSpotDivisionProcessor(BaseDataProcessor):
    """Process HubSpot division data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_Division, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from HubSpot to model"""
        return {
            'id': 'id',
            'properties.division_name': 'division_name',
            'properties.division_label': 'division_label',
            'properties.division_code': 'division_code',
            'properties.status': 'status',
            'properties.region': 'region',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot division record to model format"""
        properties = record.get('properties', {})
        
        return {
            'id': record.get('id'),
            'division_name': properties.get('division_name'),
            'division_label': properties.get('division_label') or properties.get('label'),
            'division_code': properties.get('division_code') or properties.get('code'),
            'status': properties.get('status'),
            'region': properties.get('region'),
            'manager_name': properties.get('manager_name'),
            'manager_email': properties.get('manager_email'),
            'phone': properties.get('phone'),
            'address1': properties.get('address1'),
            'address2': properties.get('address2'),
            'city': properties.get('city'),
            'state': properties.get('state'),
            'zip': properties.get('zip'),
            'hs_object_id': properties.get('hs_object_id'),
            'hs_createdate': self._parse_datetime(properties.get('hs_createdate')),
            'hs_lastmodifieddate': self._parse_datetime(properties.get('hs_lastmodifieddate')),
            'hs_pipeline': properties.get('hs_pipeline'),
            'hs_pipeline_stage': properties.get('hs_pipeline_stage'),
        }
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate division record"""
        if not record.get('id'):
            raise ValidationException("Division ID is required")
        
        # Clean phone number
        if record.get('phone'):
            record['phone'] = self._clean_phone(record['phone'])
        
        # Validate email format if present
        if record.get('manager_email'):
            record['manager_email'] = self._clean_email(record['manager_email'])
        
        return record
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime string"""
        if not value:
            return None
        
        if isinstance(value, str):
            try:
                timestamp = int(value)
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            except (ValueError, TypeError):
                return parse_datetime(value)
        
        return value
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number"""
        if not phone:
            return phone
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        return cleaned[:20]
    
    def _clean_email(self, email: str) -> str:
        """Clean and validate email"""
        if not email:
            return email
        return email.lower().strip()

class HubSpotDealProcessor(BaseDataProcessor):
    """Process HubSpot deal data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_Deal, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from HubSpot to model"""
        return {
            'id': 'id',
            'properties.dealname': 'deal_name',
            'properties.amount': 'amount',
            'properties.closedate': 'closedate',
            'properties.createdate': 'createdate',
            'properties.dealstage': 'dealstage',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot deal record to model format"""
        properties = record.get('properties', {})
        
        return {
            'id': record.get('id'),
            'deal_name': properties.get('dealname'),
            'amount': self._parse_decimal(properties.get('amount')),
            'closedate': self._parse_datetime(properties.get('closedate')),
            'createdate': self._parse_datetime(properties.get('createdate')),
            'dealstage': properties.get('dealstage'),
            'dealtype': properties.get('dealtype'),
            'description': properties.get('description'),
            'hs_object_id': properties.get('hs_object_id'),
            'hubspot_owner_id': properties.get('hubspot_owner_id'),
            'pipeline': properties.get('pipeline'),
            'division': properties.get('division'),
            'priority': properties.get('priority'),
        }
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate deal record"""
        if not record.get('id'):
            raise ValidationException("Deal ID is required")
        
        return record
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime string"""
        if not value:
            return None
        
        if isinstance(value, str):
            try:
                timestamp = int(value)
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            except (ValueError, TypeError):
                return parse_datetime(value)
        
        return value
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Parse decimal value"""
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
