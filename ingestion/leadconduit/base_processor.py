"""
Base processor for LeadConduit data imports.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from django.utils import timezone
from ingestion.models.leadconduit import LeadConduit_SyncHistory

logger = logging.getLogger(__name__)


class BaseLeadConduitProcessor:
    """Base class for LeadConduit data processing"""
    
    def __init__(self, sync_type: str):
        self.sync_type = sync_type
        self.sync_history = None
        
    def start_sync(self, api_endpoint: Optional[str] = None, 
                   query_params: Optional[Dict] = None) -> LeadConduit_SyncHistory:
        """Start a new sync process and create history record"""
        self.sync_history = LeadConduit_SyncHistory.objects.create(
            sync_type=self.sync_type,
            api_endpoint=api_endpoint,
            query_params=query_params,
            status='in_progress'
        )
        logger.info(f"Started {self.sync_type} sync with ID {self.sync_history.id}")
        return self.sync_history
    
    def complete_sync(self, records_processed: int = 0, records_created: int = 0, 
                     records_updated: int = 0, start_id: Optional[str] = None,
                     end_id: Optional[str] = None):
        """Complete the sync process successfully"""
        if self.sync_history:
            self.sync_history.completed_at = timezone.now()
            self.sync_history.records_processed = records_processed
            self.sync_history.records_created = records_created
            self.sync_history.records_updated = records_updated
            self.sync_history.status = 'completed'
            if start_id:
                self.sync_history.start_id = start_id
            if end_id:
                self.sync_history.end_id = end_id
            self.sync_history.save()
            logger.info(f"Completed {self.sync_type} sync: {records_processed} processed, "
                       f"{records_created} created, {records_updated} updated")
    
    def fail_sync(self, error_message: str):
        """Mark the sync as failed with error message"""
        if self.sync_history:
            self.sync_history.completed_at = timezone.now()
            self.sync_history.status = 'failed'
            self.sync_history.error_message = error_message
            self.sync_history.save()
            logger.error(f"Failed {self.sync_type} sync: {error_message}")
    
    def parse_timestamp(self, timestamp_ms: Optional[int]) -> Optional[datetime]:
        """Convert milliseconds since epoch to datetime"""
        if timestamp_ms is None:
            return None
        try:
            return timezone.datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            logger.warning(f"Could not parse timestamp: {timestamp_ms}")
            return None
    
    def parse_iso_datetime(self, iso_string: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string"""
        if not iso_string or not str(iso_string).strip():
            return None
        try:
            # Handle ISO format like "2019-08-24T14:15:22Z"
            if iso_string.endswith('Z'):
                iso_string = iso_string[:-1] + '+00:00'
            return datetime.fromisoformat(iso_string)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse ISO datetime: {iso_string}")
            return None
    
    def extract_lead_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract lead information from event data
        Looks in vars and appended data for common lead fields
        """
        lead_info = {}
        
        # Get vars data (main lead data)
        vars_data = event_data.get('vars', {}) or {}
        appended_data = event_data.get('appended', {}) or {}
        
        # Combine vars and appended data, with appended taking precedence
        all_data = {**vars_data, **appended_data}
        
        # Extract standard lead fields with common variations
        field_mappings = {
            'first_name': ['first_name', 'firstName', 'fname', 'lead.first_name'],
            'last_name': ['last_name', 'lastName', 'lname', 'lead.last_name'],
            'email': ['email', 'email_address', 'lead.email'],
            'phone_1': ['phone', 'phone_1', 'phone1', 'primary_phone', 'lead.phone'],
            'phone_2': ['phone_2', 'phone2', 'secondary_phone', 'mobile'],
            'address_1': ['address', 'address_1', 'street', 'lead.address'],
            'address_2': ['address_2', 'address2', 'apartment', 'unit'],
            'city': ['city', 'lead.city'],
            'state': ['state', 'st', 'lead.state'],
            'postal_code': ['zip', 'postal_code', 'zip_code', 'lead.zip'],
            'country': ['country', 'lead.country'],
            'reference': ['reference', 'ref', 'lead_reference', 'tracking_id'],
        }
        
        for target_field, possible_keys in field_mappings.items():
            for key in possible_keys:
                if key in all_data and all_data[key]:
                    lead_info[target_field] = str(all_data[key]).strip()
                    break
        
        # Store the full data for reference
        lead_info['full_data'] = all_data
        
        return lead_info
    
    def extract_lead_id(self, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract lead ID from event data
        Looks in various common locations
        """
        vars_data = event_data.get('vars', {}) or {}
        appended_data = event_data.get('appended', {}) or {}
        
        # Check common lead ID fields
        id_fields = ['lead_id', 'leadId', 'id', 'lead.id', 'event_id']
        
        for field in id_fields:
            # Check in vars first
            if field in vars_data and vars_data[field]:
                return str(vars_data[field])
            # Then check in appended data
            if field in appended_data and appended_data[field]:
                return str(appended_data[field])
        
        # If no explicit lead ID found, use the event ID
        return event_data.get('id')
    
    def safe_get_nested(self, data: Dict, path: str, default=None):
        """Safely get nested dictionary value using dot notation"""
        try:
            for key in path.split('.'):
                data = data[key]
            return data
        except (KeyError, TypeError):
            return default
    
    def clean_phone(self, phone: Optional[str]) -> Optional[str]:
        """Clean and format phone number"""
        if not phone:
            return None
        
        # Remove common formatting characters
        cleaned = ''.join(c for c in str(phone) if c.isdigit())
        
        # Return None if not enough digits
        if len(cleaned) < 10:
            return None
            
        return cleaned
    
    def clean_email(self, email: Optional[str]) -> Optional[str]:
        """Clean and validate email address"""
        if not email:
            return None
        
        email = str(email).strip().lower()
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            return None
            
        return email
