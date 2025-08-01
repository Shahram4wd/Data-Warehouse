"""
CallRail-specific validation rules following CRM sync guide architecture
"""
import logging
import re
from typing import Dict, Any, List
from ingestion.base.exceptions import ValidationException

logger = logging.getLogger(__name__)


class CallRailValidator:
    """CallRail-specific validation rules"""
    
    def __init__(self):
        self.phone_pattern = re.compile(r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$')
        self.email_pattern = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    
    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return False
        
        # Clean phone number for validation
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Check basic format
        if len(cleaned) < 10:
            return False
        
        return bool(self.phone_pattern.match(phone))
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        
        return bool(self.email_pattern.match(email))
    
    def validate_call_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate call record data"""
        warnings = []
        
        # Validate phone numbers
        customer_phone = record.get('customer_phone_number')
        if customer_phone and not self.validate_phone_number(customer_phone):
            warnings.append(f"Invalid customer phone number format: {customer_phone}")
        
        tracking_phone = record.get('tracking_phone_number')
        if tracking_phone and not self.validate_phone_number(tracking_phone):
            warnings.append(f"Invalid tracking phone number format: {tracking_phone}")
        
        # Validate call direction
        direction = record.get('direction')
        if direction and direction not in ['inbound', 'outbound']:
            warnings.append(f"Invalid call direction: {direction}")
        
        # Validate duration (should be non-negative)
        duration = record.get('duration')
        if duration is not None:
            try:
                duration_int = int(duration)
                if duration_int < 0:
                    warnings.append(f"Invalid negative call duration: {duration}")
            except (ValueError, TypeError):
                warnings.append(f"Invalid duration format: {duration}")
        
        return warnings
    
    def validate_company_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate company record data"""
        warnings = []
        
        # Validate company name
        name = record.get('name')
        if not name or len(name.strip()) == 0:
            warnings.append("Company missing name")
        
        # Validate status
        status = record.get('status')
        valid_statuses = ['active', 'disabled', 'trial']
        if status and status not in valid_statuses:
            warnings.append(f"Unknown company status: {status}")
        
        # Validate time zone
        time_zone = record.get('time_zone')
        if time_zone and len(time_zone) > 100:
            warnings.append(f"Time zone too long: {time_zone}")
        
        return warnings
    
    def validate_form_submission_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate form submission record data"""
        warnings = []
        
        # Validate form URL
        form_url = record.get('form_url')
        if form_url and not self._is_valid_url(form_url):
            warnings.append(f"Invalid form URL format: {form_url}")
        
        # Validate landing page URL
        landing_url = record.get('landing_page_url')
        if landing_url and not self._is_valid_url(landing_url):
            warnings.append(f"Invalid landing page URL format: {landing_url}")
        
        # Validate form data exists
        form_data = record.get('form_data')
        if not form_data:
            warnings.append("Form submission missing form data")
        
        return warnings
    
    def validate_tracker_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate tracker record data"""
        warnings = []
        
        # Validate tracker name
        name = record.get('name')
        if not name or len(name.strip()) == 0:
            warnings.append("Tracker missing name")
        
        # Validate tracker type
        tracker_type = record.get('type')
        valid_types = ['pool', 'source', 'form', 'website']
        if tracker_type and tracker_type not in valid_types:
            warnings.append(f"Unknown tracker type: {tracker_type}")
        
        # Validate destination number
        dest_number = record.get('destination_number')
        if dest_number and not self.validate_phone_number(dest_number):
            warnings.append(f"Invalid destination phone number: {dest_number}")
        
        # Validate tracking numbers
        tracking_numbers = record.get('tracking_numbers', [])
        if isinstance(tracking_numbers, list):
            for number in tracking_numbers:
                if not self.validate_phone_number(number):
                    warnings.append(f"Invalid tracking phone number: {number}")
        
        return warnings
    
    def validate_text_message_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate text message record data"""
        warnings = []
        
        # Validate phone numbers
        customer_phone = record.get('customer_phone_number')
        if customer_phone and not self.validate_phone_number(customer_phone):
            warnings.append(f"Invalid customer phone number: {customer_phone}")
        
        tracking_phone = record.get('tracking_phone_number')
        if tracking_phone and not self.validate_phone_number(tracking_phone):
            warnings.append(f"Invalid tracking phone number: {tracking_phone}")
        
        # Validate direction
        direction = record.get('direction')
        if direction and direction not in ['inbound', 'outbound']:
            warnings.append(f"Invalid SMS direction: {direction}")
        
        # Validate message content
        message = record.get('message')
        if not message or len(message.strip()) == 0:
            warnings.append("Text message missing content")
        
        return warnings
    
    def validate_user_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate user record data"""
        warnings = []
        
        # Validate names
        first_name = record.get('first_name')
        last_name = record.get('last_name')
        if not first_name or len(first_name.strip()) == 0:
            warnings.append("User missing first name")
        if not last_name or len(last_name.strip()) == 0:
            warnings.append("User missing last name")
        
        # Validate email
        email = record.get('email')
        if email and not self.validate_email(email):
            warnings.append(f"Invalid email format: {email}")
        
        return warnings
    
    def validate_account_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate account record data"""
        warnings = []
        
        # Validate account name
        name = record.get('name')
        if not name or len(name.strip()) == 0:
            warnings.append("Account missing name")
        
        return warnings
    
    def validate_tag_data(self, record: Dict[str, Any]) -> List[str]:
        """Validate tag record data"""
        warnings = []
        
        # Validate tag name
        name = record.get('name')
        if not name or len(name.strip()) == 0:
            warnings.append("Tag missing name")
        
        # Validate color format (if present)
        color = record.get('color')
        if color:
            # Should be a hex color or named color
            if not re.match(r'^#[0-9A-Fa-f]{6}$', color) and color not in [
                'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'gray'
            ]:
                warnings.append(f"Invalid color format: {color}")
        
        return warnings
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation"""
        if not url:
            return False
        
        # Simple URL pattern
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
