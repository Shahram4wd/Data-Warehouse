"""
Base processor for HubSpot data
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from ingestion.base.processor import BaseDataProcessor
from ingestion.base.exceptions import (
    ValidationException, RetryableException, NonRetryableException
)
from ingestion.base.validators import (
    EmailValidator, PhoneValidator, DateValidator, 
    DecimalValidator, BooleanValidator, StringValidator
)
from ingestion.base.retry import retry_with_backoff, RetryConfig
from ingestion.base.config import SyncConfiguration
from ingestion.base.performance import performance_monitor, monitor_performance
from ingestion.sync.hubspot.validators import (
    HubSpotEmailValidator, HubSpotPhoneValidator, HubSpotObjectIdValidator,
    HubSpotTimestampValidator, HubSpotCurrencyValidator, HubSpotZipCodeValidator,
    HubSpotStateValidator, HubSpotUrlValidator
)

logger = logging.getLogger(__name__)

class HubSpotBaseProcessor(BaseDataProcessor):
    """Base processor for HubSpot data"""
    
    def __init__(self, model_class, **kwargs):
        super().__init__(model_class, **kwargs)
        
        # Initialize configuration
        self.config = SyncConfiguration('hubspot')
        
        # Initialize validators
        self.email_validator = HubSpotEmailValidator()
        self.phone_validator = HubSpotPhoneValidator()
        self.object_id_validator = HubSpotObjectIdValidator()
        self.timestamp_validator = HubSpotTimestampValidator()
        self.currency_validator = HubSpotCurrencyValidator()
        self.zip_code_validator = HubSpotZipCodeValidator()
        self.state_validator = HubSpotStateValidator()
        self.url_validator = HubSpotUrlValidator()
        self.date_validator = DateValidator()
        self.decimal_validator = DecimalValidator()
        self.boolean_validator = BooleanValidator()
        
        # Initialize retry configuration
        self.retry_config = RetryConfig(**self.config.get_retry_config())
    
    def parse_duration(self, value: str) -> int:
        """Convert 'HH:MM:SS' to minutes
        
        Args:
            value: Duration string in 'HH:MM:SS' format (e.g., '2:00:00')
            
        Returns:
            Duration in minutes as integer
            
        Raises:
            Returns 0 if parsing fails to maintain data integrity
        """
        try:
            if not value:
                return 0
            
            # Handle string input    
            if isinstance(value, str):
                # Split by colons and convert to integers
                h, m, s = map(int, value.split(":"))
                return h * 60 + m + s // 60
            
            # Handle numeric input (assume it's already in minutes)
            if isinstance(value, (int, float)):
                return int(value)
                
            return 0
        except Exception as e:
            logger.warning(f"Failed to parse duration '{value}': {e}")
            return 0  # Return 0 instead of raising exception for data integrity
    
    def validate_field(self, field_name: str, value: Any, field_type: str = 'string') -> Any:
        """Validate a field using appropriate validator"""
        # Check if validation is enabled
        if not self.config.is_validation_enabled():
            return value
        
        try:
            if field_type == 'email':
                return self.email_validator.validate(value)
            elif field_type == 'phone':
                return self.phone_validator.validate(value)
            elif field_type == 'object_id':
                return self.object_id_validator.validate(value)
            elif field_type == 'timestamp':
                return self.timestamp_validator.validate(value)
            elif field_type == 'currency':
                return self.currency_validator.validate(value)
            elif field_type == 'zip_code':
                return self.zip_code_validator.validate(value)
            elif field_type == 'state':
                return self.state_validator.validate(value)
            elif field_type == 'url':
                return self.url_validator.validate(value)
            elif field_type == 'date' or field_type == 'datetime':
                return self.date_validator.validate(value)
            elif field_type == 'decimal':
                return self.decimal_validator.validate(value)
            elif field_type == 'boolean':
                return self.boolean_validator.validate(value)
            else:
                # Default string validation
                return StringValidator().validate(value)
        except ValidationException as e:
            # Handle validation errors based on strict mode
            if self.config.is_strict_validation():
                logger.error(f"Strict validation failed for field '{field_name}': {e}")
                raise ValidationException(f"Field '{field_name}': {e}")
            else:
                logger.warning(f"Validation warning for field '{field_name}': {e}")
                return value  # Return original value in non-strict mode
        except Exception as e:
            logger.error(f"Unexpected error validating field '{field_name}': {e}")
            if self.config.is_strict_validation():
                raise ValidationException(f"Field '{field_name}': Validation error")
            return value
    
    @monitor_performance('parse_datetime')
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from HubSpot format using validator"""
        try:
            return self.date_validator.validate(value)
        except ValidationException:
            return self._legacy_parse_datetime(value)
    
    def _legacy_parse_datetime(self, value: Any) -> Optional[datetime]:
        """Legacy datetime parsing for backward compatibility"""
        if not value:
            return None
        
        # If it's already a datetime object, return it
        if isinstance(value, datetime):
            return value
        
        # Convert to string if it's a number (timestamp)
        if isinstance(value, (int, float)):
            value = str(int(value))
        
        # Try to parse as datetime
        try:
            # HubSpot timestamps are in milliseconds
            if str(value).isdigit():
                timestamp = int(value)
                # Convert from milliseconds to seconds
                if timestamp > 10000000000:  # If timestamp is in milliseconds
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                # Try to parse as ISO format
                parsed = parse_datetime(str(value))
                if parsed:
                    return parsed
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to parse datetime '{value}': {e}")
        
        return None
    
    @monitor_performance('parse_decimal')
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse decimal value using validator"""
        try:
            return self.decimal_validator.validate(value)
        except ValidationException:
            return self._legacy_parse_decimal(value)
    
    def _legacy_parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Legacy decimal parsing for backward compatibility"""
        if not value:
            return None
        
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            logger.warning(f"Failed to parse decimal '{value}'")
            return None
    
    @monitor_performance('parse_boolean')
    def _parse_boolean(self, value: Any) -> Optional[bool]:
        """Parse boolean value using validator"""
        try:
            return self.boolean_validator.validate(value)
        except ValidationException:
            return self._legacy_parse_boolean(value)
    
    def _legacy_parse_boolean(self, value: Any) -> Optional[bool]:
        """Legacy boolean parsing for backward compatibility"""
        if value is None:
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value = value.lower()
            if value in ('true', '1', 'yes', 'on'):
                return True
            elif value in ('false', '0', 'no', 'off'):
                return False
        
        return None
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number using validator"""
        try:
            return self.phone_validator.validate(phone) or phone
        except ValidationException:
            return self._legacy_clean_phone(phone)
    
    def _legacy_clean_phone(self, phone: str) -> str:
        """Legacy phone cleaning for backward compatibility"""
        if not phone:
            return phone
        
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Format as standard phone number if it's 10 digits
        if len(cleaned) == 10:
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) == 11 and cleaned[0] == '1':
            return f"({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        
        return phone
    
    def _clean_email(self, email: str) -> str:
        """Clean and validate email using validator"""
        try:
            return self.email_validator.validate(email) or email
        except ValidationException:
            return self._legacy_clean_email(email)
    
    def _legacy_clean_email(self, email: str) -> str:
        """Legacy email cleaning for backward compatibility"""
        if not email:
            return email
        
        email = email.lower().strip()
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            raise ValidationException(f"Invalid email format: {email}")
        
        return email
    
    def _get_nested_value(self, data: dict, key_path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
